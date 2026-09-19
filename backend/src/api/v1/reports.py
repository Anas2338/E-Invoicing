"""
Invoice report endpoints.

Sales tax:
- GET /invoices   : summary + invoice rows for a date range (JSON)
- GET /invoices/pdf : same report as a downloadable PDF
- GET /invoices/party-wise-pdf : per-customer totals as a downloadable PDF
- GET /invoices/csv : line-item-level report as a downloadable CSV

Income tax (236G / 236H):
- GET /invoices/income-tax-pdf : per-section totals as a downloadable PDF
- GET /invoices/income-tax-party-wise-pdf : per-customer per-section PDF
- GET /invoices/income-tax-csv : line-item-level income tax CSV

All endpoints enforce authentication, invoice ownership, soft-delete
exclusion, and the user's environment scope, and share the exact same
query + aggregation via report_service, so the JSON totals, the PDF
totals and the CSV rows always match.
"""
import logging
from io import BytesIO
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import get_database_session
from src.api.middleware.auth_middleware import require_authentication
from src.models.user import User
from src.models.user_saved_product import UserSavedProduct
from src.services.company_service import get_company_member_ids
from src.schemas.report import InvoiceReportResponse, ReportYearsResponse
from src.services.invoice_service import get_user_environment_filter
from src.services.report_csv_service import generate_income_tax_csv, generate_report_csv
from src.services.report_pdf_service import ReportPDFService
from src.services.report_service import (
    build_income_tax_report,
    build_party_wise_income_tax_report,
    build_party_wise_report,
    build_report_data,
    fetch_available_years,
    fetch_report_invoices,
    validate_date_range,
)
from src.utils.rate_limits import RateLimits

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _buyer_filter_note(buyer_name: Optional[str], buyer_ntn_cnic: Optional[str]) -> Optional[str]:
    """
    Human-readable description of the buyer filters, for the PDF info block.
    None when no buyer filter is active (report covers every buyer).
    """
    parts = []
    if buyer_name and buyer_name.strip():
        parts.append(f"Customer: {buyer_name.strip()}")
    if buyer_ntn_cnic and buyer_ntn_cnic.strip():
        parts.append(f"Customer NTN/CNIC: {buyer_ntn_cnic.strip()}")
    return " | ".join(parts) if parts else None


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
    env_filter = get_user_environment_filter(db, user) if user else None

    return ReportYearsResponse(years=fetch_available_years(db, user_uuid, env_filter))


