from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, List
from datetime import datetime
import uuid
from enum import Enum
from sqlalchemy import Column, DateTime, String, JSON, Integer
from sqlalchemy.types import Uuid
from sqlalchemy import NUMERIC
from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .fbr_response import FBRResponse


class InvoiceType(str, Enum):
    """
    Enum for invoice types.
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
    TRANSFERRED = "TRANSFERRED"  # Validated and ready for FBR posting
    POSTED = "POSTED"
    FAILED = "FAILED"
    # Auto-posting statuses
    FBR_POSTING = "FBR_POSTING"  # Currently being posted to FBR
    FBR_POSTED = "FBR_POSTED"    # Successfully posted to FBR
    FBR_FAILED = "FBR_FAILED"    # Failed to post to FBR


class InvoiceItem(SQLModel):
    """
    Model for invoice items based on FBR technical specification.
    """
    hs_code: str
    product_description: str
    rate: str  # Tax rate as string (e.g., "18%")
    uom: str  # Unit of measurement
    quantity: float
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


class InvoiceBase(SQLModel):
    """
    Base fields for Invoice model.
    """
    external_id: str = Field(index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    # FBR-specific invoice fields based on technical specification
    invoice_type: str = Field(sa_column=Column(String, nullable=False))  # "Sale Invoice", "Debit Note", etc.
    invoice_date: str = Field(sa_column=Column(String, nullable=False))  # "YYYY-MM-DD" format
    transaction_type_id: Optional[str] = Field(default=None)  # Transaction type ID (e.g., "01", "02")
    seller_ntn_cnic: str = Field(sa_column=Column(String, nullable=False))  # 7 or 13 digits
    seller_business_name: str = Field(sa_column=Column(String, nullable=False))
    seller_province: str = Field(sa_column=Column(String, nullable=False))
    seller_address: str = Field(sa_column=Column(String, nullable=False))
    buyer_ntn_cnic: str = Field(sa_column=Column(String, nullable=False))  # 7 or 13 digits
    buyer_business_name: str = Field(sa_column=Column(String, nullable=False))
    buyer_province: str = Field(sa_column=Column(String, nullable=False))
    buyer_address: str = Field(sa_column=Column(String, nullable=False))
    buyer_registration_type: str = Field(sa_column=Column(String, nullable=False))  # "Registered", "Unregistered"
    invoice_ref_no: Optional[str] = Field(default=None)  # Required only for debit/credit notes
    scenario_id: Optional[str] = Field(default=None)  # Required for sandbox testing (e.g., "SN001")

    # Invoice items (stored as JSON to match FBR specification)
    items: List[dict] = Field(sa_column=Column(JSON, nullable=False))

    # Additional fields
    environment: Environment = Field(sa_column=Column(String, nullable=False))
    status: InvoiceStatus = Field(sa_column=Column(String, nullable=False), default=InvoiceStatus.DRAFT)
    validated_at: Optional[datetime] = Field(default=None)
    posted_at: Optional[datetime] = Field(default=None)
    fbr_reference_number: Optional[str] = Field(default=None)
    validation_errors: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    fbr_response_id: Optional[uuid.UUID] = Field(default=None, foreign_key="fbr_responses.id")

    # Transfer tracking (for automation database separation feature)
    source: str = Field(
        default="manual",
        sa_column=Column(String, nullable=False),
        description="Source of invoice: manual or automation"
    )
    transferred_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime),
        description="Timestamp when transferred from automation database"
    )
    automation_invoice_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(Uuid),
        description="Reference to original automation invoice if transferred"
    )

    # Soft delete field
    is_deleted: bool = Field(default=False, nullable=False)

    # Auto-posting FBR tracking fields
    fbr_posted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True),
        description="Timestamp when successfully posted to FBR"
    )
    fbr_posting_error: Optional[str] = Field(
        default=None,
        sa_column=Column(String(2000), nullable=True),
        description="Error message if posting failed"
    )
    fbr_retry_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
        description="Number of retry attempts for FBR posting"
    )


class Invoice(InvoiceBase, Base, table=True):
    """
    Invoice model representing a sale or purchase invoice.
    """
    __tablename__ = "invoices"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Additional fields for the table
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    user: "User" = Relationship(back_populates="invoices")
    fbr_response: Optional["FBRResponse"] = Relationship(back_populates="invoices")


# Model for creating new invoices
class InvoiceCreate(SQLModel):
    """
    Model for creating new invoices.
    """
    external_id: str
    # FBR-specific invoice fields based on technical specification
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

    # Invoice items (stored as JSON to match FBR specification)
    items: List[InvoiceItem]

    # Additional fields
    environment: Environment


# Model for updating invoices
class InvoiceUpdate(SQLModel):
    """
    Model for updating invoices.
    """
    # Invoice data fields (all optional for partial updates)
    external_id: Optional[str] = None
    invoice_type: Optional[str] = None
    invoice_date: Optional[str] = None
    transaction_type_id: Optional[str] = None
    seller_ntn_cnic: Optional[str] = None
    seller_business_name: Optional[str] = None
    seller_province: Optional[str] = None
    seller_address: Optional[str] = None
    buyer_ntn_cnic: Optional[str] = None
    buyer_business_name: Optional[str] = None
    buyer_province: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_registration_type: Optional[str] = None
    invoice_ref_no: Optional[str] = None
    scenario_id: Optional[str] = None
    items: Optional[List[dict]] = None
    environment: Optional[Environment] = None

    # Status fields
    status: Optional[InvoiceStatus] = None
    validated_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    fbr_reference_number: Optional[str] = None
    validation_errors: Optional[dict] = None


# Model for invoice responses
class InvoiceRead(InvoiceBase):
    """
    Model for returning invoice data.
    """
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    user: Optional["User"] = None
    fbr_response: Optional["FBRResponse"] = None