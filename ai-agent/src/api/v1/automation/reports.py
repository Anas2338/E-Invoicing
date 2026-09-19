"""
Automation report endpoints: date-range reports over the automation database.

Sales tax:
- GET /invoices/pdf                     : summary + invoice rows as a PDF
- GET /invoices/csv                     : line-item-level CSV export
- GET /invoices/party-wise-pdf          : per-customer totals as a PDF

Income tax (236G / 236H):
- GET /invoices/income-tax-pdf          : per-section totals as a PDF
- GET /invoices/income-tax-csv          : line-item-level income tax CSV
- GET /invoices/income-tax-party-wise-pdf : per-customer per-section PDF

Mirror of the main backend's ``api/v1/reports.py``, reading
``automation_invoice`` rows instead of main-database invoices — the automation
database is only reachable from this service, so the report has to live here.
Every endpoint shares the same query and aggregation via
``automation_report_service``, so the PDF totals and the CSV rows always match
the invoice rows they were built from.

Unlike the manual report, **every filter is optional**: the automation
dashboard's filters (status, source, scheduled-date range, invoice number,
customer) are passed through as-is, and a report with no filters at all
covers the user's whole automation history. The period printed in the header
and filename is resolved from the matched invoices when a date filter is
absent (see ``resolve_effective_dates``), so a download is always
self-describing instead of arriving as "unknown range".

The main database is read only for presentation: the user's business name for
the header block and their saved products for item-name resolution. Both are
best-effort — neither can fail the download.
"""
import logging
from datetime import date
from io import BytesIO
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlmodel import Session, select

from src.database.session import get_automation_db, get_db
from src.middleware.rbac import require_automation_access
from src.models.user import User
from src.models.user_saved_product import UserSavedProduct
from src.services.automation_report_csv_service import (
    generate_income_tax_csv,
    generate_report_csv,
)
from src.services.automation_report_pdf_service import AutomationReportPDFService
from src.services.automation_report_service import (
    build_income_tax_report,
    build_party_wise_income_tax_report,
    build_party_wise_report,
    build_report_data,
    environment_label,
    fetch_report_invoices,
    normalize_automation_invoice,
    resolve_effective_dates,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["automation-reports"])


# ── Shared helpers ────────────────────────────────────────────────────


def _enum_text(value: Any) -> str:
    """Status/source as their string value, whether the enum or a raw string."""
    return value.value if hasattr(value, 'value') else str(value)


def _filter_note(
    *,
    status_filter: Optional[Any],
    source_filter: Optional[Any],
    invoice_number: Optional[str],
    customer: Optional[str],
) -> Optional[str]:
    """
    Human-readable description of the dashboard filters applied on top of the
    reported period, printed in the PDF header so a filtered report is never
    mistaken for a full one.

    The date range is deliberately absent: the info block already prints the
    period it covers, resolved. None when no filter is active.
    """
    parts = []
    if status_filter:
        parts.append(f"Status: {_enum_text(status_filter)}")
    if source_filter:
        parts.append(f"Source: {_enum_text(source_filter)}")
    if invoice_number and invoice_number.strip():
        parts.append(f"Invoice: {invoice_number.strip()}")
    if customer and customer.strip():
        parts.append(f"Customer: {customer.strip()}")
    return " | ".join(parts) if parts else None


def _business_name(main_db: Session, user_uuid: UUID) -> str:
    """
    The name shown in the report header: the account name, falling back to
    the registered FBR business name, then "Unknown".

    Read from the main database because automation rows carry a snapshot of
    the seller at upload time, which may predate a rename.
    """
    try:
        user = main_db.get(User, user_uuid)
    except Exception as e:  # Main DB is optional here; never fail the download
        logger.warning(f"Could not load user for report header: {e}")
        return "Unknown"

    if not user:
        return "Unknown"
    return user.name or user.fbr_business_name or "Unknown"


def _saved_products(main_db: Session, user_uuid: UUID) -> list:
    """
    The user's saved products, for resolving item names in the CSV exports.

    Best-effort: the CSVs fall back to the raw product_description when this
    is unavailable, which is a cosmetic loss rather than a failed download.
    """
    try:
        statement = select(UserSavedProduct).where(
            UserSavedProduct.user_id == user_uuid
        )
        return list(main_db.exec(statement).all())
    except Exception as e:
        logger.warning(f"Could not load saved products for report export: {e}")
        return []


def _collect_rows(
    db: Session,
    user_uuid: UUID,
    *,
    status_filter: Optional[Any],
    source_filter: Optional[Any],
    date_from: Optional[date],
    date_to: Optional[date],
    invoice_number: Optional[str],
    customer: Optional[str],
) -> tuple:
    """
    Fetch the matching automation invoices and flatten them for the report.

    Returns ``(rows, effective_from, effective_to)`` — the period is resolved
    here because every endpoint needs it for both the header and the filename,
    and a filtered-but-dateless report must still name the range it covers.
    """
    invoices = fetch_report_invoices(
        db,
        user_uuid,
        status=status_filter,
        source=source_filter,
        date_from=date_from,
        date_to=date_to,
        invoice_number=invoice_number,
        customer=customer,
    )
    rows = [normalize_automation_invoice(invoice) for invoice in invoices]
    effective_from, effective_to = resolve_effective_dates(rows, date_from, date_to)
    return rows, effective_from, effective_to


