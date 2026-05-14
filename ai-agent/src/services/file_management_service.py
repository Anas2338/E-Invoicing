"""
File Management Service

Business logic for managing upload sessions and invoice blocking/deletion.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
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
        result = self.db.execute(
            select(ExcelUploadSession)
            .where(ExcelUploadSession.user_id == user_id)
            .order_by(ExcelUploadSession.upload_timestamp.desc())
        )
        sessions = result.scalars().all()

        result = []
        for session in sessions:
            # Count invoices by status for this session
            invoices_result = self.db.execute(
                select(AutomationInvoice)
                .where(AutomationInvoice.excel_upload_session_id == session.id)
            )
            invoices = invoices_result.scalars().all()

            pending_count = sum(1 for inv in invoices if inv.status == "pending")
            transferred_count = sum(1 for inv in invoices if inv.status == "transferred")
            transfer_failed_count = sum(1 for inv in invoices if inv.status == "transfer_failed")
            validated_count = sum(1 for inv in invoices if inv.status == "validated")
            failed_count = sum(1 for inv in invoices if inv.status == "failed")
            blocked_count = sum(1 for inv in invoices if inv.status == "blocked")
            expired_count = sum(1 for inv in invoices if inv.status == "expired")

            # Can delete session if no transferred invoices
            can_delete = transferred_count == 0

            # Can delete Excel file if it exists and all invoices are transferred
            can_delete_file = (
                session.file_path is not None and
                os.path.exists(session.file_path) and
                len(invoices) > 0 and
                transferred_count == len(invoices)
            )

            result.append({
                "id": str(session.id),
                "uploaded_at": session.upload_timestamp,
                "total_count": len(invoices),
                "pending_count": pending_count,
                "validated_count": validated_count,
                "transferred_count": transferred_count,
                "transfer_failed_count": transfer_failed_count,
                "failed_count": failed_count,
                "blocked_count": blocked_count,
                "expired_count": expired_count,
                "can_delete": can_delete,
                "can_delete_file": can_delete_file,
                "has_file": session.file_path is not None,
                "processing_status": session.processing_status,
                "processed_rows": session.processed_rows,
                "total_rows": session.total_rows,
                "error_message": session.error_message,
            })

        return result

    def delete_upload_session(self, session_id: str, user_id: str, delete_file_only: bool = False) -> Tuple[bool, int, str]:
        """
        Delete an upload session and all its invoices, or just delete the Excel file.

        Args:
            session_id: Upload session ID
            user_id: User ID for authorization
            delete_file_only: If True, only delete the Excel file, keep session and invoices

        Returns:
            Tuple of (success, deleted_count, message)

        Raises:
            HTTPException: If session not found
        """
        # Verify session exists and belongs to user
        result = self.db.execute(
            select(ExcelUploadSession)
            .where(
                and_(
                    ExcelUploadSession.id == UUID(session_id),
                    ExcelUploadSession.user_id == user_id
                )
            )
        )
        session = result.scalars().first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found"
            )

        # Delete Excel file from disk if it exists
        if session.file_path and os.path.exists(session.file_path):
            try:
                os.remove(session.file_path)
            except Exception as e:
                # Log but don't fail if file deletion fails
                print(f"Warning: Failed to delete Excel file {session.file_path}: {e}")

        # If only deleting file, update session and return
        if delete_file_only:
            session.file_path = None
            self.db.add(session)
            self.db.commit()

            log_entry = AutomationLog(
                user_id=user_id,
                action=AutomationLogAction.DELETE_SESSION,
                status=AutomationLogStatus.SUCCESS,
                details={
                    "session_id": session_id,
                    "action": "delete_excel_file_only",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            self.db.add(log_entry)
            self.db.commit()

            return True, 0, "Excel file deleted successfully"

        # Check for transferred invoices
        transferred_result = self.db.execute(
            select(func.count(AutomationInvoice.id))
            .where(
                and_(
                    AutomationInvoice.excel_upload_session_id == session.id,
                    AutomationInvoice.status == "transferred"
                )
            )
        )
        transferred_count = transferred_result.scalar()

        if transferred_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete upload session - {transferred_count} invoices already transferred to main database. You can only delete pending, validated, or failed invoices."
            )

        # Get all invoices for this session
        invoices_result = self.db.execute(
            select(AutomationInvoice)
            .where(AutomationInvoice.excel_upload_session_id == session.id)
        )
        invoices = invoices_result.scalars().all()

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

        return True, deleted_count, f"Successfully deleted {deleted_count} invoices and Excel file"

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
            HTTPException: If invoice not found or already transferred
        """
        invoice_result = self.db.execute(
            select(AutomationInvoice)
            .where(
                and_(
                    AutomationInvoice.id == UUID(invoice_id),
                    AutomationInvoice.user_id == user_id
                )
            )
        )
        invoice = invoice_result.scalars().first()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        if invoice.status == "transferred":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block transferred invoice"
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
        invoice_result = self.db.execute(
            select(AutomationInvoice)
            .where(
                and_(
                    AutomationInvoice.id == UUID(invoice_id),
                    AutomationInvoice.user_id == user_id
                )
            )
        )
        invoice = invoice_result.scalars().first()

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

    def pause_invoice(self, invoice_id: str, user_id: str) -> AutomationInvoice:
        """
        Pause a validated invoice to prevent AI agent from transferring it.

        Only allowed for invoices with status 'validated'.

        Args:
            invoice_id: Invoice ID
            user_id: User ID for authorization

        Returns:
            Updated invoice

        Raises:
            HTTPException: If invoice not found, not validated, or already transferred
        """
        invoice_result = self.db.execute(
            select(AutomationInvoice)
            .where(
                and_(
                    AutomationInvoice.id == UUID(invoice_id),
                    AutomationInvoice.user_id == user_id
                )
            )
        )
        invoice = invoice_result.scalars().first()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        if invoice.status != "validated":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause invoice with status '{invoice.status}'. Only validated invoices can be paused."
            )

        invoice.status = "paused"
        invoice.updated_at = datetime.utcnow()

        log_entry = AutomationLog(
            automation_invoice_id=invoice.id,
            action=AutomationLogAction.BLOCK,
            status=AutomationLogStatus.SUCCESS,
            details={
                "invoice_id": invoice_id,
                "action": "pause",
                "previous_status": "validated",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def resume_invoice(self, invoice_id: str, user_id: str) -> AutomationInvoice:
        """
        Resume a paused invoice so the AI agent can transfer it again.

        Only allowed for invoices with status 'paused'.

        Args:
            invoice_id: Invoice ID
            user_id: User ID for authorization

        Returns:
            Updated invoice

        Raises:
            HTTPException: If invoice not found or not paused
        """
        invoice_result = self.db.execute(
            select(AutomationInvoice)
            .where(
                and_(
                    AutomationInvoice.id == UUID(invoice_id),
                    AutomationInvoice.user_id == user_id
                )
            )
        )
        invoice = invoice_result.scalars().first()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        if invoice.status != "paused":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume invoice with status '{invoice.status}'. Only paused invoices can be resumed."
            )

        invoice.status = "validated"
        invoice.updated_at = datetime.utcnow()

        log_entry = AutomationLog(
            automation_invoice_id=invoice.id,
            action=AutomationLogAction.UNBLOCK,
            status=AutomationLogStatus.SUCCESS,
            details={
                "invoice_id": invoice_id,
                "action": "resume",
                "previous_status": "paused",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def delete_invoice(self, invoice_id: str, user_id: str) -> Tuple[bool, str]:
        """
        Delete a single invoice if not transferred.

        Args:
            invoice_id: Invoice ID
            user_id: User ID for authorization

        Returns:
            Tuple of (success, message)

        Raises:
            HTTPException: If invoice not found or already transferred
        """
        invoice_result = self.db.execute(
            select(AutomationInvoice)
            .where(
                and_(
                    AutomationInvoice.id == UUID(invoice_id),
                    AutomationInvoice.user_id == user_id
                )
            )
        )
        invoice = invoice_result.scalars().first()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
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
            HTTPException: If any invoice not found or already transferred
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

    def bulk_delete_invoices(self, invoice_ids: List[str], user_id: str) -> Dict[str, Any]:
        """
        Delete multiple invoices at once.

        Args:
            invoice_ids: List of invoice IDs
            user_id: User ID for authorization

        Returns:
            Dict with deleted_count, skipped_count, and skipped_ids
        """
        deleted_count = 0
        skipped_ids = []

        for invoice_id in invoice_ids:
            try:
                self.delete_invoice(invoice_id, user_id)
                deleted_count += 1
            except HTTPException as e:
                if e.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]:
                    skipped_ids.append(invoice_id)
                    continue
                raise

        return {
            "deleted_count": deleted_count,
            "skipped_count": len(skipped_ids),
            "skipped_ids": skipped_ids,
        }

    def bulk_retry_invoices(self, invoice_ids: List[str], user_id: str) -> int:
        """
        Retry multiple invoices at once.

        Args:
            invoice_ids: List of invoice IDs
            user_id: User ID for authorization

        Returns:
            Number of invoices queued for retry
        """
        retried_count = 0

        for invoice_id in invoice_ids:
            try:
                invoice_result = self.db.execute(
                    select(AutomationInvoice)
                    .where(
                        and_(
                            AutomationInvoice.id == UUID(invoice_id),
                            AutomationInvoice.user_id == user_id
                        )
                    )
                )
                invoice = invoice_result.scalars().first()

                if not invoice:
                    continue

                # Check if invoice is in a retryable state
                if invoice.status not in ["failed", "transfer_failed", "pending"]:
                    continue

                # Reset invoice to validated status for retry
                invoice.status = "validated"
                invoice.retry_count = (invoice.retry_count or 0) + 1
                invoice.last_retry_at = datetime.utcnow()
                invoice.validation_errors = None
                invoice.transfer_error = None

                # Log the action
                log_entry = AutomationLog(
                    automation_invoice_id=invoice.id,
                    action=AutomationLogAction.RETRY,
                    status=AutomationLogStatus.SUCCESS,
                    details={
                        "invoice_id": invoice_id,
                        "retry_count": invoice.retry_count,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                self.db.add(log_entry)
                self.db.add(invoice)

                retried_count += 1

            except Exception:
                # Skip invoices that can't be retried but continue with others
                continue

        self.db.commit()
        return retried_count
