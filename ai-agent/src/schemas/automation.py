"""
Pydantic schemas for automation feature.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, time
from uuid import UUID
from enum import Enum


class AutomationInvoiceStatus(str, Enum):
    """Status enum for automation invoices."""
    PENDING = "pending"
    EXPIRED = "expired"
    VALIDATED = "validated"
    SUBMITTED = "submitted"  # Deprecated - kept for backward compatibility
    TRANSFERRED = "transferred"
    TRANSFER_FAILED = "transfer_failed"
    FAILED = "failed"
    BLOCKED = "blocked"
    PAUSED = "paused"


class InvoiceSource(str, Enum):
    """Source of automated invoice."""
    EXCEL_UPLOAD = "excel_upload"
    API = "api"
    RECURRING = "recurring"


class AutomationInvoiceBase(BaseModel):
    """Base schema for automation invoice."""
    invoice_number: str = Field(..., max_length=100)
    invoice_data: dict
    scheduled_date: date
    scheduled_time: time


class AutomationInvoiceCreate(AutomationInvoiceBase):
    """Schema for creating automation invoice."""
    user_id: UUID
    excel_upload_session_id: UUID


class AutomationInvoiceRead(AutomationInvoiceBase):
    """Schema for reading automation invoice."""
    id: UUID
    user_id: UUID
    excel_upload_session_id: UUID
    status: AutomationInvoiceStatus
    source: InvoiceSource
    validation_errors: Optional[str] = None
    fbr_response: Optional[dict] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AutomationInvoiceUpdate(BaseModel):
    """Schema for updating automation invoice."""
    status: Optional[AutomationInvoiceStatus] = None
    validation_errors: Optional[str] = None
    fbr_response: Optional[dict] = None
    processed_at: Optional[datetime] = None


class DashboardStatsResponse(BaseModel):
    """Schema for dashboard statistics response."""
    total_invoices: int
    pending_count: int
    expired_count: int
    validated_count: int
    paused_count: int
    transferred_count: int
    transfer_failed_count: int
    failed_count: int
    blocked_count: int


class InvoiceListRequest(BaseModel):
    """Schema for invoice list request with filters."""
    status: Optional[AutomationInvoiceStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class InvoiceListResponse(BaseModel):
    """Schema for paginated invoice list response."""
    invoices: list[AutomationInvoiceRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class InvoiceRetryResponse(BaseModel):
    """Schema for invoice retry response."""
    message: str
    invoice_id: UUID
    status: AutomationInvoiceStatus
    result: Optional[dict] = None


class AutomationLogAction(str, Enum):
    """Action types for automation logs."""
    VALIDATE = "validate"
    SUBMIT = "submit"
    UPDATE_EXCEL = "update_excel"
    RETRY = "retry"


class AutomationLogStatus(str, Enum):
    """Status for automation log entries."""
    SUCCESS = "success"
    FAILURE = "failure"


class AutomationLogCreate(BaseModel):
    """Schema for creating automation log."""
    automation_invoice_id: UUID
    action: AutomationLogAction
    status: AutomationLogStatus
    details: dict


class AutomationLogRead(BaseModel):
    """Schema for reading automation log."""
    id: UUID
    automation_invoice_id: UUID
    action: AutomationLogAction
    status: AutomationLogStatus
    details: dict
    timestamp: datetime

    class Config:
        from_attributes = True


class InvoiceDetailResponse(BaseModel):
    """Schema for invoice detail response with logs."""
    invoice: AutomationInvoiceRead
    logs: list[AutomationLogRead]


class InvoiceIdsResponse(BaseModel):
    """Schema for all invoice IDs matching filters (no pagination)."""
    invoice_ids: list[UUID]
    total: int


class BatchPdfRequest(BaseModel):
    """Schema for batch PDF generation request."""
    invoice_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of invoice IDs to include in batch PDF (1-50 invoices)"
    )
