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
    Retry a failed invoice by resetting it to pending status.

    Only invoices with 'failed' status can be retried.
    The invoice will be picked up by the FTE worker in the next scheduled run.

    Row-level security: Only allows retry if invoice belongs to authenticated user.

    Returns:
        Updated invoice with pending status
    """
    # Retry invoice with user_id check (row-level security)
    automation_service = AutomationService(db)

    try:
        updated_invoice = automation_service.retry_failed_invoice(invoice_id, UUID(user_id))

        return InvoiceRetryResponse(
            message="Invoice reset to pending status and will be retried in the next scheduled run",
            invoice_id=updated_invoice.id,
            status=updated_invoice.status,
            result={
                "invoice_number": updated_invoice.invoice_number,
                "scheduled_date": updated_invoice.scheduled_date.isoformat(),
                "scheduled_time": updated_invoice.scheduled_time.isoformat()
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
