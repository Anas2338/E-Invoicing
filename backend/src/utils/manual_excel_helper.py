"""
Manual Excel Helper - standalone functions for manual (non-automation) Excel operations.
Extracted from ExcelService to remove the automation DB dependency.
"""

from typing import Optional
from datetime import date, datetime
import pandas as pd
from io import BytesIO
from uuid import UUID
from sqlmodel import Session, select
import logging

from src.utils.excel_validator import ExcelValidator
from src.schemas.invoice import Environment


def _clean_ntn_cnic(value) -> str:
    """Normalize NTN/CNIC value from Excel cell.

    Returns empty string for blank cells and common placeholder values
    that Excel/pandas produce (e.g., 0, 0.0, nan). Handles float-to-int
    conversion for numeric cells (e.g., 1234567.0 → "1234567").
    """
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        if value == int(value):
            value = int(value)
    s = str(value).strip()
    if s in ("", "0", "0.0", "nan", "None", "none", "null", "N/A", "n/a", "-", "NA", "na", "Nil", "nil"):
        return ""
    if s.endswith(".0") and len(s) > 2:
        s = s[:-2]
    return s

logger = logging.getLogger(__name__)

MANUAL_TEMPLATE_COLUMNS = [
    "invoice_number",
    "invoice_type",
    "invoice_date",
    "buyer_ntn_cnic",
    "buyer_business_name",
    "buyer_province",
    "buyer_address",
    "buyer_registration_type",
    "saved_item_code",
    "quantity",
    "value_sales_excluding_st",
    "fixed_notified_value_or_retail_price",
    "further_tax",
    "discount",
    "income_tax",
    "status",
    "reason",
]


