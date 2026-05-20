"""
Retry endpoints for automation operations.

Provides endpoints for retrying failed automation tasks with actual FBR re-validation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from uuid import UUID
from datetime import datetime
import logging

from src.database.session import get_automation_db, get_db
from src.api.middleware.auth_middleware import require_authentication
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.user import User
from src.services.fbr_client import FBRClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/invoice/{invoice_id}/retry")
async def retry_failed_invoice(
    invoice_id: UUID,
    automation_db: Session = Depends(get_automation_db),
    main_db: Session = Depends(get_db),
    user_id: str = Depends(require_authentication)
):
    """
    Retry a failed or pending automation invoice with actual FBR re-validation.

    Fetches the user's FBR token, validates the invoice data against FBR sandbox/production,
    and updates the invoice status based on the FBR response.
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

    # Fetch user from main database
    user = main_db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get user's FBR token
    fbr_token = user.fbr_sandbox_token if user.fbr_environment == "SANDBOX" else user.fbr_production_token
    if not fbr_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FBR credentials not configured. Please configure your FBR {user.fbr_environment} credentials in settings."
        )

    # Reset retry tracking
    invoice.retry_count = (invoice.retry_count or 0) + 1
    invoice.last_retry_at = datetime.utcnow()
    invoice.validation_errors = None
    invoice.transfer_error = None

    automation_db.add(invoice)
    automation_db.commit()

    # Run actual FBR validation (Production)
    fbr_client = FBRClient()
    try:
        is_valid, fbr_response, reference_number = await fbr_client.validate_invoice_with_user_credentials(
            invoice_data=invoice.invoice_data,
            fbr_token=fbr_token
        )

        if is_valid:
            invoice.status = AutomationInvoiceStatus.VALIDATED
            invoice.fbr_response = fbr_response
            logger.info(f"Invoice {invoice_id} FBR validation SUCCESS on retry #{invoice.retry_count}")
        else:
            invoice.status = AutomationInvoiceStatus.PENDING
            invoice.validation_errors = f"FBR validation failed: {str(fbr_response)}"
            invoice.fbr_response = fbr_response
            logger.warning(f"Invoice {invoice_id} FBR validation FAILED on retry #{invoice.retry_count}")

        automation_db.add(invoice)
        automation_db.commit()
        automation_db.refresh(invoice)

        return {
            "success": is_valid,
            "message": f"Invoice {'validated successfully' if is_valid else 'validation failed'} on retry.",
            "invoice_id": str(invoice.id),
            "retry_count": invoice.retry_count,
            "status": invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
            "validation_errors": invoice.validation_errors,
        }

    except Exception as e:
        logger.error(f"FBR validation error on retry for invoice {invoice_id}: {str(e)}")
        invoice.status = AutomationInvoiceStatus.PENDING
        invoice.validation_errors = f"Retry FBR validation error: {str(e)}"
        automation_db.add(invoice)
        automation_db.commit()
        automation_db.refresh(invoice)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FBR validation failed during retry: {str(e)}"
        )
    finally:
        await fbr_client.client.aclose()
