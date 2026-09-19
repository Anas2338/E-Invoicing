"""
Report CSV generation service.

Generates a line-item-level CSV export for a date range, with one row per
invoice item. Invoice-level fields (invoice_number, buyer, date, etc.) are
repeated for each item row, so the export is self-contained and can be
pivoted/aggregated in Excel or BI tools.

Two exports share this shape:
- Sales tax: the full tax picture per item (sales tax, further tax, FED,
  discounts, ...).
- Income tax: the 236G / 236H position per item — the section it falls
  under, the rate applied, and the sales value and withholding tax it was
  charged on.

Item names are resolved via the same lookup logic used by the JSON report
(exact keys first, then fuzzy matching), so both CSVs show the same friendly
names as the report page and PDFs.
"""
import csv
from io import StringIO
from typing import List, Optional

from src.models.invoice import Invoice
from src.services.report_service import (
    INCOME_TAX_RATES,
    _build_item_name_lookup,
    _income_tax_type,
    _resolve_item_name,
)

# Excel only decodes a CSV as UTF-8 when it starts with this BOM; without it
# non-ASCII business names/addresses render as mojibake when opened by
# double-click. Spreadsheet apps strip it silently.
UTF8_BOM = '﻿'


def _clean_csv_value(value) -> str:
    """Coerce a value to a clean CSV string, treating None/empty as empty string."""
    if value is None or value == '':
        return ''
    return str(value).strip()


def _fmt_amount(value) -> str:
    """Money/rate fields: fixed 2 decimals, no thousands separator so Excel
    parses the cell as a number rather than text."""
    return f"{_num_value(value):.2f}"


def _fmt_qty(value) -> str:
    """Quantities: up to 4 decimals, trailing zeros trimmed (1.5 not 1.5000)."""
    text = f"{_num_value(value):.4f}".rstrip('0').rstrip('.')
    return text or '0'


