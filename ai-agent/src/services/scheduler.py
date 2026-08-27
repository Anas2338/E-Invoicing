"""Scheduler for automation background jobs."""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone

from src.config.settings import settings
from src.database.session import get_automation_db_session, get_db_session as get_main_db_session

logger = logging.getLogger(__name__)
PAKISTAN_TZ = timezone("Asia/Karachi")
scheduler = None


def transfer_validated_invoices():
    """
    Transfer VALIDATED invoices whose scheduled time has arrived to the main database.

    Runs every 5 minutes. Uses proper Pakistan timezone for schedule comparison.
    """
    from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
    from src.services.transfer_service import TransferService
    from sqlmodel import select, and_, or_

    logger.info("Running validated invoice transfer...")
    try:
        with get_automation_db_session() as automation_db:
            with get_main_db_session() as main_db:
                now_pkt = datetime.now(PAKISTAN_TZ)
                today_pkt = now_pkt.date()
                current_time_pkt = now_pkt.time()

                logger.info(
                    f"Transfer check at {now_pkt.strftime('%Y-%m-%d %H:%M:%S')} PKT"
                )

                # Query validated invoices ready for transfer: past-date invoices
                # always qualify (backdated uploads are processed immediately);
                # today's invoices only once their scheduled time has arrived
                query = select(AutomationInvoice).where(
                    AutomationInvoice.status == AutomationInvoiceStatus.VALIDATED,
                    or_(
                        AutomationInvoice.scheduled_date < today_pkt,
                        and_(
                            AutomationInvoice.scheduled_date == today_pkt,
                            AutomationInvoice.scheduled_time <= current_time_pkt,
                        ),
                    ),
                ).order_by(
                    AutomationInvoice.scheduled_date.asc(),
                    AutomationInvoice.scheduled_time.asc(),
                )

                invoices = automation_db.exec(query).all()

                if not invoices:
                    logger.info("No validated invoices ready for transfer")
                    return

                logger.info(f"Found {len(invoices)} invoice(s) ready for transfer")

                transfer_service = TransferService()
                transferred = 0
                failed = 0

                for invoice in invoices:
                    # Pre-capture metadata — invoice may be deleted mid-transfer
                    inv_id = invoice.id
                    inv_number = invoice.invoice_number
                    try:
                        logger.info(
                            f"Transferring invoice {inv_number} "
                            f"(ID: {inv_id}) scheduled for "
                            f"{invoice.scheduled_date} {invoice.scheduled_time}"
                        )

                        manual_invoice = transfer_service.transform_invoice_data(invoice)

                        if transfer_service.check_duplicate(main_db, invoice.user_id, inv_id):
                            logger.warning(f"Duplicate: invoice {inv_id} already in main DB")
                            try:
                                invoice.status = AutomationInvoiceStatus.TRANSFERRED
                                invoice.transferred_at = datetime.utcnow()
                                invoice.transfer_error = "Duplicate - already transferred"
                                automation_db.add(invoice)
                                automation_db.commit()
                            except Exception:
                                # Invoice may have been deleted externally (e.g. session deletion)
                                automation_db.rollback()
                                logger.warning(
                                    f"Invoice {inv_id} ({inv_number}) was deleted "
                                    f"externally during duplicate handling — skipping"
                                )
                            failed += 1
                            continue

                        main_db.add(manual_invoice)
                        main_db.flush()

                        invoice.status = AutomationInvoiceStatus.TRANSFERRED
                        invoice.transferred_at = datetime.utcnow()
                        invoice.transfer_error = None
                        automation_db.add(invoice)

                        main_db.commit()
                        automation_db.commit()

                        transferred += 1
                        logger.info(
                            f"[OK] Transferred invoice {inv_number} "
                            f"-> Main DB ID: {manual_invoice.id}"
                        )

                    except Exception as e:
                        main_db.rollback()
                        automation_db.rollback()

                        error_type = transfer_service.classify_error(e)
                        error_details = f"[{error_type}] {type(e).__name__}: {str(e)}"

                        # Handle invoices deleted externally (e.g. upload session deleted
                        # mid-transfer) — skip gracefully instead of crashing the batch
                        from sqlalchemy.orm.exc import ObjectDeletedError, StaleDataError
                        if isinstance(e, (ObjectDeletedError, StaleDataError)):
                            logger.warning(
                                f"[SKIPPED] Invoice {inv_id} ({inv_number}) was deleted "
                                f"externally during transfer — skipping: {error_details}"
                            )
                            failed += 1
                            continue

                        logger.error(
                            f"[FAILED] Transfer failed for invoice "
                            f"{inv_number}: {error_details}"
                        )

                        # Try to update status to TRANSFER_FAILED — may fail if
                        # invoice was deleted externally (session cascade)
                        try:
                            invoice.status = AutomationInvoiceStatus.TRANSFER_FAILED
                            invoice.transfer_error = error_details[:2000]
                            automation_db.add(invoice)
                            automation_db.commit()
                        except Exception:
                            automation_db.rollback()
                            logger.warning(
                                f"Invoice {inv_id} ({inv_number}) was deleted "
                                f"externally after transfer failure — cannot update status"
                            )

                        failed += 1

                logger.info(
                    f"Transfer cycle complete: {transferred} transferred, {failed} failed"
                )

    except Exception as e:
        logger.error(f"Transfer job failed: {e}", exc_info=True)


