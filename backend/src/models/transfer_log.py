"""
TransferLog model for tracking invoice transfers from automation to main database.

This model stores audit trail of daily transfer operations.
"""

from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class TransferLog(SQLModel, table=True):
    """
    Audit log for invoice transfer operations.

    Tracks each transfer job execution with success/failure details.
    """
    __tablename__ = "transfer_log"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Transfer metadata
    transfer_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the transfer job started"
    )

    status: str = Field(
        description="Transfer status: success, partial_success, failed"
    )

    # Transfer statistics
    invoices_transferred: int = Field(
        default=0,
        description="Number of invoices successfully transferred"
    )

    invoices_failed: int = Field(
        default=0,
        description="Number of invoices that failed to transfer"
    )

    duration_seconds: float = Field(
        default=0.0,
        description="Duration of transfer job in seconds"
    )

    # Trigger information
    triggered_by: str = Field(
        default="scheduled",
        description="How transfer was triggered: scheduled or manual"
    )

    triggered_by_user_id: Optional[UUID] = Field(
        default=None,
        description="User ID if manually triggered, null for scheduled"
    )

    # Error details
    error_details: Optional[str] = Field(
        default=None,
        description="Error message if transfer failed"
    )

    # Failed invoice tracking
    failed_invoice_ids: Optional[str] = Field(
        default=None,
        description="JSON array of failed invoice UUIDs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "transfer_timestamp": "2026-04-24T19:00:00Z",
                "status": "partial_success",
                "invoices_transferred": 45,
                "invoices_failed": 2,
                "duration_seconds": 12.5,
                "triggered_by": "scheduled",
                "triggered_by_user_id": None,
                "error_details": None,
                "failed_invoice_ids": '["123e4567-e89b-12d3-a456-426614174000"]'
            }
        }
