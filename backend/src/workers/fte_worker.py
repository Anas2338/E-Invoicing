"""
FTE Worker - Hourly background worker for automated invoice processing.

This worker runs every hour and processes pending invoices scheduled for that hour.
It validates invoices, submits them to FBR, and updates Excel files with results.

Usage:
    uv run python -m src.workers.fte_worker
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.database.session import get_db_session
from src.services.fte_worker_service import FTEWorkerService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fte_worker.log')
    ]
)

logger = logging.getLogger(__name__)


async def process_invoices_job():
    """
    Main job function that processes pending invoices.
    Called by APScheduler every hour.
    """
    logger.info("=" * 80)
    logger.info("FTE Worker: Starting hourly invoice processing job")
    logger.info("=" * 80)

    try:
        # Create database session
        with get_db_session() as db:
            # Initialize FTE worker service
            worker_service = FTEWorkerService(db)

            # Process pending invoices
            stats = await worker_service.process_pending_invoices()

            # Log summary
            logger.info("=" * 80)
            logger.info("FTE Worker: Job completed successfully")
            logger.info(f"  Total processed: {stats['total_processed']}")
            logger.info(f"  Validated: {stats['validated']}")
            logger.info(f"  Submitted: {stats['submitted']}")
            logger.info(f"  Failed: {stats['failed']}")

            if stats['errors']:
                logger.warning(f"  Errors encountered: {len(stats['errors'])}")
                for error in stats['errors']:
                    logger.warning(f"    - Invoice {error['invoice_number']}: {error['error']}")

            logger.info("=" * 80)

    except Exception as e:
        logger.error(f"FTE Worker: Fatal error in job execution: {str(e)}", exc_info=True)
        raise


def run_job_sync():
    """
    Synchronous wrapper for the async job function.
    Required by APScheduler which doesn't natively support async.
    """
    asyncio.run(process_invoices_job())


def main():
    """
    Main entry point for FTE worker.
    Sets up APScheduler and starts the worker.
    """
    logger.info("FTE Worker: Initializing...")

    # Create scheduler
    scheduler = BlockingScheduler()

    # Schedule job to run every hour at minute 0
    # Cron format: minute hour day month day_of_week
    # '0 * * * *' means: at minute 0 of every hour
    scheduler.add_job(
        run_job_sync,
        trigger=CronTrigger(minute=0),
        id='process_invoices',
        name='Process Pending Invoices',
        replace_existing=True,
        max_instances=1  # Prevent concurrent runs
    )

    logger.info("FTE Worker: Scheduler configured")
    logger.info("  Schedule: Every hour at minute 0 (cron: 0 * * * *)")
    logger.info("FTE Worker: Starting scheduler...")

    try:
        # Start the scheduler (blocks until interrupted)
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("FTE Worker: Shutdown signal received")
        scheduler.shutdown()
        logger.info("FTE Worker: Stopped")


if __name__ == "__main__":
    main()
