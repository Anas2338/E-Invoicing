"""
Audit log API endpoints for retrieving audit trail.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..deps import get_db_session, get_current_user
from ...services.audit_service import AuditService
from ...schemas.audit import (
    AuditLogListRequest,
    AuditLogListResponse,
    AuditLogDetailResponse,
    AuditLogSummaryResponse
)
from ...schemas.auth import AuthUser

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    environment: Optional[str] = Query(None, description="Filter by environment (SANDBOX or PRODUCTION)"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    start_date: Optional[datetime] = Query(None, description="Start date for date range filter"),
    end_date: Optional[datetime] = Query(None, description="End date for date range filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    List audit logs with filtering and pagination.

    Returns audit logs for the authenticated user only (user isolation).

    **Query Parameters:**
    - **environment**: Filter by environment (SANDBOX or PRODUCTION)
    - **action**: Filter by action type (e.g., validate_invoice, post_invoice)
    - **resource_type**: Filter by resource type (e.g., invoice, user)
    - **resource_id**: Filter by specific resource ID
    - **start_date**: Start date for date range filter (ISO 8601 format)
    - **end_date**: End date for date range filter (ISO 8601 format)
    - **limit**: Maximum number of results (1-1000, default 100)
    - **offset**: Number of results to skip (for pagination)

    **Returns:**
    - List of audit logs matching the filters
    - Total count of matching logs
    - Pagination metadata
    """
    # Validate environment if provided
    if environment and environment.upper() not in ["SANDBOX", "PRODUCTION"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid environment. Must be SANDBOX or PRODUCTION."
        )

    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date"
        )

    # Get audit logs from service
    audit_logs, total = AuditService.list_audit_logs(
        db=db,
        user_id=current_user.user_id,
        environment=environment.upper() if environment else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )

    # Convert to summary response
    audit_log_summaries = [
        AuditLogSummaryResponse.model_validate(log)
        for log in audit_logs
    ]

    # Calculate has_more
    has_more = (offset + limit) < total

    return AuditLogListResponse(
        audit_logs=audit_log_summaries,
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more
    )


@router.get("/{audit_log_id}", response_model=AuditLogDetailResponse)
def get_audit_log(
    audit_log_id: int,
    db: Session = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Get detailed information about a specific audit log entry.

    **Path Parameters:**
    - **audit_log_id**: ID of the audit log entry

    **Returns:**
    - Detailed audit log information including full request/response payloads

    **Errors:**
    - 404: Audit log not found or user does not have access
    """
    audit_log = AuditService.get_audit_log_by_id(
        db=db,
        audit_log_id=audit_log_id,
        user_id=current_user.user_id
    )

    if not audit_log:
        raise HTTPException(
            status_code=404,
            detail=f"Audit log with ID {audit_log_id} not found"
        )

    return AuditLogDetailResponse.model_validate(audit_log)
