"""
FTE Worker Service for processing scheduled invoices.
"""
import asyncio
from typing import List
from datetime import datetime
from sqlmodel import Session

from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.automation_log import AutomationLogAction, AutomationLogStatus
from src.models.excel_upload_session import ExcelUploadSession
from src.services.automation_service import AutomationService
from src.services.excel_service import ExcelService
from src.schemas.fbr import FBREnvironment
import logging

logger = logging.getLogger(__name__)


class FTEWorkerService:
    """Service for FTE worker that processes scheduled invoices hourly."""

    def __init__(self, db: Session):
        """
        Initialize FTE worker service.

        Args:
            db: Database session
        """
        self.db = db
        self.automation_service = AutomationService(db)
        self.excel_service = ExcelService(db)

    async def process_pending_invoices(self) -> dict:
        """
        Process all pending invoices scheduled for the current hour.

        Returns:
            Dictionary with processing statistics
        """
        now = datetime.utcnow()
        current_hour = now.hour
        current_date = now.date()

        logger.info(f"FTE Worker: Processing invoices for {current_date} at hour {current_hour}")

        # Get pending invoices for current hour
        pending_invoices = self.automation_service.get_pending_invoices_for_hour(
            current_hour=current_hour,
            current_date=current_date
        )

        stats = {
            "total_processed": len(pending_invoices),
            "validated": 0,
            "submitted": 0,
            "failed": 0,
            "errors": []
        }

        if not pending_invoices:
            logger.info("FTE Worker: No pending invoices found for current hour")
            return stats

        logger.info(f"FTE Worker: Found {len(pending_invoices)} pending invoices")

        # Process each invoice
        for invoice in pending_invoices:
            try:
                await self._process_single_invoice(invoice, stats)
            except Exception as e:
                logger.error(f"FTE Worker: Error processing invoice {invoice.id}: {str(e)}")
                stats["errors"].append({
                    "invoice_id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "error": str(e)
                })

                # Mark as failed
                self.automation_service.update_invoice_status(
                    invoice_id=invoice.id,
                    status=AutomationInvoiceStatus.FAILED,
                    validation_errors=f"Processing error: {str(e)}"
                )

                # Log failure
                self.automation_service.log_automation_activity(
                    invoice_id=invoice.id,
                    action=AutomationLogAction.SUBMIT,
                    status=AutomationLogStatus.FAILURE,
                    details={"error": str(e)}
                )

                stats["failed"] += 1

        logger.info(f"FTE Worker: Processing complete. Stats: {stats}")
        return stats

    async def _process_single_invoice(self, invoice: AutomationInvoice, stats: dict) -> None:
        """
        Process a single invoice: validate and submit to FBR.

        Args:
            invoice: AutomationInvoice to process
            stats: Statistics dictionary to update
        """
        logger.info(f"FTE Worker: Processing invoice {invoice.invoice_number}")

        # Step 1: Validate invoice
        is_valid, validation_errors = await self.automation_service.validate_invoice(invoice)

        if not is_valid:
            logger.warning(f"FTE Worker: Invoice {invoice.invoice_number} validation failed")

            # Update status to failed
            error_message = "; ".join([f"{k}: {v}" for k, v in validation_errors.items()])
            self.automation_service.update_invoice_status(
                invoice_id=invoice.id,
                status=AutomationInvoiceStatus.FAILED,
                validation_errors=error_message
            )

            # Log validation failure
            self.automation_service.log_automation_activity(
                invoice_id=invoice.id,
                action=AutomationLogAction.VALIDATE,
                status=AutomationLogStatus.FAILURE,
                details={"validation_errors": validation_errors}
            )

            stats["failed"] += 1
            return

        # Log successful validation
        self.automation_service.log_automation_activity(
            invoice_id=invoice.id,
            action=AutomationLogAction.VALIDATE,
            status=AutomationLogStatus.SUCCESS,
            details={"message": "Invoice validated successfully"}
        )

        # Update status to validated
        self.automation_service.update_invoice_status(
            invoice_id=invoice.id,
            status=AutomationInvoiceStatus.VALIDATED
        )

        stats["validated"] += 1

        # Step 2: Submit to FBR
        # TODO: Get environment from user settings or invoice data
        environment = FBREnvironment.SANDBOX

        is_submitted, response_data, reference_number = await self.automation_service.submit_invoice_to_fbr(
            invoice=invoice,
            environment=environment
        )

        if is_submitted:
            logger.info(f"FTE Worker: Invoice {invoice.invoice_number} submitted successfully")

            # Update status to submitted
            self.automation_service.update_invoice_status(
                invoice_id=invoice.id,
                status=AutomationInvoiceStatus.SUBMITTED,
                fbr_response=response_data
            )

            # Log successful submission
            self.automation_service.log_automation_activity(
                invoice_id=invoice.id,
                action=AutomationLogAction.SUBMIT,
                status=AutomationLogStatus.SUCCESS,
                details={
                    "reference_number": reference_number,
                    "response": response_data
                }
            )

            stats["submitted"] += 1
        else:
            logger.warning(f"FTE Worker: Invoice {invoice.invoice_number} submission failed")

            # Update status to failed
            error_message = response_data.get("error", "FBR submission failed")
            self.automation_service.update_invoice_status(
                invoice_id=invoice.id,
                status=AutomationInvoiceStatus.FAILED,
                validation_errors=error_message,
                fbr_response=response_data
            )

            # Log submission failure
            self.automation_service.log_automation_activity(
                invoice_id=invoice.id,
                action=AutomationLogAction.SUBMIT,
                status=AutomationLogStatus.FAILURE,
                details={"error": error_message, "response": response_data}
            )

            stats["failed"] += 1
