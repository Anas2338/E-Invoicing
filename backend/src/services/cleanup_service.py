"""
Cleanup Service for removing old automation data.

This service handles the daily cleanup of old automation data at 2 AM PKT.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import logging

from sqlmodel import Session, select, delete
from sqlalchemy import and_

from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.excel_upload_session import ExcelUploadSession
from src.models.automation_log import AutomationLog

logger = logging.getLogger(__name__)


class CleanupResult:
    """Result of a cleanup operation."""

    def __init__(self):
        self.success = False
        self.invoices_deleted = 0
        self.sessions_deleted = 0
        self.logs_deleted = 0
        self.duration_seconds = 0.0
        self.error_message: Optional[str] = None


class CleanupService:
    """Service for cleaning up old automation data."""

    def __init__(self):
        """Initialize cleanup service."""
        pass

    def cleanup_old_automation_data(
        self,
        automation_db: Session,
        retention_days: int = 2
    ) -> CleanupResult:
        """
        Delete old automation invoices and upload sessions.

        Safety rules:
        - Only delete TRANSFERRED invoices (successful transfers)
        - Never delete TRANSFER_FAILED invoices (need manual review)
        - Never delete VALIDATED invoices waiting for transfer
        - Only delete data older than retention_days

        Args:
            automation_db: Automation database session
            retention_days: Number of days to retain data (default: 2)

        Returns:
            CleanupResult with operation details
        """
        result = CleanupResult()
        start_time = datetime.utcnow()

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            logger.info(f"Cleanup job started: deleting data older than {cutoff_date.isoformat()}")

            # Delete old TRANSFERRED invoices only (safe to delete)
            invoice_statement = delete(AutomationInvoice).where(
                and_(
                    AutomationInvoice.status == AutomationInvoiceStatus.TRANSFERRED,
                    AutomationInvoice.transferred_at < cutoff_date
                )
            )
            invoice_result = automation_db.exec(invoice_statement)
            result.invoices_deleted = invoice_result.rowcount
            automation_db.commit()

            logger.info(f"Deleted {result.invoices_deleted} old transferred invoices")

            # Delete old upload sessions
            # Only delete sessions where all invoices have been processed
            session_cutoff = datetime.utcnow() - timedelta(days=retention_days)
            session_statement = delete(ExcelUploadSession).where(
                ExcelUploadSession.created_at < session_cutoff
            )
            session_result = automation_db.exec(session_statement)
            result.sessions_deleted = session_result.rowcount
            automation_db.commit()

            logger.info(f"Deleted {result.sessions_deleted} old upload sessions")

            # Calculate duration
            end_time = datetime.utcnow()
            result.duration_seconds = (end_time - start_time).total_seconds()
            result.success = True

            logger.info(
                f"Cleanup job completed: {result.invoices_deleted} invoices, "
                f"{result.sessions_deleted} sessions deleted in {result.duration_seconds:.2f}s"
            )

        except Exception as e:
            logger.error(f"Cleanup job failed: {e}")
            result.success = False
            result.error_message = str(e)
            automation_db.rollback()

        return result

    def cleanup_old_logs(
        self,
        automation_db: Session,
        log_retention_days: int = 90
    ) -> CleanupResult:
        """
        Delete old automation logs.

        Logs are kept longer than other data for audit purposes.

        Args:
            automation_db: Automation database session
            log_retention_days: Number of days to retain logs (default: 90)

        Returns:
            CleanupResult with operation details
        """
        result = CleanupResult()
        start_time = datetime.utcnow()

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=log_retention_days)
            logger.info(f"Log cleanup started: deleting logs older than {cutoff_date.isoformat()}")

            # Delete old logs
            log_statement = delete(AutomationLog).where(
                AutomationLog.created_at < cutoff_date
            )
            log_result = automation_db.exec(log_statement)
            result.logs_deleted = log_result.rowcount
            automation_db.commit()

            logger.info(f"Deleted {result.logs_deleted} old automation logs")

            # Calculate duration
            end_time = datetime.utcnow()
            result.duration_seconds = (end_time - start_time).total_seconds()
            result.success = True

            logger.info(
                f"Log cleanup completed: {result.logs_deleted} logs deleted "
                f"in {result.duration_seconds:.2f}s"
            )

        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")
            result.success = False
            result.error_message = str(e)
            automation_db.rollback()

        return result

    def get_cleanup_stats(self, automation_db: Session) -> dict:
        """
        Get statistics about data eligible for cleanup.

        Args:
            automation_db: Automation database session

        Returns:
            Dictionary with cleanup statistics
        """
        try:
            # Count transferred invoices older than 2 days
            two_days_ago = datetime.utcnow() - timedelta(days=2)
            transferred_statement = select(AutomationInvoice).where(
                and_(
                    AutomationInvoice.status == AutomationInvoiceStatus.TRANSFERRED,
                    AutomationInvoice.transferred_at < two_days_ago
                )
            )
            transferred_count = len(automation_db.exec(transferred_statement).all())

            # Count failed invoices (should NOT be deleted)
            failed_statement = select(AutomationInvoice).where(
                AutomationInvoice.status == AutomationInvoiceStatus.TRANSFER_FAILED
            )
            failed_count = len(automation_db.exec(failed_statement).all())

            # Count old upload sessions
            old_sessions_statement = select(ExcelUploadSession).where(
                ExcelUploadSession.created_at < two_days_ago
            )
            old_sessions_count = len(automation_db.exec(old_sessions_statement).all())

            # Count old logs (90 days)
            ninety_days_ago = datetime.utcnow() - timedelta(days=90)
            old_logs_statement = select(AutomationLog).where(
                AutomationLog.created_at < ninety_days_ago
            )
            old_logs_count = len(automation_db.exec(old_logs_statement).all())

            return {
                "eligible_for_cleanup": {
                    "transferred_invoices": transferred_count,
                    "upload_sessions": old_sessions_count,
                    "logs": old_logs_count
                },
                "protected_from_cleanup": {
                    "failed_invoices": failed_count
                },
                "retention_policies": {
                    "invoices_and_sessions": "2 days",
                    "logs": "90 days"
                }
            }

        except Exception as e:
            logger.error(f"Failed to get cleanup stats: {e}")
            return {
                "error": str(e)
            }