def generate_manual_excel_template() -> BytesIO:
    """Generate Excel template for manual invoice upload (no scheduled_date/scheduled_time)."""
    df = pd.DataFrame(columns=MANUAL_TEMPLATE_COLUMNS)

    sample_row = pd.DataFrame([{
        "invoice_number": "INV-001",
        "invoice_type": "Sale Invoice",
        "invoice_date": "2026-05-12",
        "buyer_ntn_cnic": "1234567",
        "buyer_business_name": "ABC Corporation",
        "buyer_province": "PUNJAB",
        "buyer_address": "123 Main Street, Lahore",
        "buyer_registration_type": "Registered",
        "saved_item_code": "ITEM001",
        "quantity": "2",
        "value_sales_excluding_st": "50000",
        "fixed_notified_value_or_retail_price": "0",
        "further_tax": "0",
        "discount": "0",
        "income_tax": "236G",
        "status": "",
        "reason": "",
    }])
    df = pd.concat([df, sample_row], ignore_index=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Invoices')

        workbook = writer.book
        worksheet = writer.sheets['Invoices']

        from openpyxl.utils import get_column_letter

        column_widths = [
            15, 15, 12, 15, 25, 15, 30, 20,
            20, 10, 20, 25, 12, 12, 12, 12, 30,
        ]

        for idx, width in enumerate(column_widths, start=1):
            col_letter = get_column_letter(idx)
            worksheet.column_dimensions[col_letter].width = width

    output.seek(0)
    return output


def parse_excel_for_manual_invoice(
    file_source: BytesIO | str,
    user_id: UUID = None,
    main_db: Session = None,
) -> list[dict]:
    """Parse Excel file for manual invoice creation.
    Validates invoice_date is today or previous date (no future dates).
    Does NOT include scheduling fields (automation-only).
    """
    from src.models.user import User
    from src.models.user_saved_product import UserSavedProduct
    from src.models.invoice import Invoice as InvoiceModel

    try:
        df = pd.read_excel(
            file_source,
            engine='openpyxl',
            dtype={'saved_item_code': str, 'income_tax': str},
        )
    except MemoryError:
        raise MemoryError(
            "File is too large to process in memory. "
            "Please reduce the file size or split into smaller batches (max 1,000 rows)."
        )

    df = df.dropna(subset=['invoice_number'])
    if not df.empty:
        df = df[df['invoice_number'].astype(str).str.strip() != 'INV-001']

    seller_info = {}
    if user_id and main_db:
        user = main_db.get(User, user_id)
        if user:
            seller_info = {
                "seller_ntn_cnic": user.fbr_seller_ntn or "",
                "seller_business_name": user.fbr_business_name or "",
                "seller_province": user.fbr_seller_province or "",
                "seller_address": user.fbr_seller_address or "",
            }

    saved_items_dict = {}
    if user_id and main_db:
        statement = select(UserSavedProduct).where(
            UserSavedProduct.user_id == user_id,
            UserSavedProduct.is_active == 1,
        )
        saved_items = main_db.exec(statement).all()
        saved_items_dict = {item.item_code: item for item in saved_items}

    excel_invoice_numbers = set()
    for _, row in df.iterrows():
        inv_num = str(row['invoice_number']).strip() if pd.notna(row['invoice_number']) else ""
        if inv_num and inv_num != 'INV-001':
            excel_invoice_numbers.add(inv_num)

    existing_invoice_numbers = set()
    if excel_invoice_numbers and main_db:
        existing = main_db.exec(
            select(InvoiceModel.external_id).where(
                InvoiceModel.external_id.in_(excel_invoice_numbers),
                InvoiceModel.is_deleted == False,
            )
        ).all()
        existing_invoice_numbers = set(existing)

    today = date.today()
    invoice_groups: dict[str, dict] = {}
    validation_errors = []

    for row_idx, row in df.iterrows():
        invoice_number = str(row['invoice_number']).strip()
        excel_row = row_idx + 2

        if invoice_number in existing_invoice_numbers:
            validation_errors.append(
                f"Row {excel_row} (Invoice {invoice_number}): "
                f"invoice number already exists in your history."
            )
            continue

        saved_item_code = str(row['saved_item_code']).strip() if pd.notna(row['saved_item_code']) else ""
        if not saved_item_code:
            validation_errors.append(f"Row {excel_row} (Invoice {invoice_number}): saved_item_code is required")
            continue

        saved_item = saved_items_dict.get(saved_item_code)
        if not saved_item:
            validation_errors.append(
                f"Row {excel_row} (Invoice {invoice_number}): "
                f"saved_item_code '{saved_item_code}' not found in your saved items"
            )
            continue

        invoice_date_str = ""
        if pd.notna(row['invoice_date']):
            try:
                invoice_date_parsed = pd.to_datetime(row['invoice_date'])
                invoice_date_str = invoice_date_parsed.strftime('%Y-%m-%d')
                invoice_date_obj = invoice_date_parsed.date()
                if invoice_date_obj > today:
                    validation_errors.append(
                        f"Row {excel_row} (Invoice {invoice_number}): "
                        f"invoice_date '{invoice_date_str}' is in the future."
                    )
                    continue
            except Exception:
                invoice_date_str = str(row['invoice_date']).strip()
        else:
            validation_errors.append(f"Row {excel_row} (Invoice {invoice_number}): invoice_date is required")
            continue

        income_tax = "236G"
        if pd.notna(row.get('income_tax')):
            income_tax_raw = str(row['income_tax']).strip()
            if income_tax_raw in ("236G", "236H"):
                income_tax = income_tax_raw
            elif income_tax_raw:
                validation_errors.append(
                    f"Row {excel_row} (Invoice {invoice_number}): "
                    f"income_tax '{income_tax_raw}' is invalid."
                )
                continue

        quantity = float(row['quantity']) if pd.notna(row['quantity']) else 0
        value_sales_excluding_st = float(row['value_sales_excluding_st']) if pd.notna(row['value_sales_excluding_st']) else 0
        fixed_notified_value_or_retail_price = float(row['fixed_notified_value_or_retail_price']) if pd.notna(row['fixed_notified_value_or_retail_price']) else 0
        further_tax = float(row['further_tax']) if pd.notna(row['further_tax']) else 0
        discount = float(row['discount']) if pd.notna(row.get('discount')) else 0

        tax_rate = float(saved_item.default_rate) if saved_item.default_rate else 18.0
        base_value = max(value_sales_excluding_st, fixed_notified_value_or_retail_price)
        sales_tax_applicable = (base_value * tax_rate) / 100
        total_values = base_value + sales_tax_applicable + further_tax - discount

        uom_code = saved_item.default_uom or "NOS"

        item = {
            "hs_code": saved_item.hs_code,
            "product_description": saved_item.product_description,
            "rate": str(saved_item.default_rate or "18"),
            "uom": uom_code,
            "quantity": quantity,
            "total_values": total_values,
            "value_sales_excluding_st": value_sales_excluding_st,
            "fixed_notified_value_or_retail_price": fixed_notified_value_or_retail_price,
            "sales_tax_applicable": sales_tax_applicable,
            "sales_tax_withheld_at_source": 0,
            "extra_tax": 0,
            "further_tax": further_tax,
            "sro_schedule_no": saved_item.sro_schedule_no or "",
            "fed_payable": 0,
            "discount": discount,
            "sale_type": saved_item.transaction_type or "01",
            "sro_item_serial_no": saved_item.sro_item_serial_no or "",
        }

        if invoice_number not in invoice_groups:
            invoice_groups[invoice_number] = {
                "external_id": invoice_number,
                "invoice_type": str(row['invoice_type']).strip() if pd.notna(row['invoice_type']) else "Sale Invoice",
                "invoice_date": invoice_date_str,
                "transaction_type_id": saved_item.transaction_type or "01",
                "seller_ntn_cnic": seller_info.get("seller_ntn_cnic", ""),
                "seller_business_name": seller_info.get("seller_business_name", ""),
                "seller_province": seller_info.get("seller_province", ""),
                "seller_address": seller_info.get("seller_address", ""),
                "buyer_ntn_cnic": _clean_ntn_cnic(row['buyer_ntn_cnic']),
                "buyer_business_name": str(row['buyer_business_name']).strip() if pd.notna(row['buyer_business_name']) else "",
                "buyer_province": str(row['buyer_province']).strip() if pd.notna(row['buyer_province']) else "",
                "buyer_address": str(row['buyer_address']).strip() if pd.notna(row['buyer_address']) else "",
                "buyer_registration_type": str(row['buyer_registration_type']).strip() if pd.notna(row['buyer_registration_type']) else "Registered",
                "invoice_ref_no": "",
                "scenario_id": "",
                "items": [],
                "environment": Environment.PRODUCTION,
                "income_tax": income_tax,
            }
        else:
            existing_date = invoice_groups[invoice_number]["invoice_date"]
            if invoice_date_str != existing_date:
                validation_errors.append(
                    f"Row {excel_row} (Invoice {invoice_number}): "
                    f"invoice_date '{invoice_date_str}' does not match row's date '{existing_date}'."
                )
                continue

        invoice_groups[invoice_number]["items"].append(item)

    if validation_errors:
        error_summary = f"Found {len(validation_errors)} validation error(s):\n" + "\n".join(validation_errors[:5])
        if len(validation_errors) > 5:
            error_summary += f"\n... and {len(validation_errors) - 5} more errors"
        raise ValueError(error_summary)

    return list(invoice_groups.values())
