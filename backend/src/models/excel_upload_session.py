from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import Index

if TYPE_CHECKING:
    from .user import User
    from .automation_invoice import AutomationInvoice


class ExcelUploadProcessingStatus(str, Enum):
    """Processing status for Excel upload sessions."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExcelUploadSession(SQLModel, table=True):
    """
    Model for Excel upload sessions.
    Tracks file upload and processing status, prevents concurrent uploads.
    """
    __tablename__ = "excel_upload_session"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign key
    user_id: UUID = Field(foreign_key="users.id", index=True)

    # File information (optional for in-memory parsing)
    file_path: Optional[str] = Field(default=None, max_length=500)
    original_filename: str = Field(max_length=255)

    # Processing tracking
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    total_rows: int = Field(default=0)
    processed_rows: int = Field(default=0)
    processing_status: ExcelUploadProcessingStatus = Field(
        default=ExcelUploadProcessingStatus.UPLOADING,
        index=True
    )

    # Error tracking
    error_message: Optional[str] = Field(default=None, max_length=2000)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="excel_upload_sessions")
    automation_invoices: list["AutomationInvoice"] = Relationship(
        back_populates="excel_upload_session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    __table_args__ = (
        # Partial unique index: only one 'processing' session per user
        Index(
            "idx_one_processing_per_user",
            "user_id",
            unique=True,
            postgresql_where=(processing_status == ExcelUploadProcessingStatus.PROCESSING)
        ),
        # Composite index for user session queries
        Index(
            "idx_user_sessions",
            "user_id",
            "processing_status",
            "upload_timestamp"
        ),
    )
