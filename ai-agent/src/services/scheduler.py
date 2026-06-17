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
    from sqlmodel import select, and_

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

                # Query validated invoices whose scheduled time has arrived
                query = select(AutomationInvoice).where(
                    and_(
                        AutomationInvoice.status == AutomationInvoiceStatus.VALIDATED,
                        AutomationInvoice.scheduled_date <= today_pkt,
                        AutomationInvoice.scheduled_time <= current_time_pkt,
                    )
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


def expire_pending_invoices():
    """Mark invoices as EXPIRED when their scheduled_date has passed."""
    from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
    from sqlmodel import select

    logger.info("Running expired invoice cleanup...")
    try:
        with get_automation_db_session() as db:
            today = datetime.now(PAKISTAN_TZ).date()
            stmt = select(AutomationInvoice).where(
                AutomationInvoice.status == AutomationInvoiceStatus.PENDING,
                AutomationInvoice.scheduled_date < today,
            )
            expired = db.exec(stmt).all()
            count = 0
            for inv in expired:
                inv.status = AutomationInvoiceStatus.EXPIRED
                db.add(inv)
                count += 1
            db.commit()
            if count:
                logger.info(f"Marked {count} invoices as EXPIRED")
    except Exception as e:
        logger.error(f"Expired invoice cleanup failed: {e}", exc_info=True)


def cleanup_completed_upload_sessions():
    """Delete completed upload sessions older than retention period and all their invoices.

    Runs daily. Only touches the automation database — main DB is never affected.
    Deletes in FK order: logs -> invoices -> sessions.
    """
    from src.models.excel_upload_session import ExcelUploadSession, ExcelUploadProcessingStatus
    from src.models.automation_invoice import AutomationInvoice
    from src.models.automation_log import AutomationLog
    from sqlmodel import select, delete
    from datetime import timedelta

    logger.info("Running completed upload session cleanup...")
    try:
        with get_automation_db_session() as db:
            cutoff = datetime.now(PAKISTAN_TZ) - timedelta(days=settings.cleanup_retention_days)

            old_sessions_query = select(ExcelUploadSession.id).where(
                ExcelUploadSession.processing_status == ExcelUploadProcessingStatus.COMPLETED,
                ExcelUploadSession.upload_timestamp < cutoff,
            )
            old_session_ids = [row[0] for row in db.exec(old_sessions_query).all()]

            if not old_session_ids:
                logger.info("No completed upload sessions to clean up")
                return

            logger.info(
                f"Found {len(old_session_ids)} completed upload session(s) "
                f"older than {settings.cleanup_retention_days} days"
            )

            invoices_query = select(AutomationInvoice.id).where(
                AutomationInvoice.excel_upload_session_id.in_(old_session_ids)
            )
            invoice_ids = [row[0] for row in db.exec(invoices_query).all()]

            # 1. Delete logs belonging to these invoices
            if invoice_ids:
                log_stmt = delete(AutomationLog).where(
                    AutomationLog.automation_invoice_id.in_(invoice_ids)
                )
                db.exec(log_stmt)

            # 2. Delete invoices belonging to these sessions
            invoice_stmt = delete(AutomationInvoice).where(
                AutomationInvoice.excel_upload_session_id.in_(old_session_ids)
            )
            db.exec(invoice_stmt)

            # 3. Delete the sessions themselves
            session_stmt = delete(ExcelUploadSession).where(
                ExcelUploadSession.id.in_(old_session_ids)
            )
            db.exec(session_stmt)

            db.commit()
            logger.info(
                f"Cleaned up {len(old_session_ids)} completed upload session(s) "
                f"and their invoices from automation database"
            )

    except Exception as e:
        logger.error(f"Upload session cleanup failed: {e}", exc_info=True)


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

    # Transfer validated invoices every 5 minutes
    scheduler.add_job(
        transfer_validated_invoices,
        trigger=IntervalTrigger(seconds=300),
        id="transfer_invoices",
        name="Transfer validated invoices to main DB",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("  Scheduled: Invoice transfer every 5 minutes")

    scheduler.add_job(
        expire_pending_invoices,
        trigger="cron",
        hour=settings.cleanup_schedule_hour,
        minute=settings.cleanup_schedule_minute,
        id="expire_invoices",
        name="Expire pending invoices",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_old_logs,
        trigger="cron",
        hour=settings.cleanup_schedule_hour,
        minute=settings.cleanup_schedule_minute + 5,
        id="cleanup_logs",
        name="Cleanup old automation logs",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_completed_upload_sessions,
        trigger="cron",
        hour=settings.cleanup_schedule_hour,
        minute=settings.cleanup_schedule_minute + 10,
        id="cleanup_completed_sessions",
        name="Cleanup completed upload sessions older than retention period",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("AI-agent scheduler started")


def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("AI-agent scheduler stopped")
