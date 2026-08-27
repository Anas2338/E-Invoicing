"""
Invoice report endpoints.

- GET /invoices   : summary + invoice rows for a date range (JSON)
- GET /invoices/pdf : same report as a downloadable PDF

Both endpoints enforce authentication, invoice ownership, soft-delete
exclusion, and the user's environment scope, and share the exact same
query + aggregation via report_service, so the JSON totals and the PDF
totals always match.
"""
import logging
from io import BytesIO
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from src.api.deps import get_database_session
from src.api.middleware.auth_middleware import require_authentication
from src.models.user import User
from src.schemas.report import InvoiceReportResponse, ReportYearsResponse
from src.services.invoice_service import get_user_environment_filter
from src.services.report_pdf_service import ReportPDFService
from src.services.report_service import (
    build_report_data,
    fetch_available_years,
    fetch_report_invoices,
    validate_date_range,
)
from src.utils.rate_limits import RateLimits

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/years", response_model=ReportYearsResponse)
@limiter.limit(RateLimits.REPORT_INVOICES)
def get_report_years(
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> ReportYearsResponse:
    """
    Distinct invoice years for the authenticated user, newest first.

    Only the user's own non-deleted invoices count, scoped to the
    environments their FBR tokens grant access to. Feeds the Year
    dropdown on the report page.
    """
    user_uuid = UUID(user_id)
    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(user) if user else None

    return ReportYearsResponse(years=fetch_available_years(db, user_uuid, env_filter))


@router.get("/invoices", response_model=InvoiceReportResponse)
@limiter.limit(RateLimits.REPORT_INVOICES)
def get_invoice_report(
    request: Request,
    date_from: Optional[str] = Query(None, description="From date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="To date (YYYY-MM-DD, inclusive)"),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> InvoiceReportResponse:
    """
    Generate an invoice report for the selected date range.

    Returns the summary totals and one row per matching invoice.
    Only the authenticated user's own non-deleted invoices are included,
    scoped to the environments their FBR tokens grant access to.
    """
    user_uuid = UUID(user_id)
    date_from, date_to = validate_date_range(date_from, date_to)

    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(user) if user else None

    invoices = fetch_report_invoices(db, user_uuid, date_from, date_to, env_filter)
    data = build_report_data(invoices, date_from, date_to)

    return InvoiceReportResponse(**data)


@router.get("/invoices/pdf")
@limiter.limit(RateLimits.REPORT_INVOICES)
async def get_invoice_report_pdf(
    request: Request,
    date_from: Optional[str] = Query(None, description="From date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="To date (YYYY-MM-DD, inclusive)"),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> StreamingResponse:
    """
    Generate and download the invoice report PDF for the selected date range.
    """
    user_uuid = UUID(user_id)
    date_from, date_to = validate_date_range(date_from, date_to)

    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(user) if user else None

    invoices = fetch_report_invoices(db, user_uuid, date_from, date_to, env_filter)
    data = build_report_data(invoices, date_from, date_to)

    business_name = user.name if user else "Unknown"

    try:
        pdf_service = ReportPDFService()
        pdf_bytes = pdf_service.generate_report_pdf(
            date_from=date_from,
            date_to=date_to,
            summary=data['summary'],
            rows=data['invoices'],
            business_name=business_name,
            environment=env_filter,
        )
    except Exception as e:
        logger.error(f"Failed to generate report PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report PDF",
        )

    filename = f"invoice_report_{date_from}_{date_to}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
