"""
Invoice number lookup endpoints.

Provides the main backend with the invoice numbers currently in use in the
automation database, so manual invoice creation can avoid colliding with
automation invoices that have not been transferred yet.

Company-aware (FR-008): automation invoices are keyed to the company OWNER's
user id — employees never write the automation DB. An employee caller's used
numbers therefore resolve to their owner's rows through the main users table;
owners/standalone accounts are unchanged. Deliberately NOT gated behind
automation access: employees' legitimate manual Excel flow consults this feed.
"""
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from src.database.session import get_automation_db, get_db
from src.models.automation_invoice import AutomationInvoice
from src.models.user import User
from src.api.middleware.auth_middleware import require_authentication

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/invoice-numbers/used")
async def get_used_invoice_numbers(
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_automation_db),
    main_db: Session = Depends(get_db),
) -> dict:
    """
    Get all invoice numbers in the automation database for the caller's COMPANY.

    Automation rows are keyed to the owner's id. A company-linked employee
    caller resolves to their owner via the main users table (company_id); the
    owner's rows are returned because they ARE the company's pending numbers.
    Standalone/owner callers are unchanged — their own automation rows.

    Includes every status (pending, validated, transferred, failed, ...):
    transferred numbers also exist in the main database, but including them
    is harmless — the caller takes the maximum suffix, not the count.

    Only rows that have been ASSIGNED a number are returned: since invoice
    numbers are assigned at transfer time, rows still pending/validated have
    invoice_number = NULL and must not leak into this list (NULLs would be
    stringified as "None" and poison the caller's next-number computation).

    Returns:
        {"invoice_numbers": ["INV-0006", "INV-0007", ...]}
    """
    actor_id = UUID(user_id)
    automation_user_id = actor_id

    # Company-linked member → resolve the owner whose automation rows make up
    # the company's pending numbers. Missing/unreadable main-DB row falls back
    # to the caller's own id (member rows return no numbers of their own).
    try:
        actor = main_db.get(User, actor_id)
    except (ValueError, TypeError):
        actor = None
    if (
        actor is not None
        and actor.company_id is not None
        and actor.company_id != actor.id
    ):
        automation_user_id = actor.company_id

    numbers = db.exec(
        select(AutomationInvoice.invoice_number).where(
            AutomationInvoice.user_id == automation_user_id,
            AutomationInvoice.invoice_number.is_not(None),
        )
    ).all()

    return {"invoice_numbers": list(numbers)}
