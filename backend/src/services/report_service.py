"""
Report service: date-range invoice reports.

Shared query + aggregation logic consumed by both the JSON report
endpoint and the PDF report endpoint, so the web totals and the PDF
totals are identical by construction.

Filtering follows the existing conventions in invoice_service.py:
- Ownership enforced via the company-member scope (_member_scope_ids:
  actor + every member of their company, so company data is shared)
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
from src.models.user import User

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _member_scope_ids(db: Session, user_uuid: UUID) -> List[UUID]:
    """
    Company-wide VISIBILITY scope: the actor plus every member of their
    company (deactivated employees included). Standalone accounts resolve to
    ``[user_uuid]`` — identical to pre-company behavior.
    """
    user = db.get(User, user_uuid)
    if user is None:
        return [user_uuid]
    from src.services.company_service import get_company_member_ids

    return get_company_member_ids(db, user)

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
    buyer_name: Optional[str] = None,
    buyer_ntn_cnic: Optional[str] = None,
) -> List[Invoice]:
    """
    Fetch the company's non-deleted invoices whose invoice_date falls within
    [date_from, date_to] (inclusive), optionally scoped to an environment
    and to a buyer name / NTN-CNIC.

    Buyer terms are case-insensitive substring matches (same convention as
    /invoices/buyers-from-history), so "ali" finds "Ali & Sons" and a
    partial NTN finds its invoices. When both are given they are ANDed —
    each extra filter narrows the result.
    """
    statement = select(Invoice).where(
        Invoice.user_id.in_(_member_scope_ids(db, user_uuid)),
        Invoice.is_deleted == False,  # noqa: E712 — SQLAlchemy idiom
        Invoice.invoice_date >= date_from,
        Invoice.invoice_date <= date_to,
    )

    if environment:
        statement = statement.where(Invoice.environment == environment)

    if buyer_name and buyer_name.strip():
        statement = statement.where(
            Invoice.buyer_business_name.ilike(f"%{buyer_name.strip()}%")
        )

    if buyer_ntn_cnic and buyer_ntn_cnic.strip():
        statement = statement.where(
            Invoice.buyer_ntn_cnic.ilike(f"%{buyer_ntn_cnic.strip()}%")
        )

    statement = statement.order_by(Invoice.invoice_date, Invoice.created_at)

    # scalars() so we get Invoice entities, not rows (matches dashboard.py)
    return list(db.execute(statement).scalars().all())


def fetch_available_years(
    db: Session,
    user_uuid: UUID,
    environment: Optional[str] = None,
) -> List[int]:
    """
    Distinct invoice years (from invoice_date) across the company's
    non-deleted invoices, newest first. Feeds the Year dropdown on the
    report page so only years with actual data are offered.
    """
    statement = select(func.distinct(func.substr(Invoice.invoice_date, 1, 4))).where(
        Invoice.user_id.in_(_member_scope_ids(db, user_uuid)),
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
    buyer_name: Optional[str] = None,
    buyer_ntn_cnic: Optional[str] = None,
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

    buyer_name / buyer_ntn_cnic are echoed back (normalized) so the
    client can pass the *searched* filters to the PDF/CSV downloads even
    if the user has since edited the filter inputs without re-searching.
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
        'buyer_name': (buyer_name or '').strip(),
        'buyer_ntn_cnic': (buyer_ntn_cnic or '').strip(),
        'summary': summary,
        'items_summary': items_summary,
        'invoices': rows,
    }


# Money columns of the party-wise (per-customer) report. A subset of
# INVOICE_TOTAL_FIELDS: the four totals a customer-wise sales summary is
# read for, rather than the full tax picture.
PARTY_TOTAL_FIELDS = (
    'sales_value_excluding_st',
    'sales_tax',
    'further_tax',
    'value_including_tax',
)


def build_party_wise_report(invoices: List[Invoice]) -> Dict:
    """
    Aggregate a report's invoices per customer (party).

    Returns {'parties': [...], 'totals': {...}}. Each party row carries its
    invoice count and the PARTY_TOTAL_FIELDS sums; `totals` is the same
    aggregate across every party, for the grand-total row. Because the money
    comes from the same compute_invoice_totals used by build_report_data, a
    party's figures and the overall report totals always agree.

    A party is identified by business name (case-insensitive) plus NTN/CNIC:
    the same customer typed with different casing lands in one row, while two
    genuinely different parties that happen to share a name stay separate.
    Invoices arrive date-ordered, so the earliest spelling of a name is the
    one displayed. Rows are sorted by value including tax, largest first.
    """
    parties: Dict[Tuple[str, str], Dict] = {}

    for invoice in invoices:
        name = (invoice.buyer_business_name or '').strip()
        ntn_cnic = (invoice.buyer_ntn_cnic or '').strip()
        key = (name.casefold(), ntn_cnic)

        party = parties.get(key)
        if party is None:
            party = {
                'buyer_business_name': name,
                'buyer_ntn_cnic': ntn_cnic,
                'total_invoices': 0,
                **{field: 0.0 for field in PARTY_TOTAL_FIELDS},
            }
            parties[key] = party

        party['total_invoices'] += 1
        totals = compute_invoice_totals(invoice)
        for field in PARTY_TOTAL_FIELDS:
            party[field] += totals[field]

    rows = sorted(
        parties.values(),
        key=lambda p: (-p['value_including_tax'], p['buyer_business_name'].casefold()),
    )

    grand_totals = {'total_invoices': 0, **{field: 0.0 for field in PARTY_TOTAL_FIELDS}}
    for party in rows:
        grand_totals['total_invoices'] += party['total_invoices']
        for field in PARTY_TOTAL_FIELDS:
            grand_totals[field] += party[field]

    return {'parties': rows, 'totals': grand_totals}


# Income tax sections an invoice line can fall under, in report order, with
# the withholding rates applied when the invoice was entered
# (manual_excel_helper._withholding_tax_rate and the sale invoice form agree
# on these: 236G = 0.1%, 236H = 0.5%, None = no withholding).
INCOME_TAX_TYPES = ('236G', '236H', 'None')
INCOME_TAX_RATES = {'236G': 0.001, '236H': 0.005, 'None': 0.0}

# Income tax report money columns -> the line item fields they are read from.
# The same logical-name-to-item-field convention as INVOICE_TOTAL_FIELDS,
# which is where the sales tax side of these figures comes from.
INCOME_TAX_FIELDS = ('sales_value_excluding_st', 'withholding_tax_amount')
INCOME_TAX_ITEM_FIELDS = {
    'sales_value_excluding_st': 'value_sales_excluding_st',
    'withholding_tax_amount': 'withholding_tax_amount',
}


def _income_tax_type(invoice: Invoice, item: dict) -> str:
    """
    The income tax section an invoice line belongs to.

    Items carry their own income_tax_type, but invoices created before that
    field existed only have the invoice-level income_tax, so that is the
    fallback. Anything unrecognised resolves to 236G — the same default
    _withholding_tax_rate applies — so the section a line is reported under
    always matches the rate that was charged on it.
    """
    raw = str(item.get('income_tax_type') or invoice.income_tax or '236G').strip()
    return raw if raw in INCOME_TAX_RATES else '236G'


def build_income_tax_report(invoices: List[Invoice]) -> Dict:
    """
    Aggregate a report's invoices by income tax section (236G / 236H / None).

    Returns {'sections': [...], 'totals': {...}}. Each section carries the
    number of invoices that fall under it plus the section's sales value and
    withholding tax; `totals` is the report-wide aggregate for the
    grand-total row.

    Figures are read straight off the line items — the stored
    withholding_tax_amount and the same value_sales_excluding_st the sales
    tax report sums — so the two reports' numbers reconcile by construction.
    Sections with no data are omitted, so a report over ordinary sales shows
    only the sections actually used.

    One invoice can mix sections (a 236G line and a 236H line), so the
    per-section counts can add up to more than the total invoice count; the
    total is the report's own distinct invoice count.
    """
    sections: Dict[str, Dict] = {}
    invoice_ids = set()

    for invoice in invoices:
        invoice_ids.add(invoice.id)
        for item in invoice.items or []:
            income_tax_type = _income_tax_type(invoice, item)
            section = sections.get(income_tax_type)
            if section is None:
                section = {'invoice_ids': set(), **{f: 0.0 for f in INCOME_TAX_FIELDS}}
                sections[income_tax_type] = section

            section['invoice_ids'].add(invoice.id)
            for field in INCOME_TAX_FIELDS:
                section[field] += _num(item, INCOME_TAX_ITEM_FIELDS[field])

    rows = [
        {
            'income_tax_type': income_tax_type,
            'rate': INCOME_TAX_RATES[income_tax_type],
            'total_invoices': len(sections[income_tax_type]['invoice_ids']),
            **{field: sections[income_tax_type][field] for field in INCOME_TAX_FIELDS},
        }
        for income_tax_type in INCOME_TAX_TYPES
        if income_tax_type in sections
    ]

    grand_totals = {'total_invoices': len(invoice_ids), **{f: 0.0 for f in INCOME_TAX_FIELDS}}
    for section in rows:
        for field in INCOME_TAX_FIELDS:
            grand_totals[field] += section[field]

    return {'sections': rows, 'totals': grand_totals}


def build_party_wise_income_tax_report(invoices: List[Invoice]) -> Dict:
    """
    Aggregate a report's invoices per customer *and* income tax section.

    Returns {'parties': [...], 'totals': {...}} with one row per
    (customer, section) pair, so a party that sells under both 236G and 236H
    gets a row for each and the section a figure belongs to is never
    ambiguous.

    Party identity and display name follow build_party_wise_report: business
    name (case-insensitive) plus NTN/CNIC, with the earliest spelling shown.
    Rows are grouped by section in report order, largest sales value first
    within each section, so the table reads like a 236G / 236H annexure.
    """
    parties: Dict[Tuple[str, str, str], Dict] = {}
    invoice_ids = set()

    for invoice in invoices:
        invoice_ids.add(invoice.id)
        name = (invoice.buyer_business_name or '').strip()
        ntn_cnic = (invoice.buyer_ntn_cnic or '').strip()

        for item in invoice.items or []:
            income_tax_type = _income_tax_type(invoice, item)
            key = (name.casefold(), ntn_cnic, income_tax_type)
            party = parties.get(key)
            if party is None:
                party = {
                    'buyer_business_name': name,
                    'buyer_ntn_cnic': ntn_cnic,
                    'income_tax_type': income_tax_type,
                    'rate': INCOME_TAX_RATES[income_tax_type],
                    'invoice_ids': set(),
                    **{f: 0.0 for f in INCOME_TAX_FIELDS},
                }
                parties[key] = party

            party['invoice_ids'].add(invoice.id)
            for field in INCOME_TAX_FIELDS:
                party[field] += _num(item, INCOME_TAX_ITEM_FIELDS[field])

    rows = [
        {
            'buyer_business_name': party['buyer_business_name'],
            'buyer_ntn_cnic': party['buyer_ntn_cnic'],
            'income_tax_type': party['income_tax_type'],
            'rate': party['rate'],
            'total_invoices': len(party['invoice_ids']),
            **{field: party[field] for field in INCOME_TAX_FIELDS},
        }
        for party in parties.values()
    ]

    rows.sort(key=lambda p: (
        INCOME_TAX_TYPES.index(p['income_tax_type']),
        -p['sales_value_excluding_st'],
        p['buyer_business_name'].casefold(),
    ))

    grand_totals = {'total_invoices': len(invoice_ids), **{f: 0.0 for f in INCOME_TAX_FIELDS}}
    for party in rows:
        for field in INCOME_TAX_FIELDS:
            grand_totals[field] += party[field]

    return {'parties': rows, 'totals': grand_totals}
