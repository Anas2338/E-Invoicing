"""
Schemas for invoice reports.

Defines the response contract for the invoice report endpoints:
- Summary: grand totals across the selected date range
- InvoiceRow: one row per invoice with its own totals
- InvoiceReportResponse: the full report (summary + rows)
"""
from pydantic import BaseModel
from typing import Optional, List
import uuid


class ReportSummary(BaseModel):
    """
    Grand totals for the selected date range.

    Every monetary field of an invoice line item is summed, so the report
    shows the full tax picture (sales tax, further tax, extra tax, FED,
    withholding, discounts).
    """
    total_invoices: int
    sales_value_excluding_st: float
    sales_tax: float
    sales_tax_withheld_at_source: float
    further_tax: float
    extra_tax: float
    fed_payable: float
    withholding_tax_amount: float
    discount: float
    value_including_tax: float


class ReportInvoiceRow(BaseModel):
    """
    One invoice row in the report, with per-invoice totals.
    """
    id: uuid.UUID
    invoice_number: str  # Invoice.external_id
    fbr_reference_number: Optional[str] = None
    invoice_date: str  # "YYYY-MM-DD"
    invoice_type: str
    buyer_business_name: str
    status: str  # InvoiceStatus value
    source: str  # "manual" | "automation"
    sales_value_excluding_st: float
    sales_tax: float
    further_tax: float
    value_including_tax: float


class InvoiceReportResponse(BaseModel):
    """
    Full invoice report for a date range.
    """
    date_from: str
    date_to: str
    summary: ReportSummary
    invoices: List[ReportInvoiceRow]


class ReportYearsResponse(BaseModel):
    """
    Distinct invoice years available for the report filter (newest first).
    """
    years: List[int]
