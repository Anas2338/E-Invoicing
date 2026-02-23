"""
Idempotency cache model for preventing duplicate invoice postings.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON


class IdempotencyCache(SQLModel, table=True):
    """
    Idempotency cache for storing results of invoice posting operations.

    Prevents duplicate postings by caching results for 24 hours.
    """
    __tablename__ = "idempotency_cache"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Idempotency key (unique per user)
    idempotency_key: str = Field(unique=True, index=True, description="Unique idempotency key")
    user_id: str = Field(index=True, description="User who initiated the request")

    # Request details
    invoice_id: str = Field(index=True, description="Invoice ID that was posted")
    environment: str = Field(description="Environment (SANDBOX or PRODUCTION)")

    # Cached response
    response_payload: Dict[str, Any] = Field(sa_column=Column(JSON), description="Cached response from FBR")
    status_code: int = Field(description="HTTP status code of the cached response")

    # Success/failure tracking
    success: bool = Field(description="Whether the posting was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if posting failed")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True, description="When the cache entry was created")
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=24),
        index=True,
        description="When the cache entry expires (24 hours from creation)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "idempotency_key": "user-123-inv-456-20260223103000",
                "user_id": "user-123",
                "invoice_id": "inv-456",
                "environment": "SANDBOX",
                "status_code": 200,
                "success": True,
                "created_at": "2026-02-23T10:30:00Z",
                "expires_at": "2026-02-24T10:30:00Z"
            }
        }
