"""
Audit log schemas for API requests and responses.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AuditLogListRequest(BaseModel):
    """Request schema for listing audit logs with filters."""
    environment: Optional[str] = Field(None, description="Filter by environment (SANDBOX or PRODUCTION)")
    action: Optional[str] = Field(None, description="Filter by action type")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    start_date: Optional[datetime] = Field(None, description="Start date for date range filter")
    end_date: Optional[datetime] = Field(None, description="End date for date range filter")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")


class AuditLogDetailResponse(BaseModel):
    """Detailed audit log response schema."""
    id: int = Field(..., description="Audit log ID")
    user_id: str = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource")
    resource_id: Optional[str] = Field(None, description="ID of the resource")
    environment: str = Field(..., description="Environment (SANDBOX or PRODUCTION)")
    request_payload: Optional[Dict[str, Any]] = Field(None, description="Request payload")
    response_payload: Optional[Dict[str, Any]] = Field(None, description="Response payload")
    endpoint: Optional[str] = Field(None, description="API endpoint called")
    method: Optional[str] = Field(None, description="HTTP method")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    duration_ms: Optional[int] = Field(None, description="Request duration in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    created_at: datetime = Field(..., description="When the action was performed")

    class Config:
        from_attributes = True


class AuditLogSummaryResponse(BaseModel):
    """Summary audit log response schema (for list view)."""
    id: int = Field(..., description="Audit log ID")
    user_id: str = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource")
    resource_id: Optional[str] = Field(None, description="ID of the resource")
    environment: str = Field(..., description="Environment (SANDBOX or PRODUCTION)")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    duration_ms: Optional[int] = Field(None, description="Request duration in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="When the action was performed")

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Response schema for audit log list with pagination."""
    audit_logs: List[AuditLogSummaryResponse] = Field(..., description="List of audit logs")
    total: int = Field(..., description="Total number of audit logs matching filters")
    limit: int = Field(..., description="Maximum number of results per page")
    offset: int = Field(..., description="Number of results skipped")
    has_more: bool = Field(..., description="Whether there are more results available")

    class Config:
        json_schema_extra = {
            "example": {
                "audit_logs": [
                    {
                        "id": 1,
                        "user_id": "user-123",
                        "action": "validate_invoice",
                        "resource_type": "invoice",
                        "resource_id": "inv-456",
                        "environment": "SANDBOX",
                        "status_code": 200,
                        "duration_ms": 1250,
                        "created_at": "2026-02-23T10:30:00Z"
                    }
                ],
                "total": 150,
                "limit": 100,
                "offset": 0,
                "has_more": True
            }
        }
