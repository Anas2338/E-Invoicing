"""
Automation report service: date-range reports over the automation database.

Mirror of the main backend's ``src/services/report_service.py``, adapted to a
different data source: automated invoices live in ``automation_invoice`` with
their payload in the ``invoice_data`` JSON column rather than in typed
``invoice_items`` rows.

The adaptation is concentrated in one place — :func:`normalize_automation_invoice`
turns an ``AutomationInvoice`` into a row dict with exactly the keys the shared
PDF and CSV services consume (the same shape ``build_report_data`` produces on
the main backend). Every aggregation below then works on those dicts, and the
report logic itself stays identical to the manual report's, so an invoice
reported here and later transferred to the main database reports the same
figures on both sides.

Filtering follows the automation dashboard's conventions
(``api/v1/automation/dashboard.py``): ownership by ``user_id``, the date range
applied to ``scheduled_date`` (the automation equivalent of ``invoice_date``),
invoice number a partial match, and customer a partial match against the
``buyer_business_name`` key inside the JSON column.
"""
import re
from datetime import date
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import String, cast
# select comes from sqlmodel, not sqlalchemy: Session.exec() only returns ORM
# instances for sqlmodel's SelectOfScalar, so a plain sqlalchemy select() here
# would hand back Row objects instead of AutomationInvoice models.
from sqlmodel import select

if TYPE_CHECKING:  # pragma: no cover - typing only, keeps the module import-free of DB setup
    from sqlalchemy.orm import Session

    from src.models.automation_invoice import AutomationInvoice

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

# Money columns of the party-wise (per-customer) report. A subset of
# INVOICE_TOTAL_FIELDS: the four totals a customer-wise sales summary is
# read for, rather than the full tax picture.
PARTY_TOTAL_FIELDS = (
    'sales_value_excluding_st',
    'sales_tax',
    'further_tax',
    'value_including_tax',
)

# Income tax sections an invoice line can fall under, in report order, with
# the withholding rates applied when the invoice was entered
# (manual_excel_helper._withholding_tax_rate, the sale invoice form and the
# automation Excel parser all agree: 236G = 0.1%, 236H = 0.5%, None = no
# withholding).
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

# Minimum token-overlap (Jaccard) for the fuzzy item-name fallback.
# Excel uploads often overwrite the saved description with a template
# string, e.g. "300 Diaper 80 Gram Per Piece" vs the saved product's
# "ADULT DIAPER  (80 GRAM PER PIECE)" — 0.8 overlap. Unrelated products
# (e.g. "BULB 30 WATT") score well below the threshold, so they stay
# separate rows.
FUZZY_MATCH_THRESHOLD = 0.55


def _num(item: dict, field: str) -> float:
    """Coerce an item field to float, treating None/empty as 0.0."""
    try:
        return float(item.get(field, 0) or 0)
    except (ValueError, TypeError):
        return 0.0


def _enum_value(value: Any) -> str:
    """Enum -> its string value; anything else stringified."""
    return value.value if hasattr(value, 'value') else str(value or '')


def normalize_automation_invoice(invoice: "AutomationInvoice") -> Dict:
    """
    Flatten an AutomationInvoice into the row dict the report services read.

    The automation payload is JSON, so every read is defensive: a column may
    be null (``invoice_number`` stays null until the transfer job assigns it,
    ``fbr_response`` only exists after an FBR submission) and the manual-upload
    path writes fewer item keys than the Excel-upload path.

    ``invoice_date`` falls back to ``scheduled_date`` — the one date every
    automation invoice always has — so a row is never dateless, and the report
    stays grouped by a real calendar day either way.
    """
    data = invoice.invoice_data or {}
    fbr_response = invoice.fbr_response or {}
    scheduled_date = getattr(invoice, 'scheduled_date', None)

    return {
        'id': invoice.id,
        'invoice_number': invoice.invoice_number or '',
        'fbr_reference_number': fbr_response.get('USIN') or fbr_response.get('usin') or '',
        'invoice_date': (data.get('invoice_date') or '').strip()
        or (scheduled_date.isoformat() if scheduled_date else ''),
        'invoice_type': data.get('invoice_type') or '',
        'buyer_business_name': data.get('buyer_business_name') or '',
        'buyer_ntn_cnic': data.get('buyer_ntn_cnic') or '',
        'buyer_province': data.get('buyer_province') or '',
        'buyer_address': data.get('buyer_address') or '',
        'seller_business_name': data.get('seller_business_name') or '',
        'seller_ntn_cnic': data.get('seller_ntn_cnic') or '',
        'seller_province': data.get('seller_province') or '',
        'seller_address': data.get('seller_address') or '',
        'status': _enum_value(invoice.status),
        'source': _enum_value(invoice.source),
        'environment': _enum_value(data.get('environment')),
        # Header-level income tax, the fallback for items that predate the
        # per-item field (see _income_tax_type).
        'income_tax': str(data.get('income_tax') or '236G').strip(),
        'items': data.get('items') or [],
        'scheduled_date': scheduled_date,
    }


