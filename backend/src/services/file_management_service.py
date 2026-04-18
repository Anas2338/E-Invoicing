"""
File Management Service

Business logic for managing upload sessions and invoice blocking/deletion.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
from sqlmodel import Session, select, func, and_
from fastapi import HTTPException, status

from ..models.automation_invoice import AutomationInvoice
from ..models.excel_upload_session import ExcelUploadSession
from ..models.automation_log import AutomationLog, AutomationLogAction, AutomationLogStatus


class FileManagementService:
    """Service for managing upload sessions and invoice operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_upload_sessions(self, user_id: str) -> List[dict]:
        """
        Get all upload sessions for a user with invoice counts.

        Args:
            user_id: User ID to filter sessions

        Returns:
            List of upload session dictionaries with counts
        """
        # Query all sessions for the user
        sessions = self.db.exec(
            select(ExcelUploadSession)
            .where(ExcelUploadSession.user_id == user_id)
            .order_by(ExcelUploadSession.upload_timestamp.desc())
        ).all()

        result = []
        for session in sessions:
            # Count invoices by status for this session
            invoices = self.db.exec(
                select(AutomationInvoice)
                .where(AutomationInvoice.excel_upload_session_id == session.id)
            ).all()

            pending_count = sum(1 for inv in invoices if inv.status == "pending")
            submitted_count = sum(1 for inv in invoices if inv.status == "submitted")
            failed_count = sum(1 for inv in invoices if inv.status == "failed")
            blocked_count = sum(1 for inv in invoices if inv.status == "blocked")
            expired_count = sum(1 for inv in invoices if inv.status == "expired")

            # Can delete if no submitted invoices
            can_delete = submitted_count == 0

            result.append({
                "id": str(session.id),
                "uploaded_at": session.upload_timestamp,
                "total_count": len(invoices),
                "pending_count": pending_count,
                "submitted_count": submitted_count,
                "failed_count": failed_count,
                "blocked_count": blocked_count,
                "expired_count": expired_count,
                "can_delete": can_delete,
            })

        return result

    def delete_upload_session(self, session_id: str, user_id: str) -> Tuple[bool, int, str]:
        """
        Delete an upload session and all its invoices if no invoices are submitted.

        Args:
            session_id: Upload session ID
            user_id: User ID for authorization

        Returns:
            Tuple of (success, deleted_count, message)

        Raises:
            HTTPException: If session not found or has submitted invoices
        """
        # Verify session exists and belongs to user
        session = self.db.exec(
            select(ExcelUploadSession)
            .where(
                and_(
                    ExcelUploadSession.id == UUID(session_id),
                    ExcelUploadSession.user_id == user_id
                )
            )
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found"
            )

        # Check for submitted invoices
        submitted_count = self.db.exec(
            select(func.count(AutomationInvoice.id))
            .where(
                and_(
                    AutomationInvoice.excel_upload_session_id == session.id,
                    AutomationInvoice.status == "submitted"
                )
            )
        ).one()

        if submitted_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete upload session - {submitted_count} invoices already submitted to FBR. You can only delete pending or failed invoices."
            )

        # Get all invoices for this session
        invoices = self.db.exec(
            select(AutomationInvoice)
            .where(AutomationInvoice.excel_upload_session_id == session.id)
        ).all()

        deleted_count = len(invoices)

        # Delete all invoices
        for invoice in invoices:
            self.db.delete(invoice)

        # Delete the session
        self.db.delete(session)

        # Log the action
        log_entry = AutomationLog(
            user_id=user_id,
            action=AutomationLogAction.DELETE_SESSION,
            status=AutomationLogStatus.SUCCESS,
            details={
                "session_id": session_id,
                "deleted_invoice_count": deleted_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        self.db.add(log_entry)

        self.db.commit()

        return True, deleted_count, f"Successfully deleted {deleted_count} invoices"

    def block_invoice(self, invoice_id: str, user_id: str, reason: Optional[str] = None) -> AutomationInvoice:
        """
        Block an invoice from FBR submission.

        Args:
            invoice_id: Invoice ID
            user_id: User ID for authorization
            reason: Optional reason for blocking

        Returns:
            Updated invoice

        Raises:
            HTTPException: If invoice not found or already submitted
        """
        invoice = self.db.exec(
            select(AutomationInvoice)
            .where(
                and_(
                    AutomationInvoice.id == UUID(invoice_id),
                    AutomationInvoice.user_id == user_id
                )
            )
        ).first()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        if invoice.status == "submitted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block submitted invoice"
            )

        # Update status to blocked
        invoice.status = "blocked"
        invoice.reason = reason or "Blocked by user"
        invoice.updated_at = datetime.utcnow()

        # Log the action
        log_entry = AutomationLog(
            automation_invoice_id=invoice.id,
            action=AutomationLogAction.BLOCK,
            status=AutomationLogStatus.SUCCESS,
            details={
                "invoice_id": invoice_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        self.db.add(log_entry)

        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def unblock_invoice(self, invoice_id: str, user_id: str) -> AutomationInvoice:
        """
        Unblock an invoice to allow FBR submission.

        Args:
            invoice_id: Invoice ID
            user_id: User ID for authorization

        Returns:
            Updated invoice

        Raises:
            HTTPException: If invoice not found or not blocked
        """
        invoice = self.db.exec(
            select(AutomationInvoice)
            .where(
                and_(
                    AutomationInvoice.id == UUID(invoice_id),
                    AutomationInvoice.user_id == user_id
                )
            )
        ).first()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        if invoice.status != "blocked":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice is not blocked"
            )

        # Update status back to pending
        invoice.status = "pending"
        invoice.reason = None
        invoice.updated_at = datetime.utcnow()

        # Log the action
        log_entry = AutomationLog(
            automation_invoice_id=invoice.id,
            action=AutomationLogAction.UNBLOCK,
            status=AutomationLogStatus.SUCCESS,
            details={
                "invoice_id": invoice_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        self.db.add(log_entry)

        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def delete_invoice(self, invoice_id: str, user_id: str) -> Tuple[bool, str]:
        """
        Delete a single invoice if not submitted.

        Args:
            invoice_id: Invoice ID
            user_id: User ID for authorization

        Returns:
            Tuple of (success, message)

        Raises:
            HTTPException: If invoice not found or already submitted
        """
        invoice = self.db.exec(
            select(AutomationInvoice)
            .where(
                and_(
                    AutomationInvoice.id == UUID(invoice_id),
                    AutomationInvoice.user_id == user_id
                )
            )
        ).first()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        if invoice.status in ["submitted", "validated"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete submitted invoice. Submitted invoices are permanent for audit purposes."
            )

        # Log the action before deletion
        log_entry = AutomationLog(
            automation_invoice_id=invoice.id,
            action=AutomationLogAction.DELETE,
            status=AutomationLogStatus.SUCCESS,
            details={
                "invoice_id": invoice_id,
                "invoice_number": invoice.invoice_number,
                "status": invoice.status,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        self.db.add(log_entry)

        # Delete the invoice
        self.db.delete(invoice)
        self.db.commit()

        return True, "Invoice deleted successfully"

    def bulk_block_invoices(self, invoice_ids: List[str], user_id: str, reason: Optional[str] = None) -> int:
        """
        Block multiple invoices at once.

        Args:
            invoice_ids: List of invoice IDs
            user_id: User ID for authorization
            reason: Optional reason for blocking

        Returns:
            Number of invoices blocked

        Raises:
            HTTPException: If any invoice not found or already submitted
        """
        blocked_count = 0

        for invoice_id in invoice_ids:
            try:
                self.block_invoice(invoice_id, user_id, reason)
                blocked_count += 1
            except HTTPException as e:
                # Skip invoices that can't be blocked but continue with others
                if e.status_code == status.HTTP_400_BAD_REQUEST:
                    continue
                raise

        return blocked_count