def cleanup_transferred_invoices():
    """Permanently delete transferred invoices older than the retention period.

    Runs daily at 12:00 AM PKT. Only touches the automation database — the main
    database is never affected. Deletes in FK order: logs -> invoices -> sessions.
    """
    from src.models.excel_upload_session import ExcelUploadSession, ExcelUploadProcessingStatus
    from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
    from src.models.automation_log import AutomationLog
    from sqlmodel import select, delete
    from datetime import timedelta

    logger.info("Running transferred invoice cleanup...")
    try:
        with get_automation_db_session() as db:
            # transferred_at is stored as naive UTC (datetime.utcnow), so compare
            # with a naive UTC cutoff for consistency
            cutoff = datetime.utcnow() - timedelta(days=settings.cleanup_retention_days)

            # Invoices that were transferred to the main DB 2+ days ago
            # (SQLModel exec returns the UUID values directly for a single-column select)
            invoices_query = select(AutomationInvoice.id).where(
                AutomationInvoice.status == AutomationInvoiceStatus.TRANSFERRED,
                AutomationInvoice.transferred_at < cutoff,
            )
            invoice_ids = list(db.exec(invoices_query).all())

            if not invoice_ids:
                logger.info("No transferred invoices older than the retention period")
                return

            logger.info(
                f"Found {len(invoice_ids)} transferred invoice(s) older than "
                f"{settings.cleanup_retention_days} days — deleting permanently"
            )

            # 1. Delete logs belonging to these invoices
            log_stmt = delete(AutomationLog).where(
                AutomationLog.automation_invoice_id.in_(invoice_ids)
            )
            db.exec(log_stmt)

            # 2. Delete the transferred invoices themselves
            invoice_stmt = delete(AutomationInvoice).where(
                AutomationInvoice.id.in_(invoice_ids)
            )
            db.exec(invoice_stmt)

            # 3. Delete completed upload sessions left with no invoices
            #    (e.g. all their invoices were transferred and cleaned up)
            orphaned_sessions = db.exec(
                select(ExcelUploadSession).where(
                    ExcelUploadSession.processing_status == ExcelUploadProcessingStatus.COMPLETED,
                    ~select(AutomationInvoice.id).where(
                        AutomationInvoice.excel_upload_session_id == ExcelUploadSession.id
                    ).exists(),
                )
            ).all()
            for session in orphaned_sessions:
                db.delete(session)

            db.commit()
            logger.info(
                f"Deleted {len(invoice_ids)} transferred invoice(s) from automation database"
            )

    except Exception as e:
        logger.error(f"Transferred invoice cleanup failed: {e}", exc_info=True)


def cleanup_old_logs():
    """Delete automation logs older than the retention period."""
    from src.models.automation_log import AutomationLog
    from sqlmodel import select, delete

    logger.info("Running log retention cleanup...")
    try:
        with get_automation_db_session() as db:
            cutoff = datetime.now(PAKISTAN_TZ)
            from datetime import timedelta
            cutoff = cutoff - timedelta(days=settings.automation_log_retention_days)
            stmt = delete(AutomationLog).where(AutomationLog.timestamp < cutoff)
            result = db.exec(stmt)
            db.commit()
            if result.rowcount:
                logger.info(f"Deleted {result.rowcount} old automation logs")
    except Exception as e:
        logger.error(f"Log cleanup failed: {e}", exc_info=True)


def start_scheduler():
    """Start the background scheduler."""
    global scheduler
    if scheduler is not None:
        return

    scheduler = BackgroundScheduler(timezone=PAKISTAN_TZ)

    # Transfer validated invoices every 1 hour
    scheduler.add_job(
        transfer_validated_invoices,
        trigger=IntervalTrigger(seconds=3600),
        id="transfer_invoices",
        name="Transfer validated invoices to main DB",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("  Scheduled: Invoice transfer every 1 hour")

    scheduler.add_job(
        cleanup_old_logs,
        trigger="cron",
        hour=settings.cleanup_schedule_hour,
        minute=settings.cleanup_schedule_minute + 5,
        id="cleanup_logs",
        name="Cleanup old automation logs",
        replace_existing=True,
    )

    # Permanently delete transferred invoices older than the retention period.
    # Runs every day at 12:00 AM PKT as required.
    scheduler.add_job(
        cleanup_transferred_invoices,
        trigger="cron",
        hour=0,
        minute=0,
        id="cleanup_transferred_invoices",
        name="Delete transferred invoices older than retention period (12 AM PKT)",
        replace_existing=True,
    )

    scheduler.start()

    # Run cleanup once at startup too, so old transferred invoices are purged
    # even if the daily 12 AM PKT run was missed while the service was down.
    try:
        cleanup_transferred_invoices()
    except Exception:
        logger.exception("Startup transferred invoice cleanup failed")
    logger.info("AI-agent scheduler started")


def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("AI-agent scheduler stopped")
