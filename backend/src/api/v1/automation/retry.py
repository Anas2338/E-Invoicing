"""
Retry endpoints for automation operations.

Provides endpoints for retrying failed automation tasks.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from uuid import UUID
import logging

from src.database.session import get_automation_db
from src.api.middleware.auth_middleware import require_authentication
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/invoice/{invoice_id}/retry")
async def retry_failed_invoice(
    invoice_id: UUID,
    automation_db: Session = Depends(get_automation_db),
    user_id: str = Depends(require_authentication)
):
    """
    Retry a failed or transfer_failed automation invoice.

    This endpoint allows users to retry invoices that failed during automation processing.
    The invoice status will be reset to VALIDATED so the AI agent can pick it up in the next processing cycle.
    """
    # Get the invoice
    statement = select(AutomationInvoice).where(
        AutomationInvoice.id == invoice_id,
        AutomationInvoice.user_id == UUID(user_id)
    )
    invoice = automation_db.exec(statement).first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if invoice is in a retryable state
    if invoice.status not in [AutomationInvoiceStatus.FAILED, AutomationInvoiceStatus.TRANSFER_FAILED, AutomationInvoiceStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice cannot be retried. Current status: {invoice.status}"
        )

    # Reset invoice to validated status for retry
    from datetime import datetime
    invoice.status = AutomationInvoiceStatus.VALIDATED
    invoice.retry_count = (invoice.retry_count or 0) + 1
    invoice.last_retry_at = datetime.utcnow()
    invoice.validation_errors = None
    invoice.transfer_error = None

    automation_db.add(invoice)
    automation_db.commit()
    automation_db.refresh(invoice)

    logger.info(f"Invoice {invoice_id} reset for retry by user {user_id}. Retry count: {invoice.retry_count}")

    return {
        "success": True,
        "message": f"Invoice queued for retry. AI agent will process it in the next cycle (every 5 minutes).",
        "invoice_id": str(invoice.id),
        "retry_count": invoice.retry_count,
        "status": invoice.status
    }
