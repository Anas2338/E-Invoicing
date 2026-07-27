"""
Bulk operation model for tracking background validation/posting progress.

Represents a single bulk operation (validate or post) that processes
invoices one-by-one server-side. Rows are temporary — auto-cleaned
by the scheduler after 5 minutes post-completion.
"""
from typing import Optional, List
from datetime import datetime
import uuid
from enum import Enum
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import String, JSON, Integer, DateTime
from sqlalchemy.types import Uuid


class BulkOperationType(str, Enum):
    """Type of bulk operation."""
    BULK_VALIDATE = "bulk_validate"
    BULK_POST = "bulk_post"


class BulkOperationStatus(str, Enum):
    """Current state of a bulk operation task."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BulkOperationTask(SQLModel, table=True):
    """
    Tracks progress of a background bulk operation.
    """
    __tablename__ = "bulk_operation_task"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(Uuid, nullable=False, index=True)
    )
    operation_type: BulkOperationType = Field(
        sa_column=Column(String(20), nullable=False)
    )
    invoice_ids: List[str] = Field(
        sa_column=Column(JSON, nullable=False)
    )
    status: BulkOperationStatus = Field(
        sa_column=Column(
            String(20),
            nullable=False,
            default=BulkOperationStatus.PROCESSING
        )
    )
    total_count: int = Field(
        sa_column=Column(Integer, nullable=False)
    )
    processed_count: int = Field(
        sa_column=Column(Integer, nullable=False, default=0)
    )
    success_count: int = Field(
        sa_column=Column(Integer, nullable=False, default=0)
    )
    failure_count: int = Field(
        sa_column=Column(Integer, nullable=False, default=0)
    )
    errors: List[dict] = Field(
        sa_column=Column(JSON, default=[])
    )
    environment: Optional[str] = Field(
        sa_column=Column(String(10), nullable=True)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(
        sa_column=Column(DateTime, nullable=True)
    )
