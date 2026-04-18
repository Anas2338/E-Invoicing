"""
Retry API endpoints for failed invoices.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from src.database.session import get_db
from src.models.user import User
from src.models.automation_invoice import AutomationInvoice
from src.services.automation_service import AutomationService
from src.schemas.automation import InvoiceRetryResponse
from src.api.middleware.auth_middleware import require_authentication

router = APIRouter(tags=["automation-retry"])


@router.post("/invoice/{invoice_id}/retry", response_model=InvoiceRetryResponse)
async def retry_failed_invoice(
    invoice_id: UUID,
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Retry a pending invoice by re-validating it immediately.

    Only invoices with 'pending' status can be retried.
    If validation passes, invoice status becomes 'validated' and will be picked up by AI agent.
    If validation fails, invoice remains 'pending' with updated error message.

    Row-level security: Only allows retry if invoice belongs to authenticated user.

    Returns:
        Updated invoice with validated status (if validation passes) or pending (if validation fails)

    Raises:
        HTTPException 400: If validation fails or invoice cannot be retried
    """
    # Retry invoice with user_id check (row-level security)
    automation_service = AutomationService(db)

    try:
        updated_invoice = automation_service.retry_failed_invoice(invoice_id, UUID(user_id))

        # Success - invoice was re-validated and is now VALIDATED
        return InvoiceRetryResponse(
            message="Invoice re-validated successfully and will be processed by AI agent in the next cycle",
            invoice_id=updated_invoice.id,
            status=updated_invoice.status,
            result={
                "invoice_number": updated_invoice.invoice_number,
                "scheduled_date": updated_invoice.scheduled_date.isoformat(),
                "scheduled_time": updated_invoice.scheduled_time.isoformat(),
                "validation_status": "passed"
            }
        )

    except ValueError as e:
        # Validation failed or other error
        error_message = str(e)

        # Check if it's a validation error (invoice still exists but validation failed)
        if "validation failed" in error_message.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Retry failed: {error_message}. Please fix the invoice data and try again."
            )
        else:
            # Other errors (not found, wrong status, etc.)
            raise HTTPException(status_code=400, detail=error_message)
