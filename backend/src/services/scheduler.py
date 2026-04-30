"""
Scheduler Service for automated background jobs.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from src.config.settings import settings
from src.database.session import get_db_session, get_automation_db_session
from src.services.transfer_service import TransferService
from src.services.cleanup_service import CleanupService

logger = logging.getLogger(__name__)
PAKISTAN_TZ = timezone('Asia/Karachi')
scheduler = None

async def transfer_validated_invoices_job():
    """Daily job to transfer validated invoices from automation DB to main DB."""
    logger.info("Starting scheduled transfer job...")
    try:
        with get_automation_db_session() as automation_db:
            with get_db_session() as main_db:
                transfer_service = TransferService()
                result = await transfer_service.transfer_validated_invoices(
                    automation_db=automation_db,
                    main_db=main_db,
                    triggered_by="scheduled",
                    triggered_by_user_id=None
                )
                if result.success:
                    logger.info(f"Transfer completed: {result.invoices_transferred} transferred")
                else:
                    logger.error(f"Transfer failed: {result.error_message}")
    except Exception as e:
        logger.error(f"Transfer job error: {e}", exc_info=True)


async def cleanup_automation_data_job():
    """Daily job to clean up old automation data."""
    logger.info("Starting scheduled cleanup job...")
    try:
        with get_automation_db_session() as automation_db:
            cleanup_service = CleanupService()

            # Clean up old invoices and sessions
            result = cleanup_service.cleanup_old_automation_data(
                automation_db=automation_db,
                retention_days=settings.cleanup_retention_days
            )

            if result.success:
                logger.info(
                    f"Cleanup completed: {result.invoices_deleted} invoices, "
                    f"{result.sessions_deleted} sessions deleted"
                )
            else:
                logger.error(f"Cleanup failed: {result.error_message}")

    except Exception as e:
        logger.error(f"Cleanup job error: {e}", exc_info=True)


async def cleanup_automation_logs_job():
    """Daily job to clean up old automation logs."""
    logger.info("Starting scheduled log cleanup job...")
    try:
        with get_automation_db_session() as automation_db:
            cleanup_service = CleanupService()

            # Clean up old logs
            result = cleanup_service.cleanup_old_logs(
                automation_db=automation_db,
                log_retention_days=settings.automation_log_retention_days
            )

            if result.success:
                logger.info(f"Log cleanup completed: {result.logs_deleted} logs deleted")
            else:
                logger.error(f"Log cleanup failed: {result.error_message}")

    except Exception as e:
        logger.error(f"Log cleanup job error: {e}", exc_info=True)

def start_scheduler():
    """Start the scheduler with all background jobs."""
    global scheduler
    if scheduler is not None:
        return

    scheduler = AsyncIOScheduler(timezone=PAKISTAN_TZ)

    # NOTE: Daily transfer job REMOVED - AI Agent now transfers invoices every 5 minutes
    # when their scheduled time arrives (real-time transfer based on invoice schedule)

    # Job 1: Cleanup old automation data (daily at 2 AM PKT)
    scheduler.add_job(
        cleanup_automation_data_job,
        trigger=CronTrigger(
            hour=settings.cleanup_schedule_hour,
            minute=settings.cleanup_schedule_minute,
            timezone=PAKISTAN_TZ
        ),
        id='cleanup_automation_data',
        name='Cleanup Old Automation Data',
        replace_existing=True,
        max_instances=1
    )

    # Job 2: Cleanup old logs (daily at 2:30 AM PKT)
    scheduler.add_job(
        cleanup_automation_logs_job,
        trigger=CronTrigger(
            hour=settings.cleanup_schedule_hour,
            minute=settings.cleanup_schedule_minute + 30,
            timezone=PAKISTAN_TZ
        ),
        id='cleanup_automation_logs',
        name='Cleanup Old Automation Logs',
        replace_existing=True,
        max_instances=1
    )

    scheduler.start()
    logger.info(
        f"Scheduler started with 2 jobs:\n"
        f"  - Cleanup Data: Daily at {settings.cleanup_schedule_hour}:{settings.cleanup_schedule_minute:02d} PKT\n"
        f"  - Cleanup Logs: Daily at {settings.cleanup_schedule_hour}:{settings.cleanup_schedule_minute + 30:02d} PKT\n"
        f"  Note: Invoice transfer now handled by AI Agent every 5 minutes (real-time based on schedule)"
    )

def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=True)
        scheduler = None


def get_scheduler_status() -> dict:
    """
    Get the current status of the scheduler.

    Returns:
        Dictionary with scheduler status information
    """
    global scheduler

    if scheduler is None:
        return {
            "running": False,
            "jobs": []
        }

    jobs_info = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            })

    return {
        "running": scheduler.running if scheduler else False,
        "jobs": jobs_info
    }
