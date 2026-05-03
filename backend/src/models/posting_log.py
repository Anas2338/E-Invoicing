from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import Column, DateTime, String, JSON, ForeignKey
from sqlalchemy.types import Uuid


class PostingLog(SQLModel, table=True):
    """
    Audit log for all invoice posting attempts (auto and manual).

    Used for troubleshooting, analytics, and compliance.
    """
    __tablename__ = "posting_logs"

    # Primary key
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(Uuid, primary_key=True)
    )

    # Foreign keys
    user_id: uuid.UUID = Field(
        sa_column=Column(Uuid, ForeignKey('users.id'), nullable=False, index=True)
    )
    invoice_id: uuid.UUID = Field(
        sa_column=Column(Uuid, ForeignKey('invoices.id'), nullable=False, index=True)
    )

    # Log fields
    action: str = Field(
        sa_column=Column(String(20), nullable=False),
        description="'auto' or 'manual'"
    )
    result: str = Field(
        sa_column=Column(String(20), nullable=False),
        description="'success' or 'failure'"
    )
    environment: str = Field(
        sa_column=Column(String(20), nullable=False),
        description="'SANDBOX' or 'PRODUCTION'"
    )
    error_details: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Structured error information if failed"
    )
    agent_cycle_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50), nullable=True),
        description="Agent cycle identifier for auto posts"
    )

    # Timestamp
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, index=True)
    )
