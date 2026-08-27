"""
Report service: date-range invoice reports.

Shared query + aggregation logic consumed by both the JSON report
endpoint and the PDF report endpoint, so the web totals and the PDF
totals are identical by construction.

Filtering follows the existing conventions in invoice_service.py:
- Ownership enforced via Invoice.user_id == user_uuid
- Soft-deleted invoices excluded (is_deleted == False)
- Environment override from get_user_environment_filter
- invoice_date is a String "YYYY-MM-DD" column, so lexicographic
  >= / <= comparison is naturally inclusive and timezone-free.
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.invoice import Invoice

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Item fields summed for the report, in the same coercion convention as
# PDFService._build_totals_row (float(item.get(field, 0) or 0)).
# Every monetary field of an invoice line item is included, so the report
# shows the full tax picture (sales tax, further tax, extra tax, FED,
# withholding, discounts).
INVOICE_TOTAL_FIELDS = {
    'sales_value_excluding_st': 'value_sales_excluding_st',
    'sales_tax': 'sales_tax_applicable',
    'sales_tax_withheld_at_source': 'sales_tax_withheld_at_source',
    'further_tax': 'further_tax',
    'extra_tax': 'extra_tax',
    'fed_payable': 'fed_payable',
    'withholding_tax_amount': 'withholding_tax_amount',
    'discount': 'discount',
    'value_including_tax': 'total_values',
}


def _num(item: dict, field: str) -> float:
    """Coerce an item field to float, treating None/empty as 0.0."""
    try:
        return float(item.get(field, 0) or 0)
    except (ValueError, TypeError):
        return 0.0


def validate_date_range(date_from: Optional[str], date_to: Optional[str]) -> Tuple[str, str]:
    """
    Validate the From/To date query parameters.

    Returns normalized (date_from, date_to) strings.
    Raises HTTPException 400 when parameters are missing, malformed,
    unreal dates (e.g. 2026-02-30), or date_from > date_to.
    """
    if not date_from or not date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from and date_to query parameters are required (format YYYY-MM-DD)"
        )

    for param, value in (("date_from", date_from), ("date_to", date_to)):
        if not DATE_RE.match(value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {value}. Expected YYYY-MM-DD"
            )
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date: {value}. Expected a real date in YYYY-MM-DD format"
            )

    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must not be after date_to"
        )

    return date_from, date_to


def fetch_report_invoices(
    db: Session,
    user_uuid: UUID,
    date_from: str,
    date_to: str,
    environment: Optional[str] = None,
) -> List[Invoice]:
    """
    Fetch the user's non-deleted invoices whose invoice_date falls within
    [date_from, date_to] (inclusive), optionally scoped to an environment.
    """
    statement = select(Invoice).where(
        Invoice.user_id == user_uuid,
        Invoice.is_deleted == False,  # noqa: E712 — SQLAlchemy idiom
        Invoice.invoice_date >= date_from,
        Invoice.invoice_date <= date_to,
    )

    if environment:
        statement = statement.where(Invoice.environment == environment)

    statement = statement.order_by(Invoice.invoice_date, Invoice.created_at)

    # scalars() so we get Invoice entities, not rows (matches dashboard.py)
    return list(db.execute(statement).scalars().all())


def fetch_available_years(
    db: Session,
    user_uuid: UUID,
    environment: Optional[str] = None,
) -> List[int]:
    """
    Distinct invoice years (from invoice_date) across the user's
    non-deleted invoices, newest first. Feeds the Year dropdown on the
    report page so only years with actual data are offered.
    """
    statement = select(func.distinct(func.substr(Invoice.invoice_date, 1, 4))).where(
        Invoice.user_id == user_uuid,
        Invoice.is_deleted == False,  # noqa: E712 — SQLAlchemy idiom
    )

    if environment:
        statement = statement.where(Invoice.environment == environment)

    years = []
    for value in db.execute(statement).scalars().all():
        if value and len(value) == 4 and value.isdigit():
            years.append(int(value))
    return sorted(years, reverse=True)


def compute_invoice_totals(invoice: Invoice) -> Dict[str, float]:
    """
    Sum the report fields across an invoice's line items.
    """
    totals = {field: 0.0 for field in INVOICE_TOTAL_FIELDS}
    for item in invoice.items or []:
        for field, item_field in INVOICE_TOTAL_FIELDS.items():
            totals[field] += _num(item, item_field)
    return totals


def build_report_data(invoices: List[Invoice], date_from: str, date_to: str) -> Dict:
    """
    Build the full report payload: per-invoice rows and grand summary.

    One pass over the invoices: per-invoice totals are accumulated into
    the grand totals as they are computed, so the JSON and PDF endpoints
    share identical numbers.
    """
    summary = {'total_invoices': len(invoices)}
    for field in INVOICE_TOTAL_FIELDS:
        summary[field] = 0.0

    rows = []
    for invoice in invoices:
        totals = compute_invoice_totals(invoice)
        for field in INVOICE_TOTAL_FIELDS:
            summary[field] += totals[field]

        rows.append({
            'id': invoice.id,
            'invoice_number': invoice.external_id,
            'fbr_reference_number': invoice.fbr_reference_number,
            'invoice_date': invoice.invoice_date,
            'invoice_type': invoice.invoice_type,
            'buyer_business_name': invoice.buyer_business_name,
            'status': invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
            'source': invoice.source,
            **totals,
        })

    return {
        'date_from': date_from,
        'date_to': date_to,
        'summary': summary,
        'invoices': rows,
    }
