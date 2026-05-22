from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum


class FBRValidationRequest(BaseModel):
    """
    Schema for FBR validation request.
    """
    invoice_id: uuid.UUID


class FBRValidationResponse(BaseModel):
    """
    Schema for FBR validation response.
    """
    invoice_id: uuid.UUID
    status: str  # 'validated' or 'failed'
    validation_result: Dict[str, Any]
    fbr_reference_number: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    fbr_request_payload: Optional[Dict[str, Any]] = None


class FBRPostingRequest(BaseModel):
    """
    Schema for FBR posting request.
    """
    invoice_id: uuid.UUID


class FBRPostingResponse(BaseModel):
    """
    Schema for FBR posting response.
    """
    invoice_id: uuid.UUID
    status: str  # 'posted' or 'failed'
    fbr_reference_number: Optional[str] = None
    fbr_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class FBREnvironment(str, Enum):
    """
    Enum for FBR environments.
    """
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


class BulkPostingRequest(BaseModel):
    """
    Schema for bulk FBR posting request.
    """
    invoice_ids: List[uuid.UUID]
    environment: FBREnvironment


class BulkPostingResult(BaseModel):
    """
    Schema for individual result in bulk posting response.
    """
    invoice_id: uuid.UUID
    status: str  # 'posted' or 'failed'
    fbr_reference_number: Optional[str] = None
    error: Optional[str] = None


class BulkPostingResponse(BaseModel):
    """
    Schema for bulk FBR posting response.
    """
    request_id: uuid.UUID
    total_count: int
    successful_count: int
    failed_count: int
    results: List[BulkPostingResult]


class FBRResponseSchema(BaseModel):
    """
    Schema for FBR API response data.
    """
    request_payload: Dict[str, Any]
    response_payload: Dict[str, Any]
    endpoint: str
    status_code: int
    timestamp: datetime
    processing_duration_ms: Optional[int] = None