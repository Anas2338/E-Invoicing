"""
Dashboard API endpoints for automation monitoring.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, and_, or_, func
from datetime import date
import os

from src.database.session import get_db
from src.models.user import User
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus, InvoiceSource
from src.models.automation_log import AutomationLog
from src.models.excel_upload_session import ExcelUploadSession
from src.services.automation_service import AutomationService
from src.services.excel_service import ExcelService
from src.schemas.automation import (
    DashboardStatsResponse,
    InvoiceListResponse,
    InvoiceDetailResponse
)
from src.api.middleware.auth_middleware import require_authentication

router = APIRouter(prefix="/dashboard", tags=["automation-dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for authenticated user.

    Returns counts of invoices by status.
    """
    automation_service = AutomationService(db)
    stats = automation_service.get_dashboard_stats(UUID(user_id))

    return DashboardStatsResponse(**stats)


@router.get("/invoices", response_model=InvoiceListResponse)
async def get_invoice_list(
    request: Request,
    user_id: str = Depends(require_authentication),
    status: Optional[AutomationInvoiceStatus] = Query(None, description="Filter by status"),
    source: Optional[InvoiceSource] = Query(None, description="Filter by source"),
    date_from: Optional[date] = Query(None, description="Filter by scheduled date from"),
    date_to: Optional[date] = Query(None, description="Filter by scheduled date to"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of invoices for authenticated user with optional filters.

    Supports filtering by:
    - Status (pending, validated, submitted, failed, expired)
    - Source (excel_upload, api, recurring)
    - Date range (scheduled_date)

    Returns paginated results with total count.
    """
    # Build base filter conditions
    filters = [AutomationInvoice.user_id == UUID(user_id)]

    # Apply filters
    if status:
        filters.append(AutomationInvoice.status == status)

    if source:
        filters.append(AutomationInvoice.source == source)

    if date_from:
        filters.append(AutomationInvoice.scheduled_date >= date_from)

    if date_to:
        filters.append(AutomationInvoice.scheduled_date <= date_to)

    # Optimized count query - uses indexes directly without subquery
    count_query = select(func.count(AutomationInvoice.id)).where(and_(*filters))
    total = db.exec(count_query).one()

    # Build main query with same filters
    query = select(AutomationInvoice).where(and_(*filters))

    # Order by scheduled date and time (most recent first)
    # This uses the composite index idx_pending_scheduled when status filter is applied
    query = query.order_by(
        AutomationInvoice.scheduled_date.desc(),
        AutomationInvoice.scheduled_time.desc()
    )

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    invoices = db.exec(query).all()

    return InvoiceListResponse(
        invoices=invoices,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/invoice/{invoice_id}", response_model=InvoiceDetailResponse)
async def get_invoice_detail(
    invoice_id: UUID,
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific invoice.

    Includes:
    - Invoice data
    - Status and timestamps
    - Validation errors (if any)
    - FBR response (if submitted)
    - Activity logs

    Row-level security: Only returns invoice if it belongs to the requesting user.
    """
    # Get invoice with user_id check (row-level security)
    invoice = db.get(AutomationInvoice, invoice_id)

    if not invoice or str(invoice.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Get activity logs
    logs_query = select(AutomationLog).where(
        AutomationLog.automation_invoice_id == invoice_id
    ).order_by(AutomationLog.timestamp.desc())

    logs = db.exec(logs_query).all()

    return InvoiceDetailResponse(
        invoice=invoice,
        logs=logs
    )


@router.get("/download/{session_id}")
async def download_excel_file(
    session_id: UUID,
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Generate and download Excel file with invoice data from database.

    Returns Excel file with all invoices from the session, including their
    current status and processing results.

    Row-level security: Only returns data if session belongs to the requesting user.
    """
    # Get session with user_id check (row-level security)
    session = db.get(ExcelUploadSession, session_id)

    if not session or str(session.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Upload session not found")

    # Get all invoices for this session
    query = select(AutomationInvoice).where(
        AutomationInvoice.excel_upload_session_id == session_id
    ).order_by(AutomationInvoice.created_at)

    invoices = db.exec(query).all()

    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found for this session")

    # Generate Excel from database
    excel_service = ExcelService(db)
    excel_file = excel_service.generate_excel_from_database(invoices)

    # Return as streaming response
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={session.original_filename}"
        }
    )
