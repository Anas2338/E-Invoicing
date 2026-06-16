from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
from enum import Enum
from .fbr import FBRValidationResponse


class InvoiceType(str, Enum):
    """
    Enum for invoice types based on FBR specification.
    """
    SALE_INVOICE = "Sale Invoice"
    DEBIT_NOTE = "Debit Note"
    CREDIT_NOTE = "Credit Note"


class Environment(str, Enum):
    """
    Enum for environments.
    """
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


class InvoiceStatus(str, Enum):
    """
    Enum for invoice statuses.
    """
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    POSTED = "POSTED"
    FAILED = "FAILED"


class InvoiceItem(BaseModel):
    """
    Schema for invoice items based on FBR technical specification.
    """
    hs_code: str
    product_description: str
    rate: str  # Tax rate as string (e.g., "18%")
    uom: str  # Unit of measurement
    quantity: float
    item_rate: Optional[float] = None  # Unit price = value_sales_excluding_st / quantity
    total_values: float
    value_sales_excluding_st: float
    fixed_notified_value_or_retail_price: float
    sales_tax_applicable: float
    sales_tax_withheld_at_source: float
    extra_tax: float
    further_tax: float
    sro_schedule_no: Optional[str] = None
    fed_payable: float
    discount: float
    sale_type: str = "Goods at standard rate (default)"
    sro_item_serial_no: Optional[str] = None
    # Internal fields (not sent to FBR)
    income_tax_type: Optional[str] = "236G"  # Income tax type per item: "236G" or "236H"
    withholding_tax_amount: float = 0  # Calculated withholding tax amount


class InvoiceBase(BaseModel):
    """
    Base schema for invoice based on FBR technical specification.
    """
    external_id: str
    invoice_type: str  # "Sale Invoice", "Debit Note", etc.
    invoice_date: str  # "YYYY-MM-DD" format
    transaction_type_id: Optional[str] = None  # Transaction type ID (e.g., "01", "02")
    seller_ntn_cnic: str  # 7 or 13 digits
    seller_business_name: str
    seller_province: str
    seller_address: str
    buyer_ntn_cnic: str  # 7 or 13 digits
    buyer_business_name: str
    buyer_province: str
    buyer_address: str
    buyer_registration_type: str  # "Registered", "Unregistered"
    invoice_ref_no: Optional[str] = None  # Required only for debit/credit notes
    scenario_id: Optional[str] = None  # Required for sandbox testing (e.g., "SN001")

    # Invoice items
    items: List[InvoiceItem]

    environment: Environment


class InvoiceCreate(BaseModel):
    """
    Schema for creating invoices.
    external_id is optional - will be auto-generated if not provided.
    """
    external_id: Optional[str] = None
    invoice_type: str  # "Sale Invoice", "Debit Note", etc.
    invoice_date: str  # "YYYY-MM-DD" format
    transaction_type_id: Optional[str] = None  # Transaction type ID (e.g., "01", "02")
    seller_ntn_cnic: str  # 7 or 13 digits
    seller_business_name: str
    seller_province: str
    seller_address: str
    buyer_ntn_cnic: str  # 7 or 13 digits
    buyer_business_name: str
    buyer_province: str
    buyer_address: str
    buyer_registration_type: str  # "Registered", "Unregistered"
    invoice_ref_no: Optional[str] = None  # Required only for debit/credit notes
    scenario_id: Optional[str] = None  # Required for sandbox testing (e.g., "SN001")
    items: List[InvoiceItem]
    environment: Environment
    income_tax: Optional[str] = "236G"  # Income tax type: "236G" or "236H"


class InvoiceUpdate(BaseModel):
    """
    Schema for updating invoices.
    """
    status: Optional[InvoiceStatus] = None
    validated_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    fbr_reference_number: Optional[str] = None
    validation_errors: Optional[dict] = None


class InvoiceResponse(InvoiceBase):
    """
    Schema for invoice response.

    Automation source is hidden — all invoices appear as manual.
    """
    id: uuid.UUID
    user_id: uuid.UUID
    status: InvoiceStatus
    created_at: datetime
    updated_at: datetime
    validated_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    fbr_reference_number: Optional[str] = None
    validation_errors: Optional[dict] = None
    fbr_response: Optional[FBRValidationResponse] = None

    # Source is always "manual" externally (automation origin is hidden)
    source: str = "manual"
    transferred_at: Optional[datetime] = None
    automation_invoice_id: Optional[uuid.UUID] = None


class InvoiceListResponse(BaseModel):
    """
    Schema for invoice list response with pagination.
    """
    data: List[InvoiceResponse]
    total: int
    page: int
    size: int
    total_pages: int


class InvoiceFilter(BaseModel):
    """
    Schema for invoice filtering parameters.
    """
    status: Optional[InvoiceStatus] = None
    invoice_type: Optional[InvoiceType] = None
    environment: Optional[Environment] = None
    source: Optional[str] = None  # Filter by source: "manual" or "automation"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    size: int = 20


class UnifiedInvoiceItem(BaseModel):
    """
    Schema for unified invoice item (manual + automated).
    """
    id: uuid.UUID
    source: str  # "manual" or "automated"
    invoice_number: str
    invoice_type: str
    invoice_date: str
    buyer_business_name: str
    seller_business_name: str
    total_amount: float
    status: str
    created_at: datetime

    # Optional fields specific to source
    scheduled_date: Optional[str] = None  # automated only
    scheduled_time: Optional[str] = None  # automated only
    environment: Optional[str] = None  # both
    fbr_reference_number: Optional[str] = None  # FBR reference number after posting
    income_tax: Optional[str] = None  # income tax type


class UnifiedInvoiceListResponse(BaseModel):
    """
    Schema for unified invoice list response with pagination.
    """
    invoices: List[UnifiedInvoiceItem]
    total: int
    page: int
    page_size: int
    total_pages: int