def _pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _csv_response(csv_text: str, filename: str) -> Response:
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Sales tax ─────────────────────────────────────────────────────────


@router.get("/invoices/pdf")
async def get_invoice_report_pdf(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    source_filter: Optional[str] = Query(None, alias="source", description="Filter by source"),
    date_from: Optional[date] = Query(None, description="Filter by scheduled date from"),
    date_to: Optional[date] = Query(None, description="Filter by scheduled date to"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number (partial match)"),
    customer: Optional[str] = Query(None, description="Filter by buyer business name (partial match)"),
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
    main_db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Generate and download the automation invoice report PDF.

    Covers the user's automation invoices matching the dashboard filters, as
    a summary block plus one row per invoice, with a grand-total row. Active
    filters are printed in the header so the download is self-describing.
    """
    user_uuid = UUID(user_id)
    rows, eff_from, eff_to = _collect_rows(
        db, user_uuid,
        status_filter=status_filter,
        source_filter=source_filter,
        date_from=date_from,
        date_to=date_to,
        invoice_number=invoice_number,
        customer=customer,
    )
    data = build_report_data(rows, eff_from, eff_to)

    try:
        pdf_bytes = AutomationReportPDFService().generate_report_pdf(
            date_from=eff_from,
            date_to=eff_to,
            summary=data['summary'],
            rows=data['invoices'],
            business_name=_business_name(main_db, user_uuid),
            environment=environment_label(rows),
            filter_note=_filter_note(
                status_filter=status_filter,
                source_filter=source_filter,
                invoice_number=invoice_number,
                customer=customer,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to generate automation report PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate automation report PDF",
        )

    return _pdf_response(pdf_bytes, f"automation_invoice_report_{eff_from}_{eff_to}.pdf")


@router.get("/invoices/party-wise-pdf")
async def get_party_wise_report_pdf(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    source_filter: Optional[str] = Query(None, alias="source", description="Filter by source"),
    date_from: Optional[date] = Query(None, description="Filter by scheduled date from"),
    date_to: Optional[date] = Query(None, description="Filter by scheduled date to"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number (partial match)"),
    customer: Optional[str] = Query(None, description="Filter by buyer business name (partial match)"),
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
    main_db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Generate and download the party-wise (per-customer) report PDF.

    One row per customer with their invoice count and totals, largest party
    first, plus a grand-total row. Same invoice scope as the invoice report,
    so the per-party figures add up to its totals.
    """
    user_uuid = UUID(user_id)
    rows, eff_from, eff_to = _collect_rows(
        db, user_uuid,
        status_filter=status_filter,
        source_filter=source_filter,
        date_from=date_from,
        date_to=date_to,
        invoice_number=invoice_number,
        customer=customer,
    )
    data = build_party_wise_report(rows)

    try:
        pdf_bytes = AutomationReportPDFService().generate_party_wise_pdf(
            date_from=eff_from,
            date_to=eff_to,
            parties=data['parties'],
            totals=data['totals'],
            business_name=_business_name(main_db, user_uuid),
            environment=environment_label(rows),
            filter_note=_filter_note(
                status_filter=status_filter,
                source_filter=source_filter,
                invoice_number=invoice_number,
                customer=customer,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to generate party-wise automation report PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate party-wise automation report PDF",
        )

    return _pdf_response(pdf_bytes, f"automation_party_wise_report_{eff_from}_{eff_to}.pdf")


@router.get("/invoices/csv")
def get_invoice_report_csv(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    source_filter: Optional[str] = Query(None, alias="source", description="Filter by source"),
    date_from: Optional[date] = Query(None, description="Filter by scheduled date from"),
    date_to: Optional[date] = Query(None, description="Filter by scheduled date to"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number (partial match)"),
    customer: Optional[str] = Query(None, description="Filter by buyer business name (partial match)"),
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
    main_db: Session = Depends(get_db),
) -> Response:
    """
    Generate and download the automation invoice report CSV.

    One row per invoice line item with invoice-level fields repeated per item,
    so the export can be pivoted or aggregated in Excel. Same invoice scope
    and saved-product item-name resolution as the PDF endpoints.
    """
    user_uuid = UUID(user_id)
    rows, eff_from, eff_to = _collect_rows(
        db, user_uuid,
        status_filter=status_filter,
        source_filter=source_filter,
        date_from=date_from,
        date_to=date_to,
        invoice_number=invoice_number,
        customer=customer,
    )

    csv_text = generate_report_csv(rows, _saved_products(main_db, user_uuid))

    return _csv_response(csv_text, f"automation_invoice_report_{eff_from}_{eff_to}.csv")


# ── Income tax (236G / 236H) ──────────────────────────────────────────


@router.get("/invoices/income-tax-pdf")
async def get_income_tax_report_pdf(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    source_filter: Optional[str] = Query(None, alias="source", description="Filter by source"),
    date_from: Optional[date] = Query(None, description="Filter by scheduled date from"),
    date_to: Optional[date] = Query(None, description="Filter by scheduled date to"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number (partial match)"),
    customer: Optional[str] = Query(None, description="Filter by buyer business name (partial match)"),
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
    main_db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Generate and download the income tax (236G / 236H) report PDF.

    One row per income tax section with the rate applied, the number of
    invoices under it, and the sales value and withholding tax it was charged
    on, plus a grand-total row. Same invoice scope as the sales tax report, so
    the two reconcile.
    """
    user_uuid = UUID(user_id)
    rows, eff_from, eff_to = _collect_rows(
        db, user_uuid,
        status_filter=status_filter,
        source_filter=source_filter,
        date_from=date_from,
        date_to=date_to,
        invoice_number=invoice_number,
        customer=customer,
    )
    data = build_income_tax_report(rows)

    try:
        pdf_bytes = AutomationReportPDFService().generate_income_tax_pdf(
            date_from=eff_from,
            date_to=eff_to,
            sections=data['sections'],
            totals=data['totals'],
            business_name=_business_name(main_db, user_uuid),
            environment=environment_label(rows),
            filter_note=_filter_note(
                status_filter=status_filter,
                source_filter=source_filter,
                invoice_number=invoice_number,
                customer=customer,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to generate income tax automation report PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate income tax automation report PDF",
        )

    return _pdf_response(pdf_bytes, f"automation_income_tax_report_{eff_from}_{eff_to}.pdf")


@router.get("/invoices/income-tax-party-wise-pdf")
async def get_party_wise_income_tax_report_pdf(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    source_filter: Optional[str] = Query(None, alias="source", description="Filter by source"),
    date_from: Optional[date] = Query(None, description="Filter by scheduled date from"),
    date_to: Optional[date] = Query(None, description="Filter by scheduled date to"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number (partial match)"),
    customer: Optional[str] = Query(None, description="Filter by buyer business name (partial match)"),
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
    main_db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Generate and download the party-wise income tax report PDF.

    One row per customer *and* income tax section — a party selling under both
    236G and 236H gets a row for each — with the sales value and withholding
    tax reported under that section, plus a grand-total row.
    """
    user_uuid = UUID(user_id)
    rows, eff_from, eff_to = _collect_rows(
        db, user_uuid,
        status_filter=status_filter,
        source_filter=source_filter,
        date_from=date_from,
        date_to=date_to,
        invoice_number=invoice_number,
        customer=customer,
    )
    data = build_party_wise_income_tax_report(rows)

    try:
        pdf_bytes = AutomationReportPDFService().generate_party_wise_income_tax_pdf(
            date_from=eff_from,
            date_to=eff_to,
            parties=data['parties'],
            totals=data['totals'],
            business_name=_business_name(main_db, user_uuid),
            environment=environment_label(rows),
            filter_note=_filter_note(
                status_filter=status_filter,
                source_filter=source_filter,
                invoice_number=invoice_number,
                customer=customer,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to generate party-wise income tax automation report PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate party-wise income tax automation report PDF",
        )

    return _pdf_response(
        pdf_bytes, f"automation_party_wise_income_tax_report_{eff_from}_{eff_to}.pdf"
    )


@router.get("/invoices/income-tax-csv")
def get_income_tax_report_csv(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    source_filter: Optional[str] = Query(None, alias="source", description="Filter by source"),
    date_from: Optional[date] = Query(None, description="Filter by scheduled date from"),
    date_to: Optional[date] = Query(None, description="Filter by scheduled date to"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number (partial match)"),
    customer: Optional[str] = Query(None, description="Filter by buyer business name (partial match)"),
    user_id: str = Depends(require_automation_access),
    db: Session = Depends(get_automation_db),
    main_db: Session = Depends(get_db),
) -> Response:
    """
    Generate and download the income tax report CSV.

    One row per invoice line item with the income tax section it falls under,
    the rate applied, and the sales value and withholding tax it was charged
    on. Same invoice scope and item-name resolution as the sales tax CSV.
    """
    user_uuid = UUID(user_id)
    rows, eff_from, eff_to = _collect_rows(
        db, user_uuid,
        status_filter=status_filter,
        source_filter=source_filter,
        date_from=date_from,
        date_to=date_to,
        invoice_number=invoice_number,
        customer=customer,
    )

    csv_text = generate_income_tax_csv(rows, _saved_products(main_db, user_uuid))

    return _csv_response(csv_text, f"automation_income_tax_report_{eff_from}_{eff_to}.csv")