def fetch_report_invoices(
    db: "Session",
    user_uuid: UUID,
    *,
    status: Optional[Any] = None,
    source: Optional[Any] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    invoice_number: Optional[str] = None,
    customer: Optional[str] = None,
) -> List["AutomationInvoice"]:
    """
    The user's automation invoices matching the dashboard filters.

    Same conditions as the dashboard's invoice list — so the report covers
    exactly the rows on screen — but unpaginated and ordered oldest first,
    which is how a report reads (the dashboard lists newest first).

    Imported lazily so this module stays importable without database
    configuration, which keeps the aggregation functions unit-testable
    offline.
    """
    from src.models.automation_invoice import AutomationInvoice

    filters = [AutomationInvoice.user_id == user_uuid]

    if status:
        filters.append(AutomationInvoice.status == status)

    if source:
        filters.append(AutomationInvoice.source == source)

    if date_from:
        filters.append(AutomationInvoice.scheduled_date >= date_from)

    if date_to:
        filters.append(AutomationInvoice.scheduled_date <= date_to)

    if invoice_number and invoice_number.strip():
        filters.append(AutomationInvoice.invoice_number.ilike(f'%{invoice_number.strip()}%'))

    if customer and customer.strip():
        filters.append(
            cast(AutomationInvoice.invoice_data['buyer_business_name'], String).ilike(
                f'%{customer.strip()}%'
            )
        )

    statement = (
        select(AutomationInvoice)
        .where(*filters)
        .order_by(AutomationInvoice.scheduled_date, AutomationInvoice.scheduled_time)
    )

    return list(db.exec(statement).all())


