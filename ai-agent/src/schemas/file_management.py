"""
File Management Schemas

Pydantic schemas for upload session management and invoice blocking/deletion operations.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class UploadSessionResponse(BaseModel):
    """Response schema for a single upload session"""

    id: str = Field(..., description="Upload session ID")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    total_count: int = Field(..., description="Total invoices in this session")
    pending_count: int = Field(0, description="Number of pending invoices")
    validated_count: int = Field(0, description="Number of validated invoices")
    transferred_count: int = Field(0, description="Number of transferred invoices")
    transfer_failed_count: int = Field(0, description="Number of transfer failed invoices")
    failed_count: int = Field(0, description="Number of failed invoices")
    blocked_count: int = Field(0, description="Number of blocked invoices")
    expired_count: int = Field(0, description="Number of expired invoices")
    can_delete: bool = Field(..., description="Whether this session can be deleted (no transferred invoices)")
    processing_status: str = Field(..., description="Current processing status: uploading, processing, completed, failed")
    processed_rows: int = Field(0, description="Number of rows processed so far")
    total_rows: int = Field(0, description="Total rows in the upload")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }


class UploadSessionListResponse(BaseModel):
    """Response schema for list of upload sessions"""

    sessions: List[UploadSessionResponse] = Field(..., description="List of upload sessions")
    total: int = Field(..., description="Total number of sessions")


class BlockInvoiceRequest(BaseModel):
    """Request schema for blocking/unblocking an invoice"""

    reason: Optional[str] = Field(None, description="Optional reason for blocking")


class BulkBlockRequest(BaseModel):
    """Request schema for bulk blocking invoices"""

    invoice_ids: List[str] = Field(..., description="List of invoice IDs to block", min_length=1)
    reason: Optional[str] = Field(None, description="Optional reason for blocking")


class BulkDeleteRequest(BaseModel):
    """Request schema for bulk deleting invoices"""

    invoice_ids: List[str] = Field(..., description="List of invoice IDs to delete", min_length=1)


class BulkRetryRequest(BaseModel):
    """Request schema for bulk retrying invoices"""

    invoice_ids: List[str] = Field(..., description="List of invoice IDs to retry", min_length=1)


class DeleteInvoiceResponse(BaseModel):
    """Response schema for invoice deletion"""

    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Success or error message")


class DeleteUploadSessionResponse(BaseModel):
    """Response schema for upload session deletion"""

    success: bool = Field(..., description="Whether deletion was successful")
    deleted_count: int = Field(..., description="Number of invoices deleted")
    message: str = Field(..., description="Success message")
