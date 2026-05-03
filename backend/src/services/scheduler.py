"""
Scheduler Service for automated background jobs.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone
from datetime import datetime, time as dt_time
from uuid import UUID

from src.config.settings import settings
from src.database.session import get_db_session, get_automation_db_session
from src.services.transfer_service import TransferService
from src.services.cleanup_service import CleanupService
from src.services.auto_posting_service import AutoPostingService
from src.models.user import User
from src.models.invoice import Invoice, InvoiceStatus
from sqlalchemy import select, and_

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


async def auto_posting_job():
    """Job to automatically post eligible invoices to FBR (runs every 5 minutes)."""
    logger.info("Starting auto-posting job...")
    try:
        with get_db_session() as db:
            auto_service = AutoPostingService(db)
            current_datetime = datetime.now(PAKISTAN_TZ)
            current_time = current_datetime.time()

            # Get all users with auto-posting enabled
            # Use query() instead of exec() to ensure we get User model instances
            users = db.query(User).filter(
                User.auto_posting_enabled == True,
                (User.auto_posting_paused_until == None) |
                (User.auto_posting_paused_until < current_datetime)
            ).all()

            if not users:
                logger.info("No users with auto-posting enabled")
                return

            eligible_users = []
            for user in users:
                # Check if within time window
                if not auto_service.is_within_time_window(
                    current_time,
                    user.auto_posting_start_time,
                    user.auto_posting_end_time
                ):
                    continue

                # Check daily limit
                remaining = auto_service.get_daily_limit_remaining(user, current_datetime)
                if remaining <= 0:
                    continue

                eligible_users.append(user)

            logger.info(f"Found {len(eligible_users)} users eligible for auto-posting")

            total_posted = 0
            total_failed = 0

            # Import PostingService for actual posting
            from src.services.posting_service import PostingService
            posting_service = PostingService()

            # Process each eligible user
            for user in eligible_users:
                # Get eligible invoices (VALIDATED or TRANSFERRED status)
                # Use query() instead of exec() to ensure we get Invoice model instances
                invoices = db.query(Invoice).filter(
                    Invoice.user_id == user.id,
                    Invoice.status.in_([InvoiceStatus.VALIDATED, InvoiceStatus.TRANSFERRED]),
                    Invoice.is_deleted == False
                ).order_by(Invoice.created_at).limit(10).all()

                if not invoices:
                    continue

                logger.info(f"Processing {len(invoices)} invoices for user {user.id}")

                # Check remaining limit for this user
                remaining = auto_service.get_daily_limit_remaining(user, current_datetime)

                for invoice in invoices[:remaining]:
                    try:
                        # Post invoice to FBR using PostingService
                        is_posted, reference_number, response_data = await posting_service.post_single_invoice(
                            db=db,
                            invoice=invoice,
                            user_id=str(user.id)
                        )

                        if is_posted:
                            total_posted += 1
                            # Increment daily counter
                            auto_service.increment_daily_counter(
                                user.id,
                                current_datetime,
                                user.auto_posting_start_time,
                                user.auto_posting_end_time
                            )
                            # Create posting log
                            auto_service.create_posting_log(
                                user_id=user.id,
                                invoice_id=invoice.id,
                                action='auto',
                                result='success',
                                environment=user.auto_posting_environment
                            )
                            logger.info(f"Posted invoice {invoice.id} to FBR: {reference_number}")
                        else:
                            total_failed += 1
                            # Create posting log
                            auto_service.create_posting_log(
                                user_id=user.id,
                                invoice_id=invoice.id,
                                action='auto',
                                result='failure',
                                environment=user.auto_posting_environment,
                                error_details=response_data
                            )
                            logger.warning(f"Failed to post invoice {invoice.id}: {response_data.get('error')}")

                    except Exception as e:
                        total_failed += 1
                        # Create posting log
                        auto_service.create_posting_log(
                            user_id=user.id,
                            invoice_id=invoice.id,
                            action='auto',
                            result='failure',
                            environment=user.auto_posting_environment,
                            error_details={"error": str(e)}
                        )
                        logger.error(f"Error posting invoice {invoice.id}: {e}")

            # Close posting service
            await posting_service.close()

            logger.info(f"Auto-posting completed: {total_posted} posted, {total_failed} failed")

    except Exception as e:
        logger.error(f"Auto-posting job error: {e}", exc_info=True)

def start_scheduler():
    """Start the scheduler with all background jobs."""
    global scheduler
    if scheduler is not None:
        return

    scheduler = AsyncIOScheduler(timezone=PAKISTAN_TZ)

    # NOTE: Daily transfer job REMOVED - AI Agent now transfers invoices every 5 minutes
    # when their scheduled time arrives (real-time transfer based on invoice schedule)

    # Job 1: Auto-posting to FBR (every 5 minutes)
    scheduler.add_job(
        auto_posting_job,
        trigger=IntervalTrigger(minutes=5),
        id='auto_posting',
        name='Auto Post to FBR',
        replace_existing=True,
        max_instances=1
    )

    # Job 2: Cleanup old automation data (daily at 2 AM PKT)
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

    # Job 3: Cleanup old logs (daily at 2:30 AM PKT)
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
        f"Scheduler started with 3 jobs:\n"
        f"  - Auto-posting: Every 5 minutes\n"
        f"  - Cleanup Data: Daily at {settings.cleanup_schedule_hour}:{settings.cleanup_schedule_minute:02d} PKT\n"
        f"  - Cleanup Logs: Daily at {settings.cleanup_schedule_hour}:{settings.cleanup_schedule_minute + 30:02d} PKT\n"
        f"  Note: Invoice transfer handled by AI Agent every 5 minutes (real-time based on schedule)"
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