def resolve_effective_dates(
    rows: List[Dict],
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Tuple[str, str]:
    """
    The period the report actually covers, as YYYY-MM-DD strings.

    A filter the user set is echoed back; a side they left open is filled from
    the matched invoices' scheduled dates, so an unfiltered report is still
    self-describing in its header and filename instead of claiming an open
    range. Only when nothing matched at all does a side fall back to today,
    which keeps the filename date-shaped.

    Resolved per side rather than both-or-nothing: "from March onwards" should
    report March-to-<last invoice>, not fall back to today for both.
    """
    dates = sorted(
        row['scheduled_date'].isoformat()
        for row in rows
        if row.get('scheduled_date')
    )
    fallback = date.today().isoformat()

    resolved_from = date_from.isoformat() if date_from else (dates[0] if dates else fallback)
    resolved_to = date_to.isoformat() if date_to else (dates[-1] if dates else fallback)

    return resolved_from, resolved_to


def environment_label(rows: List[Dict]) -> Optional[str]:
    """
    The single environment the report covers, or None when it spans several
    (or none) — the PDF info block then prints "All".

    Automation invoices are always uploaded as PRODUCTION, but the label is
    derived rather than assumed so a future sandbox path can't mislabel.
    """
    environments = {row['environment'] for row in rows if row.get('environment')}
    return environments.pop() if len(environments) == 1 else None


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
        description = (getattr(product, 'product_description', '') or '').strip()
        item_name = (getattr(product, 'item_name', '') or '').strip()
        if not item_name:
            continue
        hs_code = (getattr(product, 'hs_code', '') or '').strip()

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


def compute_invoice_totals(row: Dict) -> Dict[str, float]:
    """
    Sum the report fields across an invoice row's line items.
    """
    totals = {field: 0.0 for field in INVOICE_TOTAL_FIELDS}
    for item in row.get('items') or []:
        for field, item_field in INVOICE_TOTAL_FIELDS.items():
            totals[field] += _num(item, item_field)
    return totals


def build_report_data(
    rows: List[Dict],
    date_from: str,
    date_to: str,
    saved_products: Optional[List] = None,
) -> Dict:
    """
    Build the full report payload: per-invoice rows and grand summary.

    One pass over the rows: per-invoice totals are accumulated into the
    grand totals as they are computed, so every consumer shares identical
    numbers.

    saved_products are the user's saved items (user_saved_products);
    when given, item lines are labelled with the saved item_name so the
    report matches the /products page (exact keys first, then a fuzzy
    fallback for template-style descriptions), falling back to the raw
    product_description for items that don't come from a saved product.
    """
    summary = {'total_invoices': len(rows)}
    for field in INVOICE_TOTAL_FIELDS:
        summary[field] = 0.0

    lookup = _build_item_name_lookup(saved_products)

    # Item name -> total quantity across every invoice in the range,
    # so the report also shows what was sold, not just the money totals.
    item_quantities: Dict[str, float] = {}
    for row in rows:
        for item in row.get('items') or []:
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

    invoice_rows = []
    for row in rows:
        totals = compute_invoice_totals(row)
        for field in INVOICE_TOTAL_FIELDS:
            summary[field] += totals[field]

        invoice_rows.append({
            'id': row['id'],
            'invoice_number': row['invoice_number'],
            'fbr_reference_number': row['fbr_reference_number'],
            'invoice_date': row['invoice_date'],
            'scheduled_date': (
                row['scheduled_date'].isoformat() if row.get('scheduled_date') else ''
            ),
            'invoice_type': row['invoice_type'],
            'buyer_business_name': row['buyer_business_name'],
            'status': row['status'],
            'source': row['source'],
            **totals,
        })

    return {
        'date_from': date_from,
        'date_to': date_to,
        'summary': summary,
        'items_summary': items_summary,
        'invoices': invoice_rows,
    }


def build_party_wise_report(rows: List[Dict]) -> Dict:
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
    Rows arrive date-ordered, so the earliest spelling of a name is the one
    displayed. Rows are sorted by value including tax, largest first.
    """
    parties: Dict[Tuple[str, str], Dict] = {}

    for row in rows:
        name = (row.get('buyer_business_name') or '').strip()
        ntn_cnic = (row.get('buyer_ntn_cnic') or '').strip()
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
        totals = compute_invoice_totals(row)
        for field in PARTY_TOTAL_FIELDS:
            party[field] += totals[field]

    party_rows = sorted(
        parties.values(),
        key=lambda p: (-p['value_including_tax'], p['buyer_business_name'].casefold()),
    )

    grand_totals = {'total_invoices': 0, **{field: 0.0 for field in PARTY_TOTAL_FIELDS}}
    for party in party_rows:
        grand_totals['total_invoices'] += party['total_invoices']
        for field in PARTY_TOTAL_FIELDS:
            grand_totals[field] += party[field]

    return {'parties': party_rows, 'totals': grand_totals}


def _income_tax_type(row: Dict, item: dict) -> str:
    """
    The income tax section an invoice line belongs to.

    Items carry their own income_tax_type, but some upload paths only write
    the header-level income_tax, so that is the fallback. Anything
    unrecognised resolves to 236G — the same default the withholding rate
    calculation applies — so the section a line is reported under always
    matches the rate that was charged on it.
    """
    raw = str(item.get('income_tax_type') or row.get('income_tax') or '236G').strip()
    return raw if raw in INCOME_TAX_RATES else '236G'


def build_income_tax_report(rows: List[Dict]) -> Dict:
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

    for row in rows:
        invoice_ids.add(row['id'])
        for item in row.get('items') or []:
            income_tax_type = _income_tax_type(row, item)
            section = sections.get(income_tax_type)
            if section is None:
                section = {'invoice_ids': set(), **{f: 0.0 for f in INCOME_TAX_FIELDS}}
                sections[income_tax_type] = section

            section['invoice_ids'].add(row['id'])
            for field in INCOME_TAX_FIELDS:
                section[field] += _num(item, INCOME_TAX_ITEM_FIELDS[field])

    section_rows = [
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
    for section in section_rows:
        for field in INCOME_TAX_FIELDS:
            grand_totals[field] += section[field]

    return {'sections': section_rows, 'totals': grand_totals}


def build_party_wise_income_tax_report(rows: List[Dict]) -> Dict:
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

    for row in rows:
        invoice_ids.add(row['id'])
        name = (row.get('buyer_business_name') or '').strip()
        ntn_cnic = (row.get('buyer_ntn_cnic') or '').strip()

        for item in row.get('items') or []:
            income_tax_type = _income_tax_type(row, item)
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

            party['invoice_ids'].add(row['id'])
            for field in INCOME_TAX_FIELDS:
                party[field] += _num(item, INCOME_TAX_ITEM_FIELDS[field])

    party_rows = [
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

    party_rows.sort(key=lambda p: (
        INCOME_TAX_TYPES.index(p['income_tax_type']),
        -p['sales_value_excluding_st'],
        p['buyer_business_name'].casefold(),
    ))

    grand_totals = {'total_invoices': len(invoice_ids), **{f: 0.0 for f in INCOME_TAX_FIELDS}}
    for party in party_rows:
        for field in INCOME_TAX_FIELDS:
            grand_totals[field] += party[field]

    return {'parties': party_rows, 'totals': grand_totals}
