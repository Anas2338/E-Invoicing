"""
Transfer Service for moving validated invoices from automation DB to main DB.

This service handles the daily transfer of validated invoices at 6 PM PKT.
"""

import os
from datetime import datetime, date, timedelta
from typing import Optional, List
from uuid import UUID
import logging
import json
import traceback

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, OperationalError, DatabaseError

from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.invoice import Invoice, InvoiceStatus
from src.models.transfer_log import TransferLog
from src.models.excel_upload_session import ExcelUploadSession

logger = logging.getLogger(__name__)


class TransferResult:
    """Result of a transfer operation."""

    def __init__(self):
        self.success = False
        self.invoices_transferred = 0
        self.invoices_failed = 0
        self.duration_seconds = 0.0
        self.transfer_log_id: Optional[UUID] = None
        self.failed_invoice_ids: List[UUID] = []
        self.error_message: Optional[str] = None


class TransferService:
    """Service for transferring validated invoices from automation to main database."""

    def __init__(self):
        """Initialize transfer service."""
        pass

    def classify_error(self, error: Exception) -> str:
        """
        Classify error as transient or permanent.

        Transient errors can be retried (network issues, temporary database problems).
        Permanent errors should not be retried (data validation, integrity violations).

        Args:
            error: The exception that occurred

        Returns:
            "transient" or "permanent"
        """
        # Permanent errors - should not be retried (check first, more specific)
        permanent_errors = (
            IntegrityError,    # Constraint violations, duplicates
            ValueError,        # Data validation errors
            KeyError,          # Missing required fields
        )

        # Transient errors - can be retried
        transient_errors = (
            OperationalError,  # Database connection issues
            DatabaseError,     # Temporary database problems (base class, check after IntegrityError)
        )

        # Check permanent errors first (more specific)
        if isinstance(error, permanent_errors):
            return "permanent"
        elif isinstance(error, transient_errors):
            return "transient"
        else:
            # Unknown errors treated as transient (can retry once to see)
            return "transient"

    def transform_invoice_data(self, automation_invoice: AutomationInvoice) -> Invoice:
        """
        Transform automation invoice JSON data to structured Invoice model.

        Args:
            automation_invoice: Source automation invoice

        Returns:
            Transformed Invoice model ready for main database
        """
        invoice_data = automation_invoice.invoice_data

        # Create Invoice with structured fields
        # NOTE: source="manual" makes transferred invoices appear identical to manually created ones
        # Audit trail preserved via automation_invoice_id and transferred_at fields
        invoice = Invoice(
            external_id=automation_invoice.invoice_number,
            user_id=automation_invoice.user_id,
            invoice_type=invoice_data.get("invoice_type", "Sale Invoice"),
            invoice_date=invoice_data.get("invoice_date"),
            seller_ntn_cnic=invoice_data.get("seller_ntn_cnic"),
            seller_business_name=invoice_data.get("seller_business_name"),
            seller_province=invoice_data.get("seller_province"),
            seller_address=invoice_data.get("seller_address"),
            buyer_ntn_cnic=invoice_data.get("buyer_ntn_cnic"),
            buyer_business_name=invoice_data.get("buyer_business_name"),
            buyer_province=invoice_data.get("buyer_province"),
            buyer_address=invoice_data.get("buyer_address"),
            buyer_registration_type=invoice_data.get("buyer_registration_type", "Registered"),
            invoice_ref_no=invoice_data.get("invoice_ref_no"),
            scenario_id=invoice_data.get("scenario_id"),
            items=invoice_data.get("items", []),
            environment=invoice_data.get("environment", "SANDBOX"),
            status=InvoiceStatus.VALIDATED,
            # Transfer tracking fields - source="manual" for seamless UI integration
            source="manual",  # Changed from "automation" to merge with manual invoices
            transferred_at=datetime.utcnow(),  # Audit trail: when transferred
            automation_invoice_id=automation_invoice.id,  # Audit trail: original automation invoice
            # Copy FBR validation response
            validation_errors=None,
            fbr_response_id=None
        )

        return invoice

    def check_duplicate(
        self,
        main_db: Session,
        user_id: UUID,
        automation_invoice_id: UUID
    ) -> bool:
        """
        Check if invoice has already been transferred.

        Args:
            main_db: Main database session
            user_id: User ID
            automation_invoice_id: Automation invoice ID

        Returns:
            True if duplicate exists, False otherwise
        """
        statement = select(Invoice).where(
            Invoice.user_id == user_id,
            Invoice.automation_invoice_id == automation_invoice_id
        )
        existing = main_db.exec(statement).first()
        return existing is not None

    def cleanup_excel_files_for_completed_sessions(self, automation_db: Session) -> int:
        """
        Automatically delete Excel files for sessions where all invoices are transferred.

        This runs after the transfer job to clean up Excel files that are no longer needed.
        The session records remain for audit purposes.

        Args:
            automation_db: Automation database session

        Returns:
            Number of Excel files deleted
        """
        deleted_count = 0

        try:
            # Get all sessions that have a file_path
            sessions_with_files = automation_db.exec(
                select(ExcelUploadSession).where(
                    ExcelUploadSession.file_path.isnot(None)
                )
            ).all()

            for session in sessions_with_files:
                # Get all invoices for this session
                invoices = automation_db.exec(
                    select(AutomationInvoice).where(
                        AutomationInvoice.excel_upload_session_id == session.id
                    )
                ).all()

                if not invoices:
                    continue

                # Check if all invoices are transferred
                all_transferred = all(
                    invoice.status == AutomationInvoiceStatus.TRANSFERRED
                    for invoice in invoices
                )

                if all_transferred and session.file_path:
                    # Delete the Excel file from disk
                    if os.path.exists(session.file_path):
                        try:
                            os.remove(session.file_path)
                            logger.info(f"Auto-deleted Excel file: {session.file_path}")
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete Excel file {session.file_path}: {e}")
                            continue

                    # Update session to remove file_path
                    session.file_path = None
                    automation_db.add(session)

            automation_db.commit()

            if deleted_count > 0:
                logger.info(f"Auto-cleanup: deleted {deleted_count} Excel files for completed sessions")

        except Exception as e:
            logger.error(f"Excel file auto-cleanup failed: {e}")
            automation_db.rollback()

        return deleted_count

    async def transfer_validated_invoices(
        self,
        automation_db: Session,
        main_db: Session,
        triggered_by: str = "scheduled",
        triggered_by_user_id: Optional[UUID] = None
    ) -> TransferResult:
        """
        Transfer validated invoices from last 24 hours from automation DB to main DB.

        This is the main transfer operation that runs daily at 6 PM PKT.
        Only transfers invoices with scheduled_date from the last 24 hours.

        Args:
            automation_db: Automation database session
            main_db: Main database session
            triggered_by: How transfer was triggered ("scheduled" or "manual")
            triggered_by_user_id: User ID if manually triggered

        Returns:
            TransferResult with operation details
        """
        result = TransferResult()
        start_time = datetime.utcnow()
        failed_invoice_ids = []

        try:
            # Calculate 24-hour window for scheduled dates
            # Transfer invoices scheduled in the last 24 hours
            now = datetime.utcnow()
            yesterday = (now - timedelta(hours=24)).date()
            today = now.date()

            # Query validated invoices with scheduled_date in last 24 hours
            statement = select(AutomationInvoice).where(
                AutomationInvoice.status == AutomationInvoiceStatus.VALIDATED,
                AutomationInvoice.scheduled_date >= yesterday,
                AutomationInvoice.scheduled_date <= today
            )

            invoices_to_transfer = automation_db.exec(statement).all()

            logger.info(f"Transfer job started: {len(invoices_to_transfer)} invoices to transfer")

            # Process each invoice
            for auto_invoice in invoices_to_transfer:
                try:
                    # Check for duplicate
                    if self.check_duplicate(main_db, auto_invoice.user_id, auto_invoice.id):
                        logger.warning(f"Duplicate detected: invoice {auto_invoice.id} already transferred")
                        auto_invoice.status = AutomationInvoiceStatus.TRANSFERRED
                        auto_invoice.transferred_at = datetime.utcnow()
                        auto_invoice.transfer_error = "Duplicate - already transferred"
                        automation_db.add(auto_invoice)
                        result.invoices_failed += 1
                        failed_invoice_ids.append(auto_invoice.id)
                        continue

                    # Transform to manual invoice
                    manual_invoice = self.transform_invoice_data(auto_invoice)

                    # Insert into main database
                    main_db.add(manual_invoice)
                    main_db.flush()  # Get ID without committing

                    # Update automation invoice status
                    auto_invoice.status = AutomationInvoiceStatus.TRANSFERRED
                    auto_invoice.transferred_at = datetime.utcnow()
                    auto_invoice.transfer_error = None
                    automation_db.add(auto_invoice)

                    # Commit both databases
                    main_db.commit()
                    automation_db.commit()

                    result.invoices_transferred += 1
                    logger.debug(f"Transferred invoice {auto_invoice.id} -> {manual_invoice.id}")

                except IntegrityError as e:
                    # Rollback both sessions
                    main_db.rollback()
                    automation_db.rollback()

                    # Classify error and log with stack trace
                    error_type = self.classify_error(e)
                    error_details = f"[{error_type}] Integrity error: {str(e)}"
                    stack_trace = traceback.format_exc()
                    logger.error(f"Transfer failed for invoice {auto_invoice.id}: {error_details}\n{stack_trace}")

                    # Mark as failed
                    auto_invoice.status = AutomationInvoiceStatus.TRANSFER_FAILED
                    auto_invoice.transfer_error = error_details[:2000]  # Truncate to field length
                    automation_db.add(auto_invoice)
                    automation_db.commit()

                    result.invoices_failed += 1
                    failed_invoice_ids.append(auto_invoice.id)

                except Exception as e:
                    # Rollback both sessions
                    main_db.rollback()
                    automation_db.rollback()

                    # Classify error and log with stack trace
                    error_type = self.classify_error(e)
                    error_details = f"[{error_type}] {type(e).__name__}: {str(e)}"
                    stack_trace = traceback.format_exc()
                    logger.error(f"Transfer failed for invoice {auto_invoice.id}: {error_details}\n{stack_trace}")

                    # Mark as failed
                    auto_invoice.status = AutomationInvoiceStatus.TRANSFER_FAILED
                    auto_invoice.transfer_error = error_details[:2000]  # Truncate to field length
                    automation_db.add(auto_invoice)
                    automation_db.commit()

                    result.invoices_failed += 1
                    failed_invoice_ids.append(auto_invoice.id)


            # Calculate duration
            end_time = datetime.utcnow()
            result.duration_seconds = (end_time - start_time).total_seconds()

            # Determine overall status
            if result.invoices_failed == 0:
                status = "success"
                result.success = True
            elif result.invoices_transferred > 0:
                status = "partial_success"
                result.success = True
            else:
                status = "failed"
                result.success = False

            # Create transfer log
            transfer_log = TransferLog(
                transfer_timestamp=start_time,
                status=status,
                invoices_transferred=result.invoices_transferred,
                invoices_failed=result.invoices_failed,
                duration_seconds=result.duration_seconds,
                triggered_by=triggered_by,
                triggered_by_user_id=triggered_by_user_id,
                error_details=None,
                failed_invoice_ids=json.dumps([str(id) for id in failed_invoice_ids]) if failed_invoice_ids else None
            )
            automation_db.add(transfer_log)
            automation_db.commit()

            result.transfer_log_id = transfer_log.id
            result.failed_invoice_ids = failed_invoice_ids

            logger.info(
                f"Transfer job completed: {result.invoices_transferred} transferred, "
                f"{result.invoices_failed} failed, {result.duration_seconds:.2f}s"
            )

            # Auto-cleanup Excel files for fully transferred sessions
            try:
                self.cleanup_excel_files_for_completed_sessions(automation_db)
            except Exception as cleanup_error:
                logger.error(f"Excel file cleanup failed (non-critical): {cleanup_error}")

        except Exception as e:
            logger.error(f"Transfer job failed: {e}")
            result.success = False
            result.error_message = str(e)

            # Try to log the failure
            try:
                end_time = datetime.utcnow()
                result.duration_seconds = (end_time - start_time).total_seconds()

                transfer_log = TransferLog(
                    transfer_timestamp=start_time,
                    status="failed",
                    invoices_transferred=result.invoices_transferred,
                    invoices_failed=result.invoices_failed,
                    duration_seconds=result.duration_seconds,
                    triggered_by=triggered_by,
                    triggered_by_user_id=triggered_by_user_id,
                    error_details=str(e)[:2000],
                    failed_invoice_ids=None
                )
                automation_db.add(transfer_log)
                automation_db.commit()
                result.transfer_log_id = transfer_log.id
            except Exception as log_error:
                logger.error(f"Failed to log transfer failure: {log_error}")

        return result

    async def retry_failed_transfers(
        self,
        automation_db: Session,
        main_db: Session,
        invoice_ids: Optional[List[UUID]] = None,
        triggered_by_user_id: Optional[UUID] = None
    ) -> TransferResult:
        """
        Retry previously failed invoice transfers.

        Args:
            automation_db: Automation database session
            main_db: Main database session
            invoice_ids: Optional list of specific invoice IDs to retry. If None, retry all failed.
            triggered_by_user_id: User ID who triggered the retry

        Returns:
            TransferResult with retry operation details
        """
        result = TransferResult()
        start_time = datetime.utcnow()
        failed_invoice_ids = []

        try:
            # Query failed invoices
            statement = select(AutomationInvoice).where(
                AutomationInvoice.status == AutomationInvoiceStatus.TRANSFER_FAILED
            )

            # Filter by specific IDs if provided
            if invoice_ids:
                statement = statement.where(AutomationInvoice.id.in_(invoice_ids))

            invoices_to_retry = automation_db.exec(statement).all()

            logger.info(f"Retry job started: {len(invoices_to_retry)} invoices to retry")

            # Process each invoice
            for auto_invoice in invoices_to_retry:
                try:
                    # Check if error was permanent (don't retry permanent errors)
                    if auto_invoice.transfer_error and "[permanent]" in auto_invoice.transfer_error.lower():
                        logger.warning(f"Skipping invoice {auto_invoice.id}: permanent error")
                        result.invoices_failed += 1
                        failed_invoice_ids.append(auto_invoice.id)
                        continue

                    # Check for duplicate (in case it was transferred elsewhere)
                    if self.check_duplicate(main_db, auto_invoice.user_id, auto_invoice.id):
                        logger.warning(f"Duplicate detected: invoice {auto_invoice.id} already transferred")
                        auto_invoice.status = AutomationInvoiceStatus.TRANSFERRED
                        auto_invoice.transferred_at = datetime.utcnow()
                        auto_invoice.transfer_error = "Duplicate - already transferred"
                        automation_db.add(auto_invoice)
                        automation_db.commit()
                        result.invoices_transferred += 1
                        continue

                    # Transform to manual invoice
                    manual_invoice = self.transform_invoice_data(auto_invoice)

                    # Insert into main database
                    main_db.add(manual_invoice)
                    main_db.flush()  # Get ID without committing

                    # Update automation invoice status
                    auto_invoice.status = AutomationInvoiceStatus.TRANSFERRED
                    auto_invoice.transferred_at = datetime.utcnow()
                    auto_invoice.transfer_error = None  # Clear previous error
                    automation_db.add(auto_invoice)

                    # Commit both databases
                    main_db.commit()
                    automation_db.commit()

                    result.invoices_transferred += 1
                    logger.info(f"Retry successful: invoice {auto_invoice.id} -> {manual_invoice.id}")

                except IntegrityError as e:
                    # Rollback both sessions
                    main_db.rollback()
                    automation_db.rollback()

                    # Classify error and log with stack trace
                    error_type = self.classify_error(e)
                    error_details = f"[{error_type}] Integrity error: {str(e)}"
                    stack_trace = traceback.format_exc()
                    logger.error(f"Retry failed for invoice {auto_invoice.id}: {error_details}\n{stack_trace}")

                    # Update error details (keep TRANSFER_FAILED status)
                    auto_invoice.transfer_error = error_details[:2000]
                    automation_db.add(auto_invoice)
                    automation_db.commit()

                    result.invoices_failed += 1
                    failed_invoice_ids.append(auto_invoice.id)

                except Exception as e:
                    # Rollback both sessions
                    main_db.rollback()
                    automation_db.rollback()

                    # Classify error and log with stack trace
                    error_type = self.classify_error(e)
                    error_details = f"[{error_type}] {type(e).__name__}: {str(e)}"
                    stack_trace = traceback.format_exc()
                    logger.error(f"Retry failed for invoice {auto_invoice.id}: {error_details}\n{stack_trace}")

                    # Update error details (keep TRANSFER_FAILED status)
                    auto_invoice.transfer_error = error_details[:2000]
                    automation_db.add(auto_invoice)
                    automation_db.commit()

                    result.invoices_failed += 1
                    failed_invoice_ids.append(auto_invoice.id)

            # Calculate duration
            end_time = datetime.utcnow()
            result.duration_seconds = (end_time - start_time).total_seconds()

            # Determine overall status
            if result.invoices_failed == 0:
                status = "success"
                result.success = True
            elif result.invoices_transferred > 0:
                status = "partial_success"
                result.success = True
            else:
                status = "failed"
                result.success = False

            # Create transfer log for retry operation
            transfer_log = TransferLog(
                transfer_timestamp=start_time,
                status=status,
                invoices_transferred=result.invoices_transferred,
                invoices_failed=result.invoices_failed,
                duration_seconds=result.duration_seconds,
                triggered_by="manual_retry",
                triggered_by_user_id=triggered_by_user_id,
                error_details=None,
                failed_invoice_ids=json.dumps([str(id) for id in failed_invoice_ids]) if failed_invoice_ids else None
            )
            automation_db.add(transfer_log)
            automation_db.commit()

            result.transfer_log_id = transfer_log.id
            result.failed_invoice_ids = failed_invoice_ids

            logger.info(
                f"Retry job completed: {result.invoices_transferred} transferred, "
                f"{result.invoices_failed} failed, {result.duration_seconds:.2f}s"
            )

        except Exception as e:
            logger.error(f"Retry job failed: {e}")
            result.success = False
            result.error_message = str(e)

            # Try to log the failure
            try:
                end_time = datetime.utcnow()
                result.duration_seconds = (end_time - start_time).total_seconds()

                transfer_log = TransferLog(
                    transfer_timestamp=start_time,
                    status="failed",
                    invoices_transferred=result.invoices_transferred,
                    invoices_failed=result.invoices_failed,
                    duration_seconds=result.duration_seconds,
                    triggered_by="manual_retry",
                    triggered_by_user_id=triggered_by_user_id,
                    error_details=str(e)[:2000],
                    failed_invoice_ids=None
                )
                automation_db.add(transfer_log)
                automation_db.commit()
                result.transfer_log_id = transfer_log.id
            except Exception as log_error:
                logger.error(f"Failed to log retry failure: {log_error}")

        return result