def _num_value(value) -> float:
    """Coerce an item field to float, treating None/empty/unparseable as 0.0."""
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def generate_report_csv(
    invoices: List[Invoice],
    saved_products: Optional[List] = None,
) -> str:
    """
    Generate a CSV export of invoices with one row per line item.

    Columns:
    - Invoice fields: invoice_number, fbr_reference_number, invoice_date,
      invoice_type, buyer business name / NTN / province / address,
      seller business name / NTN / province / address, status, environment
    - Item fields: item_name (resolved from saved products), hs_code,
      product_description, quantity, uom, rate, item_rate,
      value_sales_excluding_st, sales_tax_applicable,
      sales_tax_withheld_at_source, further_tax, extra_tax, fed_payable,
      discount, withholding_tax_amount, total_values, sale_type,
      income_tax_type

    Invoice rows with no items get a single row with invoice data and empty
    item columns (edge case: manual invoices require at least one item, but
    automation transfers might hit validation edge cases).
    """
    lookup = _build_item_name_lookup(saved_products)

    output = StringIO()
    writer = csv.writer(output)

    # CSV header
    writer.writerow([
        'Invoice Number',
        'FBR Reference Number',
        'Invoice Date',
        'Invoice Type',
        'Buyer Business Name',
        'Buyer NTN/CNIC',
        'Buyer Province',
        'Buyer Address',
        'Seller Business Name',
        'Seller NTN/CNIC',
        'Seller Province',
        'Seller Address',
        'Status',
        'Environment',
        'Item Name',
        'HS Code',
        'Product Description',
        'Quantity',
        'UOM',
        'Tax Rate',
        'Item Rate (Unit Price)',
        'Sales Value Excl. ST',
        'Sales Tax',
        'Sales Tax Withheld at Source',
        'Further Tax',
        'Extra Tax',
        'FED Payable',
        'Discount',
        'Withholding Tax',
        'Total Value Incl. Tax',
        'Sale Type',
        'Income Tax Type',
    ])

    for invoice in invoices:
        # Invoice-level fields (repeated for each item row)
        invoice_fields = [
            _clean_csv_value(invoice.external_id),
            _clean_csv_value(invoice.fbr_reference_number),
            _clean_csv_value(invoice.invoice_date),
            _clean_csv_value(invoice.invoice_type),
            _clean_csv_value(invoice.buyer_business_name),
            _clean_csv_value(invoice.buyer_ntn_cnic),
            _clean_csv_value(invoice.buyer_province),
            _clean_csv_value(invoice.buyer_address),
            _clean_csv_value(invoice.seller_business_name),
            _clean_csv_value(invoice.seller_ntn_cnic),
            _clean_csv_value(invoice.seller_province),
            _clean_csv_value(invoice.seller_address),
            _clean_csv_value(invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status)),
            _clean_csv_value(invoice.environment),
        ]

        items = invoice.items or []
        if not items:
            # Invoice with no items: write one row with invoice data and empty item columns
            writer.writerow(invoice_fields + [''] * 18)
            continue

        for item in items:
            description = (item.get('product_description') or '').strip()
            hs_code = (item.get('hs_code') or '').strip()
            item_name = _resolve_item_name(description, hs_code, lookup) if description else ''

            item_fields = [
                item_name,
                hs_code,
                description,
                _fmt_qty(item.get('quantity')),
                _clean_csv_value(item.get('uom')),
                _clean_csv_value(item.get('rate')),
                _fmt_amount(item.get('item_rate')),
                _fmt_amount(item.get('value_sales_excluding_st')),
                _fmt_amount(item.get('sales_tax_applicable')),
                _fmt_amount(item.get('sales_tax_withheld_at_source')),
                _fmt_amount(item.get('further_tax')),
                _fmt_amount(item.get('extra_tax')),
                _fmt_amount(item.get('fed_payable')),
                _fmt_amount(item.get('discount')),
                _fmt_amount(item.get('withholding_tax_amount')),
                _fmt_amount(item.get('total_values')),
                _clean_csv_value(item.get('sale_type')),
                _clean_csv_value(item.get('income_tax_type')),
            ]

            writer.writerow(invoice_fields + item_fields)

    return UTF8_BOM + output.getvalue()


def generate_income_tax_csv(
    invoices: List[Invoice],
    saved_products: Optional[List] = None,
) -> str:
    """
    Generate a line-item CSV of the income tax (236G / 236H) position.

    Columns: invoice number / date, buyer name / NTN-CNIC, item name and HS
    code, then the income tax columns the section is reported on — type, the
    rate applied as a percentage, the sales value excluding sales tax, and
    the withholding tax charged.

    Invoices with no line items produce no rows here (unlike the sales tax
    CSV, which emits an invoice-only row): a row with no item carries no
    income tax section and would only add noise.
    """
    lookup = _build_item_name_lookup(saved_products)

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Invoice Number',
        'Invoice Date',
        'Buyer Business Name',
        'Buyer NTN/CNIC',
        'Item Name',
        'HS Code',
        'Income Tax Type',
        'Rate %',
        'Sales Value Excl. ST',
        'Withholding Tax',
    ])

    for invoice in invoices:
        for item in invoice.items or []:
            description = (item.get('product_description') or '').strip()
            hs_code = (item.get('hs_code') or '').strip()
            item_name = _resolve_item_name(description, hs_code, lookup) if description else ''
            income_tax_type = _income_tax_type(invoice, item)

            writer.writerow([
                _clean_csv_value(invoice.external_id),
                _clean_csv_value(invoice.invoice_date),
                _clean_csv_value(invoice.buyer_business_name),
                _clean_csv_value(invoice.buyer_ntn_cnic),
                item_name,
                hs_code,
                income_tax_type,
                # Bare number, no "%" so Excel reads the cell as a value.
                f"{INCOME_TAX_RATES[income_tax_type] * 100:g}",
                _fmt_amount(item.get('value_sales_excluding_st')),
                _fmt_amount(item.get('withholding_tax_amount')),
            ])

    return UTF8_BOM + output.getvalue()
