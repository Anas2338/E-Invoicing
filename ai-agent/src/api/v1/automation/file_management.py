"""
File Management API Endpoints

REST API endpoints for managing upload sessions and invoice blocking/deletion.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session

from src.database.session import get_automation_db, get_db
from src.services.file_management_service import FileManagementService
from src.schemas.file_management import (
    UploadSessionListResponse,
    UploadSessionResponse,
    BlockInvoiceRequest,
    BulkBlockRequest,
    BulkDeleteRequest,
    BulkRetryRequest,
    DeleteInvoiceResponse,
    DeleteUploadSessionResponse,
)
from src.api.middleware.auth_middleware import require_authentication
from src.middleware.rbac import require_automation_access


router = APIRouter(tags=["automation-file-management"])


@router.get("/upload-sessions", response_model=UploadSessionListResponse)
async def get_upload_sessions(
    request: Request,
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
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
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
):
    """
    Delete an upload session and all its invoices.

    Only allowed if no invoices have been transferred to main database.

    Args:
        session_id: Upload session ID to delete

    Returns:
        Success message with count of deleted invoices

    Raises:
        HTTPException 404: Session not found
        HTTPException 400: Session has transferred invoices
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


@router.delete("/upload-session/{session_id}/file", response_model=DeleteUploadSessionResponse)
async def delete_excel_file(
    session_id: str,
    request: Request,
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
):
    """
    Delete only the Excel file for an upload session.

    Allowed for sessions where all invoices have been transferred.
    The session and invoice records remain for audit purposes.

    Args:
        session_id: Upload session ID

    Returns:
        Success message

    Raises:
        HTTPException 404: Session not found
    """
    service = FileManagementService(db)
    success, deleted_count, message = service.delete_upload_session(
        session_id, user_id, delete_file_only=True
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
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
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
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
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
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
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


@router.post("/invoice/{invoice_id}/pause", status_code=status.HTTP_200_OK)
async def pause_invoice(
    invoice_id: str,
    request: Request,
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
):
    """
    Pause a validated invoice to prevent AI agent from transferring it.

    Only allowed for invoices with status 'validated'.
    The invoice will remain paused until manually resumed.

    Args:
        invoice_id: Invoice ID to pause

    Returns:
        Updated invoice status

    Raises:
        HTTPException 404: Invoice not found
        HTTPException 400: Invoice not in validated status
    """
    service = FileManagementService(db)
    invoice = service.pause_invoice(invoice_id, user_id)

    return {
        "success": True,
        "message": "Invoice paused successfully. It will not be transferred to the main database until resumed.",
        "invoice_id": str(invoice.id),
        "status": invoice.status,
    }


@router.post("/invoice/{invoice_id}/resume", status_code=status.HTTP_200_OK)
async def resume_invoice(
    invoice_id: str,
    request: Request,
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
):
    """
    Resume a paused invoice so the AI agent can transfer it.

    Only allowed for invoices with status 'paused'.
    The invoice will be picked up by the AI agent in the next transfer cycle.

    Args:
        invoice_id: Invoice ID to resume

    Returns:
        Updated invoice status

    Raises:
        HTTPException 404: Invoice not found
        HTTPException 400: Invoice not in paused status
    """
    service = FileManagementService(db)
    invoice = service.resume_invoice(invoice_id, user_id)

    return {
        "success": True,
        "message": "Invoice resumed successfully. It will be transferred in the next AI agent cycle.",
        "invoice_id": str(invoice.id),
        "status": invoice.status,
    }


@router.post("/invoices/bulk-pause", status_code=status.HTTP_200_OK)
async def bulk_pause_invoices(
    body: BulkBlockRequest,
    request: Request,
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
):
    """
    Pause multiple validated invoices at once.

    Args:
        body: List of invoice IDs to pause

    Returns:
        Count of successfully paused invoices
    """
    service = FileManagementService(db)
    paused_count = 0
    for invoice_id in body.invoice_ids:
        try:
            service.pause_invoice(invoice_id, user_id)
            paused_count += 1
        except HTTPException:
            continue

    return {
        "success": True,
        "message": f"Successfully paused {paused_count} invoices",
        "paused_count": paused_count,
        "total_requested": len(body.invoice_ids),
    }


@router.post("/invoices/bulk-resume", status_code=status.HTTP_200_OK)
async def bulk_resume_invoices(
    body: BulkBlockRequest,
    request: Request,
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
):
    """
    Resume multiple paused invoices at once.

    Args:
        body: List of invoice IDs to resume

    Returns:
        Count of successfully resumed invoices
    """
    service = FileManagementService(db)
    resumed_count = 0
    for invoice_id in body.invoice_ids:
        try:
            service.resume_invoice(invoice_id, user_id)
            resumed_count += 1
        except HTTPException:
            continue

    return {
        "success": True,
        "message": f"Successfully resumed {resumed_count} invoices",
        "resumed_count": resumed_count,
        "total_requested": len(body.invoice_ids),
    }


@router.post("/invoices/bulk-block", status_code=status.HTTP_200_OK)
async def bulk_block_invoices(
    body: BulkBlockRequest,
    request: Request,
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
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


@router.post("/invoices/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_invoices(
    body: BulkDeleteRequest,
    request: Request,
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
):
    """
    Delete multiple invoices at once.

    Only allowed for invoices with status: pending, failed, expired, or blocked.

    Args:
        body: List of invoice IDs to delete

    Returns:
        Count of successfully deleted invoices
    """
    service = FileManagementService(db)
    result = service.bulk_delete_invoices(body.invoice_ids, user_id)

    return {
        "success": result["deleted_count"] > 0 or result["skipped_count"] == 0,
        "message": f"Successfully deleted {result['deleted_count']} invoices",
        "deleted_count": result["deleted_count"],
        "skipped_count": result["skipped_count"],
        "total_requested": len(body.invoice_ids),
    }


@router.post("/invoices/bulk-retry", status_code=status.HTTP_200_OK)
async def bulk_retry_invoices(
    body: BulkRetryRequest,
    request: Request,
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
    main_db: Session = Depends(get_db),
):
    """
    Retry multiple invoices with actual FBR re-validation.

    Only allowed for invoices with status: pending, failed, or transfer_failed.
    Each invoice is validated against FBR and its status updated based on
    the FBR response (validated on success, pending with errors on failure).

    Args:
        body: List of invoice IDs to retry

    Returns:
        Count of validated/failed invoices
    """
    from src.models.user import User
    from src.services.file_management_service import FileManagementService
    from src.services.fbr_client import FBRClient

    # Fetch user's FBR token from main database (same as single-invoice retry)
    user = main_db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # FBR production token — the automation pipeline validates against
    # FBR production endpoints only (same as the single-invoice retry and upload flow)
    fbr_token = user.fbr_production_token
    if not fbr_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "FBR credentials not configured. "
                "Please configure your FBR production credentials in settings."
            ),
        )

    service = FileManagementService(db)
    fbr_client = FBRClient()
    try:
        result = await service.bulk_retry_invoices(
            body.invoice_ids, user_id, fbr_token, fbr_client
        )
    finally:
        await fbr_client.client.aclose()

    return {
        "success": True,
        "message": result["message"],
        "retried_count": result["retried_count"],
        "total_requested": len(body.invoice_ids),
        "validated_count": result["validated_count"],
        "failed_count": result["failed_count"],
        "skipped_count": result["skipped_count"],
    }
