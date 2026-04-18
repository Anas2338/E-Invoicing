"""
File Management API Endpoints

REST API endpoints for managing upload sessions and invoice blocking/deletion.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session

from src.database.session import get_db
from src.services.file_management_service import FileManagementService
from src.schemas.file_management import (
    UploadSessionListResponse,
    UploadSessionResponse,
    BlockInvoiceRequest,
    BulkBlockRequest,
    DeleteInvoiceResponse,
    DeleteUploadSessionResponse,
)
from src.api.middleware.auth_middleware import require_authentication


router = APIRouter(tags=["automation-file-management"])


@router.get("/upload-sessions", response_model=UploadSessionListResponse)
async def get_upload_sessions(
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Get all upload sessions for the current user with invoice counts.

    Returns:
        List of upload sessions with status breakdown
    """
    service = FileManagementService(db)
    sessions = service.get_upload_sessions(user_id)

    return UploadSessionListResponse(
        sessions=[UploadSessionResponse(**session) for session in sessions],
        total=len(sessions),
    )


@router.delete("/upload-session/{session_id}", response_model=DeleteUploadSessionResponse)
async def delete_upload_session(
    session_id: str,
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Delete an upload session and all its invoices.

    Only allowed if no invoices have been submitted to FBR.

    Args:
        session_id: Upload session ID to delete

    Returns:
        Success message with count of deleted invoices

    Raises:
        HTTPException 404: Session not found
        HTTPException 400: Session has submitted invoices
    """
    service = FileManagementService(db)
    success, deleted_count, message = service.delete_upload_session(
        session_id, user_id
    )

    return DeleteUploadSessionResponse(
        success=success,
        deleted_count=deleted_count,
        message=message,
    )


@router.post("/invoice/{invoice_id}/block", status_code=status.HTTP_200_OK)
async def block_invoice(
    invoice_id: str,
    request: Request,
    body: BlockInvoiceRequest = BlockInvoiceRequest(),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Block an invoice from FBR submission.

    Changes invoice status to "blocked" so AI Agent will skip it.

    Args:
        invoice_id: Invoice ID to block
        body: Optional reason for blocking

    Returns:
        Updated invoice

    Raises:
        HTTPException 404: Invoice not found
        HTTPException 400: Invoice already submitted
    """
    service = FileManagementService(db)
    invoice = service.block_invoice(
        invoice_id, user_id, body.reason
    )

    return {
        "success": True,
        "message": "Invoice blocked successfully",
        "invoice_id": str(invoice.id),
        "status": invoice.status,
    }


@router.post("/invoice/{invoice_id}/unblock", status_code=status.HTTP_200_OK)
async def unblock_invoice(
    invoice_id: str,
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Unblock an invoice to allow FBR submission.

    Changes invoice status from "blocked" back to "pending".

    Args:
        invoice_id: Invoice ID to unblock

    Returns:
        Updated invoice

    Raises:
        HTTPException 404: Invoice not found
        HTTPException 400: Invoice not blocked
    """
    service = FileManagementService(db)
    invoice = service.unblock_invoice(invoice_id, user_id)

    return {
        "success": True,
        "message": "Invoice unblocked successfully",
        "invoice_id": str(invoice.id),
        "status": invoice.status,
    }


@router.delete("/invoice/{invoice_id}", response_model=DeleteInvoiceResponse)
async def delete_invoice(
    invoice_id: str,
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Delete a single invoice.

    Only allowed for invoices with status: pending, failed, expired, or blocked.
    Submitted invoices cannot be deleted for audit purposes.

    Args:
        invoice_id: Invoice ID to delete

    Returns:
        Success message

    Raises:
        HTTPException 404: Invoice not found
        HTTPException 400: Invoice already submitted
    """
    service = FileManagementService(db)
    success, message = service.delete_invoice(invoice_id, user_id)

    return DeleteInvoiceResponse(success=success, message=message)


@router.post("/invoices/bulk-block", status_code=status.HTTP_200_OK)
async def bulk_block_invoices(
    body: BulkBlockRequest,
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Block multiple invoices at once.

    Args:
        body: List of invoice IDs to block with optional reason

    Returns:
        Count of successfully blocked invoices
    """
    service = FileManagementService(db)
    blocked_count = service.bulk_block_invoices(
        body.invoice_ids, user_id, body.reason
    )

    return {
        "success": True,
        "message": f"Successfully blocked {blocked_count} invoices",
        "blocked_count": blocked_count,
        "total_requested": len(body.invoice_ids),
    }
