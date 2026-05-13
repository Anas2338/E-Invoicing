from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import Index

from .automation_base import automation_metadata

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
    metadata = automation_metadata
    __tablename__ = "excel_upload_session"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # User reference (no FK - cross-database reference)
    user_id: UUID = Field(index=True)

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
    # Note: No relationship to User (cross-database reference)
    automation_invoices: list["AutomationInvoice"] = Relationship(
        back_populates="excel_upload_session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    __table_args__ = (
        # Composite index for user session queries
        Index(
            "idx_user_sessions",
            "user_id",
            "processing_status",
            "upload_timestamp"
        ),
    )
