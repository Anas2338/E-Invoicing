"""
Invoice number lookup endpoints.

Provides the main backend with the invoice numbers currently in use in the
automation database, so manual invoice creation can avoid colliding with
automation invoices that have not been transferred yet.
"""
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from src.database.session import get_automation_db
from src.models.automation_invoice import AutomationInvoice
from src.api.middleware.auth_middleware import require_authentication

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/invoice-numbers/used")
async def get_used_invoice_numbers(
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_automation_db),
) -> dict:
    """
    Get all invoice numbers in the automation database for the authenticated user.

    Includes every status (pending, validated, transferred, failed, ...):
    transferred numbers also exist in the main database, but including them
    is harmless — the caller takes the maximum suffix, not the count.

    Returns:
        {"invoice_numbers": ["INV-0006", "INV-0007", ...]}
    """
    numbers = db.exec(
        select(AutomationInvoice.invoice_number).where(
            AutomationInvoice.user_id == UUID(user_id)
        )
    ).all()

    return {"invoice_numbers": list(numbers)}
