"""
Pydantic schemas for the Excel staging API.

Request/response models for all 7 staging endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Row schema
# ---------------------------------------------------------------------------


class StagingRowResponse(BaseModel):
    """Response model for a single staging row."""
    id: UUID
    excel_row_number: int
    group_key: str
    is_valid: bool
    is_dirty: bool
    field_errors: dict = Field(default_factory=dict)

    # 16 template columns
    invoice_number: str
    invoice_type: str
    invoice_date: str
    buyer_ntn_cnic: str = ""
    buyer_business_name: str
    buyer_province: str
    buyer_address: str
    buyer_registration_type: str = "Registered"
    saved_item_code: str
    quantity: float = 0.0
    value_sales_excluding_st: float = 0.0
    fixed_notified_value_or_retail_price: float = 0.0
    further_tax: float = 0.0
    discount: float = 0.0
    income_tax: str = "236G"
    withholding_tax_amount: Optional[float] = None

    # Computed fields
    product_description: Optional[str] = None
    hs_code: Optional[str] = None
    rate: Optional[str] = None
    uom: Optional[str] = None
    sale_type: Optional[str] = None
    transaction_type_id: Optional[str] = None
    total_values: Optional[float] = None
    sales_tax_applicable: Optional[float] = None
    sales_tax_withheld_at_source: float = 0.0
    extra_tax: float = 0.0
    fed_payable: float = 0.0
    sro_schedule_no: Optional[str] = None
    sro_item_serial_no: Optional[str] = None
    item_rate: Optional[float] = None

    # Seller fields
    seller_ntn_cnic: str = ""
    seller_business_name: str = ""
    seller_province: str = ""
    seller_address: str = ""

    model_config = {"from_attributes": True}


class StagingRowUpdateRequest(BaseModel):
    """Request model for updating a row — all fields optional."""
    invoice_number: Optional[str] = None
    invoice_type: Optional[str] = None
    invoice_date: Optional[str] = None
    buyer_ntn_cnic: Optional[str] = None
    buyer_business_name: Optional[str] = None
    buyer_province: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_registration_type: Optional[str] = None
    saved_item_code: Optional[str] = None
    product_description: Optional[str] = None
    quantity: Optional[float] = None
    value_sales_excluding_st: Optional[float] = None
    fixed_notified_value_or_retail_price: Optional[float] = None
    further_tax: Optional[float] = None
    discount: Optional[float] = None
    income_tax: Optional[str] = None
    withholding_tax_amount: Optional[float] = None


# ---------------------------------------------------------------------------
# Session schemas
# ---------------------------------------------------------------------------


class StagingSessionResponse(BaseModel):
    """Response model for a staging session (without rows)."""
    session_id: UUID = Field(alias="session_id")
    status: str
    original_filename: str
    total_rows: int
    valid_rows: int
    errored_rows: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

    @classmethod
    def from_orm(cls, session):
        return cls(
            session_id=session.id,
            status=session.status.value if hasattr(session.status, 'value') else session.status,
            original_filename=session.original_filename,
            total_rows=session.total_rows,
            valid_rows=session.valid_rows,
            errored_rows=session.errored_rows,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


class StagingSessionDetailResponse(BaseModel):
    """Response model for a staging session with all rows."""
    session_id: UUID = Field(alias="session_id")
    status: str
    original_filename: str
    total_rows: int
    valid_rows: int
    errored_rows: int
    created_at: datetime
    updated_at: datetime
    rows: list[StagingRowResponse]

    model_config = {"from_attributes": True, "populate_by_name": True}

    @classmethod
    def from_orm(cls, session, rows):
        return cls(
            session_id=session.id,
            status=session.status.value if hasattr(session.status, 'value') else session.status,
            original_filename=session.original_filename,
            total_rows=session.total_rows,
            valid_rows=session.valid_rows,
            errored_rows=session.errored_rows,
            created_at=session.created_at,
            updated_at=session.updated_at,
            rows=[StagingRowResponse.model_validate(r) for r in rows],
        )


class StagingActiveSessionsResponse(BaseModel):
    """Response model for active sessions query."""
    sessions: list[StagingSessionResponse]


class StagingUploadResponse(BaseModel):
    """Response model for successful upload."""
    session_id: UUID
    status: str
    original_filename: str
    total_rows: int
    valid_rows: int
    errored_rows: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Action response schemas
# ---------------------------------------------------------------------------


class StagingRecheckResponse(BaseModel):
    """Response model for recheck action."""
    session_id: UUID
    errored_rows_before: int
    errored_rows_after: int
    all_clear: bool
    rows: list[StagingRowResponse]


class StagingCommitInvoiceInfo(BaseModel):
    """An invoice created during commit."""
    id: UUID
    external_id: str
    invoice_type: str
    status: str


class StagingCommitError(BaseModel):
    """An invoice that failed during commit."""
    invoice_number: str
    error: str


class StagingCommitResponse(BaseModel):
    """Response model for commit action."""
    session_id: UUID
    total_committed: int
    total_failed: int
    invoices: list[StagingCommitInvoiceInfo] = Field(default_factory=list)
    errors: list[StagingCommitError] = Field(default_factory=list)


class StagingCancelResponse(BaseModel):
    """Response model for cancel action."""
    message: str = "Upload cancelled. Staging session deleted."
