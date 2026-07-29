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
from src.database.session import get_db_session
from src.services.auto_posting_service import AutoPostingService
from src.models.user import User
from src.models.invoice import Invoice, InvoiceStatus
from src.models.fbr_notifications import FBRChangeNotification
from src.models.posting_log import PostingLog
from src.models.bulk_operation import BulkOperationTask
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)
PAKISTAN_TZ = timezone('Asia/Karachi')
scheduler = None
async def auto_posting_job():
    """Job to automatically post eligible invoices to FBR (runs every 5 minutes)."""
    logger.info("Starting auto-posting job...")
    try:
        with get_db_session() as db:
            auto_service = AutoPostingService(db)
            current_datetime = datetime.now(PAKISTAN_TZ)
            current_time = current_datetime.time()

            # Get all users with auto-posting enabled
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

                eligible_users.append(user)

            logger.info(f"Found {len(eligible_users)} users eligible for auto-posting")

            total_posted = 0
            total_failed = 0

            # Import PostingService for actual posting
            from src.services.posting_service import PostingService
            posting_service = PostingService()

            # Process each eligible user
            for user in eligible_users:
                # Get eligible invoices (VALIDATED status includes transferred-from-automation)
                invoices = db.query(Invoice).filter(
                    Invoice.user_id == user.id,
                    Invoice.status == InvoiceStatus.VALIDATED,
                    Invoice.is_deleted == False
                ).order_by(Invoice.created_at).limit(user.auto_posting_daily_limit).all()

                if not invoices:
                    continue

                logger.info(f"Processing {len(invoices)} invoices for user {user.id}")

                for invoice in invoices:
                    try:
                        # Post invoice to FBR using PostingService
                        # Pass user's auto-posting environment so token is selected
                        # based on user's configured preference, not invoice.environment
                        is_posted, reference_number, response_data = await posting_service.post_single_invoice(
                            db=db,
                            invoice=invoice,
                            user_id=str(user.id),
                            posting_environment=user.auto_posting_environment,
                        )

                        if is_posted:
                            total_posted += 1
                            # Create posting log and increment daily counter
                            auto_service.create_posting_log(
                                user_id=user.id,
                                invoice_id=invoice.id,
                                action='auto',
                                result='success',
                                environment=user.auto_posting_environment,
                            )
                            auto_service.increment_daily_counter(
                                user.id,
                                current_datetime,
                                user.auto_posting_start_time,
                                user.auto_posting_end_time,
                            )
                            logger.info(f"Posted invoice {invoice.id} to FBR: {reference_number}")
                        else:
                            total_failed += 1
                            error_msg = response_data.get('error', 'Posting failed') if isinstance(response_data, dict) else str(response_data)
                            auto_service.create_posting_log(
                                user_id=user.id,
                                invoice_id=invoice.id,
                                action='auto',
                                result='failure',
                                environment=user.auto_posting_environment,
                                error_details={'error': error_msg},
                            )
                            logger.warning(f"Failed to post invoice {invoice.id}: {error_msg}")

                    except Exception as e:
                        total_failed += 1
                        auto_service.create_posting_log(
                            user_id=user.id,
                            invoice_id=invoice.id,
                            action='auto',
                            result='failure',
                            environment=user.auto_posting_environment,
                            error_details={'error': str(e)},
                        )
                        logger.error(f"Error posting invoice {invoice.id}: {e}")

            logger.info(f"Auto-posting completed: {total_posted} posted, {total_failed} failed")

    except Exception as e:
        logger.error(f"Auto-posting job error: {e}", exc_info=True)


def cleanup_old_notifications_job():
    """Delete FBR change notifications older than 2 days."""
    logger.info("Starting old notification cleanup...")
    try:
        with get_db_session() as db:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=2)
            result = db.query(FBRChangeNotification).filter(
                FBRChangeNotification.created_at < cutoff
            ).delete()
            db.commit()
            if result > 0:
                logger.info(f"Deleted {result} old notification(s) older than 2 days")
            else:
                logger.info("No old notifications to clean up")
    except Exception as e:
        logger.error(f"Notification cleanup job error: {e}", exc_info=True)


def cleanup_old_posting_logs_job():
    """Delete posting logs older than 15 days."""
    logger.info("Starting old posting log cleanup...")
    try:
        with get_db_session() as db:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=15)
            result = db.query(PostingLog).filter(
                PostingLog.created_at < cutoff
            ).delete()
            db.commit()
            if result > 0:
                logger.info(f"Deleted {result} old posting log(s) older than 15 days")
            else:
                logger.info("No old posting logs to clean up")
    except Exception as e:
        logger.error(f"Posting log cleanup job error: {e}", exc_info=True)


def cleanup_bulk_operation_tasks_job():
    """Delete completed bulk operation tasks older than 1 hour."""
    logger.info("Starting bulk operation task cleanup...")
    try:
        with get_db_session() as db:
            from datetime import timedelta
            from src.models.bulk_operation import BulkOperationStatus
            cutoff = datetime.utcnow() - timedelta(hours=1)
            result = db.query(BulkOperationTask).filter(
                BulkOperationTask.status != BulkOperationStatus.PROCESSING,
                BulkOperationTask.completed_at < cutoff
            ).delete()
            db.commit()
            if result > 0:
                logger.info(f"Deleted {result} old bulk operation task(s) completed >1 hour ago")
            else:
                logger.info("No old bulk operation tasks to clean up")
    except Exception as e:
        logger.error(f"Bulk operation task cleanup job error: {e}", exc_info=True)


def start_scheduler():
    """Start the scheduler with all background jobs."""
    global scheduler
    if scheduler is not None:
        return

    scheduler = AsyncIOScheduler(timezone=PAKISTAN_TZ)

    # Job: Auto-posting to FBR (every 5 minutes)
    scheduler.add_job(
        auto_posting_job,
        trigger=IntervalTrigger(minutes=5),
        id='auto_posting',
        name='Auto Post to FBR',
        replace_existing=True,
        max_instances=1
    )

    # Job: Clean up old FBR change notifications (daily at 3:00 AM PKT)
    scheduler.add_job(
        cleanup_old_notifications_job,
        trigger=CronTrigger(hour=3, minute=0, timezone=PAKISTAN_TZ),
        id='cleanup_old_notifications',
        name='Clean Up Old Notifications',
        replace_existing=True,
    )

    # Job: Clean up old posting logs (daily at 3:30 AM PKT)
    scheduler.add_job(
        cleanup_old_posting_logs_job,
        trigger=CronTrigger(hour=3, minute=30, timezone=PAKISTAN_TZ),
        id='cleanup_old_posting_logs',
        name='Clean Up Old Posting Logs',
        replace_existing=True,
    )

    # Job: Clean up completed bulk operation tasks (every 30 minutes)
    scheduler.add_job(
        cleanup_bulk_operation_tasks_job,
        trigger=IntervalTrigger(minutes=30),
        id='cleanup_bulk_operation_tasks',
        name='Clean Up Old Bulk Operation Tasks',
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with auto-posting, notification, posting log, and bulk task cleanup jobs")

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