@router.get("/invoices", response_model=InvoiceReportResponse)
@limiter.limit(RateLimits.REPORT_INVOICES)
def get_invoice_report(
    request: Request,
    date_from: Optional[str] = Query(None, description="From date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="To date (YYYY-MM-DD, inclusive)"),
    buyer_name: Optional[str] = Query(None, description="Customer/buyer business name (partial, case-insensitive)"),
    buyer_ntn_cnic: Optional[str] = Query(None, description="Customer/buyer NTN or CNIC (partial)"),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> InvoiceReportResponse:
    """
    Generate an invoice report for the selected date range.

    Returns the summary totals and one row per matching invoice.
    Only the authenticated user's own non-deleted invoices are included,
    scoped to the environments their FBR tokens grant access to.
    Optionally narrowed to a customer name and/or NTN-CNIC.
    """
    user_uuid = UUID(user_id)
    date_from, date_to = validate_date_range(date_from, date_to)

    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(db, user) if user else None

    invoices = fetch_report_invoices(
        db, user_uuid, date_from, date_to, env_filter, buyer_name, buyer_ntn_cnic
    )
    member_ids = get_company_member_ids(db, user) if user else [user_uuid]
    saved_products = db.execute(
        select(UserSavedProduct).where(UserSavedProduct.user_id.in_(member_ids))
    ).scalars().all()
    data = build_report_data(
        invoices, date_from, date_to, saved_products, buyer_name, buyer_ntn_cnic
    )

    return InvoiceReportResponse(**data)


@router.get("/invoices/pdf")
@limiter.limit(RateLimits.REPORT_INVOICES)
async def get_invoice_report_pdf(
    request: Request,
    date_from: Optional[str] = Query(None, description="From date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="To date (YYYY-MM-DD, inclusive)"),
    buyer_name: Optional[str] = Query(None, description="Customer/buyer business name (partial, case-insensitive)"),
    buyer_ntn_cnic: Optional[str] = Query(None, description="Customer/buyer NTN or CNIC (partial)"),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> StreamingResponse:
    """
    Generate and download the invoice report PDF for the selected date range.

    Applies the same optional customer name / NTN-CNIC filters as the JSON
    endpoint, and prints them in the PDF header so a filtered report is
    self-describing.
    """
    user_uuid = UUID(user_id)
    date_from, date_to = validate_date_range(date_from, date_to)

    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(db, user) if user else None

    invoices = fetch_report_invoices(
        db, user_uuid, date_from, date_to, env_filter, buyer_name, buyer_ntn_cnic
    )
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
            filter_note=_buyer_filter_note(buyer_name, buyer_ntn_cnic),
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


@router.get("/invoices/party-wise-pdf")
@limiter.limit(RateLimits.REPORT_INVOICES)
async def get_party_wise_report_pdf(
    request: Request,
    date_from: Optional[str] = Query(None, description="From date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="To date (YYYY-MM-DD, inclusive)"),
    buyer_name: Optional[str] = Query(None, description="Customer/buyer business name (partial, case-insensitive)"),
    buyer_ntn_cnic: Optional[str] = Query(None, description="Customer/buyer NTN or CNIC (partial)"),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> StreamingResponse:
    """
    Generate and download the party-wise (per-customer) report PDF.

    One row per customer with their invoice count and totals (Sales Value
    Excl. Tax, Sales Tax, Further Tax, Value Incl. Tax), largest party first,
    plus a grand-total row. Same invoice scope — date range and optional
    customer name / NTN-CNIC filters — as the other report endpoints, so the
    per-party figures add up to the invoice report's totals.
    """
    user_uuid = UUID(user_id)
    date_from, date_to = validate_date_range(date_from, date_to)

    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(db, user) if user else None

    invoices = fetch_report_invoices(
        db, user_uuid, date_from, date_to, env_filter, buyer_name, buyer_ntn_cnic
    )
    data = build_party_wise_report(invoices)

    business_name = user.name if user else "Unknown"

    try:
        pdf_service = ReportPDFService()
        pdf_bytes = pdf_service.generate_party_wise_pdf(
            date_from=date_from,
            date_to=date_to,
            parties=data['parties'],
            totals=data['totals'],
            business_name=business_name,
            environment=env_filter,
            filter_note=_buyer_filter_note(buyer_name, buyer_ntn_cnic),
        )
    except Exception as e:
        logger.error(f"Failed to generate party-wise report PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate party-wise report PDF",
        )

    filename = f"party_wise_report_{date_from}_{date_to}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/invoices/csv")
@limiter.limit(RateLimits.REPORT_INVOICES)
def get_invoice_report_csv(
    request: Request,
    date_from: Optional[str] = Query(None, description="From date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="To date (YYYY-MM-DD, inclusive)"),
    buyer_name: Optional[str] = Query(None, description="Customer/buyer business name (partial, case-insensitive)"),
    buyer_ntn_cnic: Optional[str] = Query(None, description="Customer/buyer NTN or CNIC (partial)"),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> Response:
    """
    Generate and download the invoice report CSV for the selected date range.

    One row per invoice line item, with invoice-level fields repeated per
    item, so the export can be pivoted or aggregated in Excel. Uses the
    same invoice scope — including the optional customer name / NTN-CNIC
    filters — and saved-product item-name resolution as the JSON and PDF
    endpoints.
    """
    user_uuid = UUID(user_id)
    date_from, date_to = validate_date_range(date_from, date_to)

    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(db, user) if user else None

    invoices = fetch_report_invoices(
        db, user_uuid, date_from, date_to, env_filter, buyer_name, buyer_ntn_cnic
    )
    member_ids = get_company_member_ids(db, user) if user else [user_uuid]
    saved_products = db.execute(
        select(UserSavedProduct).where(UserSavedProduct.user_id.in_(member_ids))
    ).scalars().all()

    csv_text = generate_report_csv(invoices, saved_products)

    filename = f"invoice_report_{date_from}_{date_to}.csv"

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/invoices/income-tax-pdf")
@limiter.limit(RateLimits.REPORT_INVOICES)
async def get_income_tax_report_pdf(
    request: Request,
    date_from: Optional[str] = Query(None, description="From date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="To date (YYYY-MM-DD, inclusive)"),
    buyer_name: Optional[str] = Query(None, description="Customer/buyer business name (partial, case-insensitive)"),
    buyer_ntn_cnic: Optional[str] = Query(None, description="Customer/buyer NTN or CNIC (partial)"),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> StreamingResponse:
    """
    Generate and download the income tax (236G / 236H) report PDF.

    One row per income tax section with the rate applied, the number of
    invoices under it, and the sales value and withholding tax it was
    charged on, plus a grand-total row. Same invoice scope — date range and
    optional customer name / NTN-CNIC filters — as the sales tax report, so
    the two reports reconcile.
    """
    user_uuid = UUID(user_id)
    date_from, date_to = validate_date_range(date_from, date_to)

    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(db, user) if user else None

    invoices = fetch_report_invoices(
        db, user_uuid, date_from, date_to, env_filter, buyer_name, buyer_ntn_cnic
    )
    data = build_income_tax_report(invoices)

    business_name = user.name if user else "Unknown"

    try:
        pdf_service = ReportPDFService()
        pdf_bytes = pdf_service.generate_income_tax_pdf(
            date_from=date_from,
            date_to=date_to,
            sections=data['sections'],
            totals=data['totals'],
            business_name=business_name,
            environment=env_filter,
            filter_note=_buyer_filter_note(buyer_name, buyer_ntn_cnic),
        )
    except Exception as e:
        logger.error(f"Failed to generate income tax report PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate income tax report PDF",
        )

    filename = f"income_tax_report_{date_from}_{date_to}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/invoices/income-tax-party-wise-pdf")
@limiter.limit(RateLimits.REPORT_INVOICES)
async def get_party_wise_income_tax_report_pdf(
    request: Request,
    date_from: Optional[str] = Query(None, description="From date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="To date (YYYY-MM-DD, inclusive)"),
    buyer_name: Optional[str] = Query(None, description="Customer/buyer business name (partial, case-insensitive)"),
    buyer_ntn_cnic: Optional[str] = Query(None, description="Customer/buyer NTN or CNIC (partial)"),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> StreamingResponse:
    """
    Generate and download the party-wise income tax report PDF.

    One row per customer *and* income tax section — a party selling under
    both 236G and 236H gets a row for each — with the sales value and
    withholding tax reported under that section, largest party first within
    each section, plus a grand-total row.
    """
    user_uuid = UUID(user_id)
    date_from, date_to = validate_date_range(date_from, date_to)

    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(db, user) if user else None

    invoices = fetch_report_invoices(
        db, user_uuid, date_from, date_to, env_filter, buyer_name, buyer_ntn_cnic
    )
    data = build_party_wise_income_tax_report(invoices)

    business_name = user.name if user else "Unknown"

    try:
        pdf_service = ReportPDFService()
        pdf_bytes = pdf_service.generate_party_wise_income_tax_pdf(
            date_from=date_from,
            date_to=date_to,
            parties=data['parties'],
            totals=data['totals'],
            business_name=business_name,
            environment=env_filter,
            filter_note=_buyer_filter_note(buyer_name, buyer_ntn_cnic),
        )
    except Exception as e:
        logger.error(f"Failed to generate party-wise income tax PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate party-wise income tax PDF",
        )

    filename = f"party_wise_income_tax_report_{date_from}_{date_to}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/invoices/income-tax-csv")
@limiter.limit(RateLimits.REPORT_INVOICES)
def get_income_tax_report_csv(
    request: Request,
    date_from: Optional[str] = Query(None, description="From date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="To date (YYYY-MM-DD, inclusive)"),
    buyer_name: Optional[str] = Query(None, description="Customer/buyer business name (partial, case-insensitive)"),
    buyer_ntn_cnic: Optional[str] = Query(None, description="Customer/buyer NTN or CNIC (partial)"),
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_database_session),
) -> Response:
    """
    Generate and download the income tax report CSV.

    One row per invoice line item with the income tax section it falls
    under, the rate applied, and the sales value and withholding tax it was
    charged on. Uses the same invoice scope and saved-product item-name
    resolution as the sales tax CSV.
    """
    user_uuid = UUID(user_id)
    date_from, date_to = validate_date_range(date_from, date_to)

    user = db.get(User, user_uuid)
    env_filter = get_user_environment_filter(db, user) if user else None

    invoices = fetch_report_invoices(
        db, user_uuid, date_from, date_to, env_filter, buyer_name, buyer_ntn_cnic
    )
    member_ids = get_company_member_ids(db, user) if user else [user_uuid]
    saved_products = db.execute(
        select(UserSavedProduct).where(UserSavedProduct.user_id.in_(member_ids))
    ).scalars().all()

    csv_text = generate_income_tax_csv(invoices, saved_products)

    filename = f"income_tax_report_{date_from}_{date_to}.csv"

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
