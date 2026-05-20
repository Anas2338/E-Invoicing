"""
Background validation service for processing invoices asynchronously.
"""
import logging
from datetime import datetime
from uuid import UUID
from sqlmodel import Session, select
from typing import Optional

from src.database.session import get_automation_db_session
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.excel_upload_session import ExcelUploadSession, ExcelUploadProcessingStatus
from src.services.validation_service import ValidationService
from src.services.fbr_client import FBRClient
from src.config.settings import settings

logger = logging.getLogger(__name__)


class BackgroundValidationService:
    """Service for background FBR validation of invoices."""

    @staticmethod
    async def validate_invoices_background(
        session_id: UUID,
        user_id: UUID,
        fbr_token: str
    ):
        """
        Validate all invoices for a session in the background.
        Updates progress in real-time.
        Creates its own database session.

        Args:
            session_id: Upload session UUID
            user_id: User UUID
            fbr_token: User's FBR production token
        """
        logger.info(f"Starting background validation for session {session_id}")

        # Create new database session for background task
        with get_automation_db_session() as db:
            try:
                # Get upload session
                upload_session = db.get(ExcelUploadSession, session_id)
                if not upload_session:
                    logger.error(f"Upload session {session_id} not found")
                    return

                # Update status to processing
                upload_session.processing_status = ExcelUploadProcessingStatus.PROCESSING
                db.add(upload_session)
                db.commit()

                # Get all invoices for this session
                statement = select(AutomationInvoice).where(
                    AutomationInvoice.excel_upload_session_id == session_id,
                    AutomationInvoice.user_id == user_id
                )
                invoices = db.exec(statement).all()

                if not invoices:
                    logger.warning(f"No invoices found for session {session_id}")
                    upload_session.processing_status = ExcelUploadProcessingStatus.COMPLETED
                    db.add(upload_session)
                    db.commit()
                    return

                # Initialize services
                validation_service = ValidationService()
                fbr_client = FBRClient()

                # Get current time for expiration check
                now = datetime.utcnow()
                current_date = now.date()
                current_time = now.time()

                validated_count = 0
                failed_count = 0
                expired_count = 0
                processed_count = 0

                try:
                    # Process invoices in batches for better performance
                    batch_size = 10  # Process 10 invoices in parallel
                    total_invoices = len(invoices)

                    for i in range(0, total_invoices, batch_size):
                        batch = invoices[i:i + batch_size]

                        # Process batch
                        for invoice in batch:
                            try:
                                # Check if invoice is already expired
                                is_expired = False
                                if invoice.scheduled_date < current_date:
                                    is_expired = True
                                elif invoice.scheduled_date == current_date and invoice.scheduled_time < current_time:
                                    is_expired = True

                                if is_expired:
                                    # Mark as expired, skip validation
                                    invoice.status = AutomationInvoiceStatus.EXPIRED
                                    invoice.validation_errors = "Scheduled time is in the past"
                                    expired_count += 1
                                else:
                                    # Step 1: Local validation
                                    is_valid_locally, validation_errors = validation_service.validate_invoice_locally(
                                        invoice.invoice_data
                                    )

                                    if not is_valid_locally:
                                        # Mark as PENDING with validation errors
                                        invoice.status = AutomationInvoiceStatus.PENDING
                                        invoice.validation_errors = f"Validation failed: {str(validation_errors)}"
                                        failed_count += 1
                                    else:
                                        # Step 2: FBR validation (Production)
                                        try:
                                            # DRY RUN MODE - Simulate FBR validation
                                            if settings.dry_run:
                                                import random
                                                import time

                                                logger.info(f"[DRY RUN] Simulating FBR validation for invoice {invoice.invoice_number}")

                                                is_valid_fbr = random.random() < 0.98

                                                if is_valid_fbr:
                                                    fbr_response = {
                                                        "dated": time.strftime("%Y-%m-%d %H:%M:%S"),
                                                        "validationResponse": {
                                                            "statusCode": "00",
                                                            "status": "Valid",
                                                            "error": "",
                                                            "invoiceStatuses": [{
                                                                "itemSNo": "1",
                                                                "statusCode": "00",
                                                                "status": "Valid",
                                                                "invoiceNo": "",
                                                                "errorCode": "",
                                                                "error": ""
                                                            }]
                                                        }
                                                    }
                                                    logger.info(f"[DRY RUN] Simulated validation SUCCESS for invoice {invoice.invoice_number}")
                                                else:
                                                    error_scenarios = [
                                                        {"code": "0052", "msg": "HS Code does not match with provided sale type"},
                                                        {"code": "0078", "msg": "Valid Item Sr. No. is mandatory where SRO/Schedule No. is provided"}
                                                    ]
                                                    error = random.choice(error_scenarios)
                                                    fbr_response = {
                                                        "dated": time.strftime("%Y-%m-%d %H:%M:%S"),
                                                        "validationResponse": {
                                                            "statusCode": "01",
                                                            "status": "Invalid",
                                                            "error": f"[{error['code']}] {error['msg']}",
                                                            "invoiceStatuses": []
                                                        }
                                                    }
                                                    logger.warning(f"[DRY RUN] Simulated validation FAILURE for invoice {invoice.invoice_number}")
                                            else:
                                                # REAL MODE - Actual FBR API call (Production)
                                                is_valid_fbr, fbr_response, reference_number = await fbr_client.validate_invoice_with_user_credentials(
                                                    invoice_data=invoice.invoice_data,
                                                    fbr_token=fbr_token
                                                )

                                            if is_valid_fbr:
                                                # Mark as validated and ready for posting
                                                invoice.status = AutomationInvoiceStatus.VALIDATED
                                                invoice.fbr_response = fbr_response
                                                validated_count += 1
                                            else:
                                                # Mark as PENDING with FBR validation errors
                                                invoice.status = AutomationInvoiceStatus.PENDING
                                                invoice.validation_errors = f"FBR validation failed: {str(fbr_response)}"
                                                invoice.fbr_response = fbr_response
                                                failed_count += 1

                                        except Exception as e:
                                            # FBR API call failed - mark as PENDING
                                            invoice.status = AutomationInvoiceStatus.PENDING
                                            invoice.validation_errors = f"FBR validation error: {str(e)}"
                                            failed_count += 1

                                db.add(invoice)
                                processed_count += 1

                            except Exception as e:
                                logger.error(f"Error processing invoice {invoice.invoice_number}: {str(e)}")
                                invoice.status = AutomationInvoiceStatus.PENDING
                                invoice.validation_errors = f"Processing error: {str(e)}"
                                failed_count += 1
                                db.add(invoice)
                                processed_count += 1

                        # Commit batch and update progress
                        db.commit()
                        upload_session.processed_rows = processed_count
                        db.add(upload_session)
                        db.commit()

                        logger.info(f"Processed batch {i // batch_size + 1}: {processed_count}/{total_invoices} invoices")

                finally:
                    # Always close the FBR client
                    await fbr_client.client.aclose()

                # Update session status to completed
                upload_session.processing_status = ExcelUploadProcessingStatus.COMPLETED
                upload_session.processed_rows = processed_count
                db.add(upload_session)
                db.commit()

                logger.info(
                    f"Background validation completed for session {session_id}: "
                    f"{validated_count} validated, {failed_count} failed, {expired_count} expired"
                )

            except Exception as e:
                logger.error(f"Background validation failed for session {session_id}: {str(e)}")
                try:
                    upload_session = db.get(ExcelUploadSession, session_id)
                    if upload_session:
                        upload_session.processing_status = ExcelUploadProcessingStatus.FAILED
                        upload_session.error_message = f"Background validation error: {str(e)}"
                        db.add(upload_session)
                        db.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to update session status: {str(commit_error)}")
