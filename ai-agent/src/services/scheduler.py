"""Scheduler for automation background jobs."""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

from src.config.settings import settings
from src.database.session import get_automation_db_session

logger = logging.getLogger(__name__)
PAKISTAN_TZ = timezone("Asia/Karachi")
scheduler = None


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
            stmt = delete(AutomationLog).where(AutomationLog.created_at < cutoff)
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

    scheduler.start()
    logger.info("AI-agent scheduler started")


def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("AI-agent scheduler stopped")
