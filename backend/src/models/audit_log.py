"""
Audit log model for tracking all FBR API interactions.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
from enum import Enum


class AuditAction(str, Enum):
    """Audit action types."""
    VALIDATE_INVOICE = "validate_invoice"
    POST_INVOICE = "post_invoice"
    BULK_POST_INVOICES = "bulk_post_invoices"
    VERIFY_BUYER = "verify_buyer"
    CREATE_INVOICE = "create_invoice"
    UPDATE_INVOICE = "update_invoice"
    DELETE_INVOICE = "delete_invoice"


class AuditLog(SQLModel, table=True):
    """
    Audit log for tracking all FBR API interactions and critical operations.

    Stores complete request/response data for compliance and troubleshooting.
    """
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)

    # User context
    user_id: str = Field(index=True, description="User who performed the action")

    # Action details
    action: str = Field(index=True, description="Action performed (e.g., validate_invoice, post_invoice)")
    resource_type: str = Field(description="Type of resource (e.g., invoice, user)")
    resource_id: Optional[str] = Field(default=None, index=True, description="ID of the resource")

    # Environment
    environment: str = Field(index=True, description="Environment (SANDBOX or PRODUCTION)")

    # Request/Response data
    request_payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON), description="Request payload sent to FBR")
    response_payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON), description="Response received from FBR")

    # HTTP details
    endpoint: Optional[str] = Field(default=None, description="FBR API endpoint called")
    method: Optional[str] = Field(default=None, description="HTTP method (GET, POST, etc.)")
    status_code: Optional[int] = Field(default=None, index=True, description="HTTP status code")

    # Timing
    duration_ms: Optional[int] = Field(default=None, description="Request duration in milliseconds")

    # Error tracking
    error_message: Optional[str] = Field(default=None, description="Error message if request failed")
    error_code: Optional[str] = Field(default=None, description="Error code if request failed")

    # Correlation
    correlation_id: Optional[str] = Field(default=None, index=True, description="Correlation ID for tracking related requests")

    # Metadata
    ip_address: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True, description="When the action was performed")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-123",
                "action": "validate_invoice",
                "resource_type": "invoice",
                "resource_id": "inv-456",
                "environment": "SANDBOX",
                "endpoint": "https://esp.fbr.gov.pk:8244/FBR/Production/di_data/v1/di/validateinvoicedata",
                "method": "POST",
                "status_code": 200,
                "duration_ms": 1250,
                "created_at": "2026-02-23T10:30:00Z"
            }
        }
