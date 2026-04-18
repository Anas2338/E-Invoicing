from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from typing import Optional, TYPE_CHECKING
from datetime import datetime, date, time
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import Index

if TYPE_CHECKING:
    from .user import User
    from .excel_upload_session import ExcelUploadSession
    from .automation_log import AutomationLog


class AutomationInvoiceStatus(str, Enum):
    """Status enum for automation invoices."""
    PENDING = "pending"
    EXPIRED = "expired"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    FAILED = "failed"
    BLOCKED = "blocked"


class InvoiceSource(str, Enum):
    """Source of automated invoice."""
    EXCEL_UPLOAD = "excel_upload"
    API = "api"  # Future: API-based automation
    RECURRING = "recurring"  # Future: Recurring scheduled invoices


class AutomationInvoice(SQLModel, table=True):
    """
    Model for automated invoices from Excel upload.
    Tracks scheduling, processing status, and FBR submission results.
    """
    __tablename__ = "automation_invoice"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    user_id: UUID = Field(foreign_key="users.id", index=True)
    excel_upload_session_id: UUID = Field(
        foreign_key="excel_upload_session.id",
        index=True
    )

    # Invoice identification
    invoice_number: str = Field(max_length=100, index=True)

    # Invoice data (full invoice details from Excel as JSON)
    invoice_data: dict = Field(sa_column=Column(JSON))

    # Scheduling information
    scheduled_date: date = Field(index=True)
    scheduled_time: time = Field(index=True)

    # Processing status
    status: AutomationInvoiceStatus = Field(
        default=AutomationInvoiceStatus.PENDING,
        index=True
    )

    # Source of invoice (for tracking automation method)
    source: InvoiceSource = Field(
        default=InvoiceSource.EXCEL_UPLOAD,
        index=True
    )

    # Validation and submission results
    validation_errors: Optional[str] = Field(default=None, max_length=5000)
    fbr_response: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # AI Agent retry tracking
    retry_count: int = Field(default=0, ge=0)
    last_retry_at: Optional[datetime] = Field(default=None)
    priority: int = Field(default=5, ge=1, le=10)  # 1=highest, 10=lowest

    # Blocking reason (for blocked status)
    reason: Optional[str] = Field(default=None, max_length=1000)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="automation_invoices")
    excel_upload_session: Optional["ExcelUploadSession"] = Relationship(
        back_populates="automation_invoices"
    )
    automation_logs: list["AutomationLog"] = Relationship(
        back_populates="automation_invoice",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    __table_args__ = (
        # Unique constraint: one invoice number per user
        Index(
            "idx_unique_invoice_per_user",
            "user_id",
            "invoice_number",
            unique=True
        ),
        # Composite index for hourly worker query
        Index(
            "idx_pending_scheduled",
            "status",
            "scheduled_date",
            "scheduled_time"
        ),
        # AI Agent retry tracking index
        Index(
            "idx_retry_tracking",
            "status",
            "last_retry_at",
            "retry_count"
        ),
        # AI Agent priority processing index
        Index(
            "idx_priority_processing",
            "priority",
            "scheduled_date",
            "scheduled_time"
        ),
    )
