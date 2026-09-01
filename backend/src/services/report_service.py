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


# Minimum token-overlap (Jaccard) for the fuzzy item-name fallback.
# Excel uploads often overwrite the saved description with a template
# string, e.g. "300 Diaper 80 Gram Per Piece" vs the saved product's
# "ADULT DIAPER  (80 GRAM PER PIECE)" — 0.8 overlap. Unrelated products
# (e.g. "BULB 30 WATT") score well below the threshold, so they stay
# separate rows.
FUZZY_MATCH_THRESHOLD = 0.55


def _token_set(text: str) -> set:
    """Lowercased alphanumeric tokens of a description; single-char
    tokens dropped so codes like 'P.C' don't pollute the match."""
    return {token for token in re.split(r'[^a-z0-9]+', str(text).lower()) if len(token) > 1}


def _jaccard(a: set, b: set) -> float:
    """Token overlap ratio: 1.0 = identical wording, 0.0 = nothing shared."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _build_item_name_lookup(saved_products: Optional[List]) -> Dict:
    """
    Build the matching table from the user's saved products (/products
    page) so the report can show the friendly Item Name instead of the
    raw FBR product_description.

    Two tiers, most specific first:
    - exact keys: (hs_code, product_description) -> item_name,
      product_description -> item_name, and item_name -> itself (for
      items typed with the saved name)
    - fuzzy candidates: saved descriptions to fuzzy-match against, used
      when no exact key hits (see FUZZY_MATCH_THRESHOLD)

    First match wins per key, mirroring the saved-items table.
    """
    exact: Dict = {}
    fuzzy: List[Dict] = []
    seen = set()

    for product in saved_products or []:
        description = (product.product_description or '').strip()
        item_name = (product.item_name or '').strip()
        if not item_name:
            continue
        hs_code = (product.hs_code or '').strip()

        if description:
            if hs_code:
                exact.setdefault((hs_code, description), item_name)
            exact.setdefault(description, item_name)
            # Dedupe repeated saved rows (e.g. ITEM-001 / ITEM-002
            # carrying the same product) so they don't split the vote.
            if (hs_code, description) not in seen:
                seen.add((hs_code, description))
                fuzzy.append({
                    'tokens': _token_set(description),
                    'name': item_name,
                    'hs': hs_code,
                })
        if description != item_name:
            exact.setdefault(item_name, item_name)

    return {'exact': exact, 'fuzzy': fuzzy}


def _resolve_item_name(
    description: str,
    hs_code: str,
    lookup: Dict,
) -> str:
    """
    Resolve an invoice item's product_description to the saved item_name.

    Exact (hs_code, description) / description / item_name hits win
    outright. Otherwise the closest fuzzy candidate above the threshold
    wins; ties prefer the candidate with the same HS code, so
    "300 Diaper 80 Gram Per Piece" resolves to the saved
    "ADULT DIAPER" instead of a differently-coded lookalike.
    Falls back to the raw description when nothing matches.
    """
    exact = lookup['exact']
    name = exact.get((hs_code, description)) or exact.get(description)
    if name:
        return name

    tokens = _token_set(description)
    best = None
    for candidate in lookup['fuzzy']:
        score = _jaccard(tokens, candidate['tokens'])
        if score < FUZZY_MATCH_THRESHOLD:
            continue
        if best is None or score > best['score'] or (
            score == best['score'] and hs_code == candidate['hs'] and best['hs'] != candidate['hs']
        ):
            best = {'score': score, 'name': candidate['name'], 'hs': candidate['hs']}

    return best['name'] if best else description


def build_report_data(
    invoices: List[Invoice],
    date_from: str,
    date_to: str,
    saved_products: Optional[List] = None,
) -> Dict:
    """
    Build the full report payload: per-invoice rows and grand summary.

    One pass over the invoices: per-invoice totals are accumulated into
    the grand totals as they are computed, so the JSON and PDF endpoints
    share identical numbers.

    saved_products are the user's saved items (user_saved_products);
    when given, item lines are labelled with the saved item_name so the
    report matches the /products page (exact keys first, then a fuzzy
    fallback for template-style descriptions), falling back to the raw
    product_description for items that don't come from a saved product.
    """
    summary = {'total_invoices': len(invoices)}
    for field in INVOICE_TOTAL_FIELDS:
        summary[field] = 0.0

    lookup = _build_item_name_lookup(saved_products)

    # Item name -> total quantity across every invoice in the range,
    # so the report also shows what was sold, not just the money totals.
    item_quantities: Dict[str, float] = {}
    for invoice in invoices:
        for item in invoice.items or []:
            description = (item.get('product_description') or '').strip()
            if not description:
                continue
            hs_code = (item.get('hs_code') or '').strip()
            item_name = _resolve_item_name(description, hs_code, lookup)
            item_quantities[item_name] = item_quantities.get(item_name, 0.0) + _num(item, 'quantity')

    items_summary = [
        {'item_name': item_name, 'quantity': quantity}
        for item_name, quantity in sorted(
            item_quantities.items(), key=lambda kv: kv[1], reverse=True
        )
    ]

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
        'items_summary': items_summary,
        'invoices': rows,
    }
