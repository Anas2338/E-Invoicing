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
                # Get eligible invoices (VALIDATED or TRANSFERRED status)
                invoices = db.query(Invoice).filter(
                    Invoice.user_id == user.id,
                    Invoice.status.in_([InvoiceStatus.VALIDATED, InvoiceStatus.TRANSFERRED]),
                    Invoice.is_deleted == False
                ).order_by(Invoice.created_at).limit(user.auto_posting_daily_limit).all()

                if not invoices:
                    continue

                logger.info(f"Processing {len(invoices)} invoices for user {user.id}")

                for invoice in invoices:
                    try:
                        # Post invoice to FBR using PostingService
                        is_posted, reference_number, response_data = await posting_service.post_single_invoice(
                            db=db,
                            invoice=invoice,
                            user_id=str(user.id)
                        )

                        if is_posted:
                            total_posted += 1
                            logger.info(f"Posted invoice {invoice.id} to FBR: {reference_number}")
                        else:
                            total_failed += 1
                            logger.warning(f"Failed to post invoice {invoice.id}: {response_data.get('error')}")

                    except Exception as e:
                        total_failed += 1
                        logger.error(f"Error posting invoice {invoice.id}: {e}")

            logger.info(f"Auto-posting completed: {total_posted} posted, {total_failed} failed")

    except Exception as e:
        logger.error(f"Auto-posting job error: {e}", exc_info=True)

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

    scheduler.start()
    logger.info("Scheduler started with auto-posting job (runs every 5 minutes)")

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
