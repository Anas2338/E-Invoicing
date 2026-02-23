"""
Base error response schemas for consistent API error handling.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: Optional[str] = Field(None, description="Field name that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code for programmatic handling")


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class ValidationErrorResponse(BaseModel):
    """Validation error response with field-level details."""
    error: str = Field(default="validation_error", description="Error type")
    message: str = Field(..., description="Human-readable error message")
    validation_errors: List[ErrorDetail] = Field(..., description="List of validation errors")


class FBRErrorResponse(BaseModel):
    """FBR API error response."""
    error: str = Field(default="fbr_error", description="Error type")
    message: str = Field(..., description="Human-readable error message")
    fbr_code: Optional[str] = Field(None, description="FBR error code")
    fbr_message: Optional[str] = Field(None, description="Original FBR error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details from FBR")


class DatabaseErrorResponse(BaseModel):
    """Database error response."""
    error: str = Field(default="database_error", description="Error type")
    message: str = Field(..., description="Human-readable error message")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")


class AuthenticationErrorResponse(BaseModel):
    """Authentication error response."""
    error: str = Field(default="authentication_error", description="Error type")
    message: str = Field(..., description="Human-readable error message")
    www_authenticate: Optional[str] = Field(None, description="WWW-Authenticate header value")


class AuthorizationErrorResponse(BaseModel):
    """Authorization error response."""
    error: str = Field(default="authorization_error", description="Error type")
    message: str = Field(..., description="Human-readable error message")
    required_permission: Optional[str] = Field(None, description="Required permission")


class NotFoundErrorResponse(BaseModel):
    """Resource not found error response."""
    error: str = Field(default="not_found", description="Error type")
    message: str = Field(..., description="Human-readable error message")
    resource_type: Optional[str] = Field(None, description="Type of resource not found")
    resource_id: Optional[str] = Field(None, description="ID of resource not found")


class ConflictErrorResponse(BaseModel):
    """Conflict error response (e.g., optimistic locking failure)."""
    error: str = Field(default="conflict", description="Error type")
    message: str = Field(..., description="Human-readable error message")
    conflict_type: Optional[str] = Field(None, description="Type of conflict")


class RateLimitErrorResponse(BaseModel):
    """Rate limit exceeded error response."""
    error: str = Field(default="rate_limit_exceeded", description="Error type")
    message: str = Field(..., description="Human-readable error message")
    retry_after: int = Field(..., description="Seconds to wait before retrying")
    limit: Optional[int] = Field(None, description="Rate limit threshold")
