"""
Pydantic schemas for Excel upload feature.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class ExcelUploadProcessingStatus(str, Enum):
    """Processing status for Excel upload sessions."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExcelUploadSessionCreate(BaseModel):
    """Schema for creating Excel upload session."""
    user_id: UUID
    file_path: str
    original_filename: str
    total_rows: int = 0


class ExcelUploadSessionRead(BaseModel):
    """Schema for reading Excel upload session."""
    id: UUID
    user_id: UUID
    file_path: str
    original_filename: str
    upload_timestamp: datetime
    total_rows: int
    processed_rows: int
    processing_status: ExcelUploadProcessingStatus
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ExcelUploadSessionUpdate(BaseModel):
    """Schema for updating Excel upload session."""
    total_rows: Optional[int] = None
    processed_rows: Optional[int] = None
    processing_status: Optional[ExcelUploadProcessingStatus] = None
    error_message: Optional[str] = None


class ExcelUploadResponse(BaseModel):
    """Schema for Excel upload response."""
    session_id: UUID
    total_rows: int
    message: str


class ExcelUploadStatusResponse(BaseModel):
    """Schema for Excel upload status response with detailed validation statistics."""
    session_id: UUID
    status: ExcelUploadProcessingStatus
    processed_rows: int
    total_rows: int
    error_message: Optional[str] = None
    # Validation statistics
    validated_count: Optional[int] = 0
    failed_count: Optional[int] = 0
    expired_count: Optional[int] = 0
    pending_count: Optional[int] = 0
    progress_percentage: Optional[float] = 0.0


class ExcelValidationError(BaseModel):
    """Schema for Excel validation error."""
    row: Optional[int] = None
    column: Optional[str] = None
    error: str


class ExcelValidationResult(BaseModel):
    """Schema for Excel validation result."""
    valid: bool
    errors: list[ExcelValidationError] = []
    total_rows: int = 0
