"""
Pydantic schemas for bulk invoice operations (validate/post).

These are separate from the SQLModel to keep API contracts clean
and independent of the database model.
"""
from typing import Optional, List
from datetime import datetime
import uuid
from pydantic import BaseModel


class BulkValidateRequest(BaseModel):
    """Request body for starting a background bulk validation."""
    invoice_ids: List[uuid.UUID]


class BulkPostRequest(BaseModel):
    """Request body for starting a background bulk posting."""
    invoice_ids: List[uuid.UUID]
    environment: str


class BulkOperationResponse(BaseModel):
    """Response returned immediately after starting a bulk operation."""
    task_id: uuid.UUID
    message: str


class BulkOperationError(BaseModel):
    """Per-invoice error details within a bulk operation."""
    invoice_id: str
    invoice_number: str
    error: str


class BulkOperationStatusResponse(BaseModel):
    """Full status of a bulk operation, returned when polling."""
    task_id: uuid.UUID
    operation_type: str
    status: str
    total_count: int
    processed_count: int
    success_count: int
    failure_count: int
    errors: List[BulkOperationError]
    progress_percentage: float
    created_at: datetime
    completed_at: Optional[datetime] = None


class ActiveBulkTasksResponse(BaseModel):
    """Response containing all active bulk tasks for a user."""
    tasks: List[BulkOperationStatusResponse]


class BulkDeleteRequest(BaseModel):
    """Request body for bulk deleting invoices."""
    invoice_ids: List[uuid.UUID]


class BulkDeleteResponse(BaseModel):
    """Response from a bulk delete operation."""
    deleted_count: int
    not_found_ids: List[str] = []
    failed: List[dict] = []
