"""
Core automation service for invoice processing.
"""
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, date, time
from uuid import UUID
from sqlmodel import Session, select, func, and_
import sqlalchemy as sa

from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.automation_log import AutomationLog, AutomationLogAction, AutomationLogStatus
from src.models.excel_upload_session import ExcelUploadSession, ExcelUploadProcessingStatus
from src.services.validation_service import ValidationService
from src.services.fbr_client import FBRClient
from src.schemas.fbr import FBREnvironment


class AutomationService:
    """Service for core automation logic."""

    def __init__(self, db: Session):
        """
        Initialize automation service.

        Args:
            db: Database session
        """
        self.db = db

    def create_upload_session(
        self,
        user_id: UUID,
        original_filename: str,
        total_rows: int,
        file_path: Optional[str] = None
    ) -> ExcelUploadSession:
        """
        Create new Excel upload session.

        Args:
            user_id: User UUID
            original_filename: Original filename
            total_rows: Total number of rows in Excel
            file_path: Path to uploaded file (optional, None for in-memory parsing)

        Returns:
            Created ExcelUploadSession
        """
        session = ExcelUploadSession(
            user_id=user_id,
            file_path=file_path,
            original_filename=original_filename,
            total_rows=total_rows,
            processing_status=ExcelUploadProcessingStatus.PROCESSING
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def store_invoices_from_excel(
        self,
        user_id: UUID,
        session_id: UUID,
        invoices: list[dict]
    ) -> List[AutomationInvoice]:
        """
        Store invoices from Excel file in database.

        Args:
            user_id: User UUID
            session_id: Excel upload session UUID
            invoices: List of invoice dictionaries with structure:
                {
                    "invoice_data": {...},  # FBR-compliant invoice fields
                    "scheduled_date": date,
                    "scheduled_time": time
                }

        Returns:
            List of created AutomationInvoice objects
        """
        created_invoices = []

        for invoice_entry in invoices:
            # Extract components from new structure
            invoice_data = invoice_entry['invoice_data']
            scheduled_date = invoice_entry['scheduled_date']
            scheduled_time = invoice_entry['scheduled_time']

            # Create a copy of invoice_data for JSON storage with serializable types
            invoice_data_json = invoice_data.copy()

            # Serialize date/time fields in invoice_data if present
            if 'invoice_date' in invoice_data_json and hasattr(invoice_data_json['invoice_date'], 'isoformat'):
                invoice_data_json['invoice_date'] = invoice_data_json['invoice_date'].isoformat()

            automation_invoice = AutomationInvoice(
                user_id=user_id,
                excel_upload_session_id=session_id,
                invoice_number=invoice_data['invoice_number'],
                invoice_data=invoice_data_json,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                status=AutomationInvoiceStatus.PENDING
            )
            self.db.add(automation_invoice)
            created_invoices.append(automation_invoice)

        self.db.commit()
        for invoice in created_invoices:
            self.db.refresh(invoice)

        return created_invoices

    def mark_past_invoices_as_expired(self, user_id: UUID, session_id: UUID) -> int:
        """
        Mark invoices with past scheduled times as expired.

        Args:
            user_id: User UUID
            session_id: Excel upload session UUID

        Returns:
            Number of invoices marked as expired
        """
        now = datetime.utcnow()
        current_date = now.date()
        current_time = now.time()

        # Find invoices with past scheduled times
        statement = select(AutomationInvoice).where(
            and_(
                AutomationInvoice.user_id == user_id,
                AutomationInvoice.excel_upload_session_id == session_id,
                AutomationInvoice.status == AutomationInvoiceStatus.PENDING,
                AutomationInvoice.scheduled_date < current_date
            )
        )
        past_invoices = self.db.exec(statement).all()

        # Also check invoices scheduled for today but in the past
        statement_today = select(AutomationInvoice).where(
            and_(
                AutomationInvoice.user_id == user_id,
                AutomationInvoice.excel_upload_session_id == session_id,
                AutomationInvoice.status == AutomationInvoiceStatus.PENDING,
                AutomationInvoice.scheduled_date == current_date,
                AutomationInvoice.scheduled_time < current_time
            )
        )
        past_invoices_today = self.db.exec(statement_today).all()

        all_past_invoices = past_invoices + past_invoices_today

        # Mark as expired
        for invoice in all_past_invoices:
            invoice.status = AutomationInvoiceStatus.EXPIRED
            invoice.validation_errors = "Scheduled time is in the past"
            self.db.add(invoice)

        self.db.commit()
        return len(all_past_invoices)

    def get_pending_invoices_for_hour(self, current_hour: int, current_date: date) -> List[AutomationInvoice]:
        """
        Get pending invoices scheduled for the current hour.

        Args:
            current_hour: Current hour (0-23)
            current_date: Current date

        Returns:
            List of pending AutomationInvoice objects
        """
        statement = select(AutomationInvoice).where(
            and_(
                AutomationInvoice.status == AutomationInvoiceStatus.PENDING,
                AutomationInvoice.scheduled_date == current_date,
                func.extract('hour', AutomationInvoice.scheduled_time) == current_hour
            )
        )
        return self.db.exec(statement).all()

    def update_invoice_status(
        self,
        invoice_id: UUID,
        status: AutomationInvoiceStatus,
        validation_errors: Optional[str] = None,
        fbr_response: Optional[dict] = None
    ) -> AutomationInvoice:
        """
        Update invoice status and related fields.

        Args:
            invoice_id: Invoice UUID
            status: New status
            validation_errors: Validation error message (optional)
            fbr_response: FBR API response (optional)

        Returns:
            Updated AutomationInvoice
        """
        invoice = self.db.get(AutomationInvoice, invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        invoice.status = status
        if validation_errors:
            invoice.validation_errors = validation_errors
        if fbr_response:
            invoice.fbr_response = fbr_response
        if status in [AutomationInvoiceStatus.SUBMITTED, AutomationInvoiceStatus.FAILED]:
            invoice.processed_at = datetime.utcnow()

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def log_automation_activity(
        self,
        invoice_id: UUID,
        action: AutomationLogAction,
        status: AutomationLogStatus,
        details: dict
    ) -> AutomationLog:
        """
        Log automation activity.

        Args:
            invoice_id: Invoice UUID
            action: Action type
            status: Action status
            details: Action details

        Returns:
            Created AutomationLog
        """
        log = AutomationLog(
            automation_invoice_id=invoice_id,
            action=action,
            status=status,
            details=details
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_dashboard_stats(self, user_id: UUID) -> dict:
        """
        Get dashboard statistics for user.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with statistics
        """
        # Count invoices by status
        statement = select(
            func.count(AutomationInvoice.id).label('total'),
            func.sum(func.cast(AutomationInvoice.status == AutomationInvoiceStatus.PENDING, sa.Integer)).label('pending'),
            func.sum(func.cast(AutomationInvoice.status == AutomationInvoiceStatus.EXPIRED, sa.Integer)).label('expired'),
            func.sum(func.cast(AutomationInvoice.status == AutomationInvoiceStatus.VALIDATED, sa.Integer)).label('validated'),
            func.sum(func.cast(AutomationInvoice.status == AutomationInvoiceStatus.SUBMITTED, sa.Integer)).label('submitted'),
            func.sum(func.cast(AutomationInvoice.status == AutomationInvoiceStatus.FAILED, sa.Integer)).label('failed'),
        ).where(AutomationInvoice.user_id == user_id)

        result = self.db.exec(statement).first()

        return {
            "total_invoices": result.total or 0,
            "pending_count": result.pending or 0,
            "expired_count": result.expired or 0,
            "validated_count": result.validated or 0,
            "submitted_count": result.submitted or 0,
            "failed_count": result.failed or 0,
        }

    def retry_failed_invoice(self, invoice_id: UUID, user_id: UUID) -> AutomationInvoice:
        """
        Reset failed invoice to pending for retry.

        Args:
            invoice_id: Invoice UUID
            user_id: User UUID (for authorization check)

        Returns:
            Updated AutomationInvoice

        Raises:
            ValueError: If invoice is not found, not owned by user, or not in failed status
        """
        invoice = self.db.get(AutomationInvoice, invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        # Verify user ownership (row-level security)
        if invoice.user_id != user_id:
            raise ValueError(f"Invoice {invoice_id} not found")  # Don't reveal existence

        if invoice.status != AutomationInvoiceStatus.FAILED:
            raise ValueError(f"Invoice must be in 'failed' status to retry. Current status: {invoice.status}")

        # Reset to pending
        invoice.status = AutomationInvoiceStatus.PENDING
        invoice.validation_errors = None
        invoice.fbr_response = None
        invoice.processed_at = None

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        # Log retry action
        self.log_automation_activity(
            invoice_id=invoice_id,
            action=AutomationLogAction.RETRY,
            status=AutomationLogStatus.SUCCESS,
            details={"message": "Invoice reset to pending for retry"}
        )

        return invoice

    async def validate_invoice(self, invoice: AutomationInvoice) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate invoice using ValidationService.

        Args:
            invoice: AutomationInvoice to validate

        Returns:
            Tuple of (is_valid, validation_errors)
        """
        validation_service = ValidationService()

        # Use invoice_data from the automation invoice
        invoice_data = invoice.invoice_data

        # Perform local validation
        is_valid, validation_errors = validation_service.validate_invoice_locally(invoice_data)

        return is_valid, validation_errors

    async def submit_invoice_to_fbr(
        self,
        invoice: AutomationInvoice,
        environment: FBREnvironment = FBREnvironment.SANDBOX
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Submit invoice to FBR using FBRClient.

        Args:
            invoice: AutomationInvoice to submit
            environment: FBR environment (SANDBOX or PRODUCTION)

        Returns:
            Tuple of (is_submitted, response_data, reference_number)
        """
        fbr_client = FBRClient()

        # Use invoice_data from the automation invoice
        invoice_data = invoice.invoice_data

        # Post invoice to FBR
        is_posted, response_data, reference_number = await fbr_client.post_invoice(
            invoice_data=invoice_data,
            environment=environment
        )

        return is_posted, response_data, reference_number
