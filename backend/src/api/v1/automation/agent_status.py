"""
AI Agent status API endpoints.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select, func
from datetime import datetime

from src.database.session import get_db
from src.models.ai_agent_health_check import AIAgentHealthCheck
from src.models.automation_log import AutomationLog
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.schemas.agent import (
    AIAgentHealthCheckResponse,
    AIAgentDecisionListResponse,
    AIAgentDecisionLog,
    AIAgentStatusSummary
)
from src.api.middleware.auth_middleware import require_authentication

router = APIRouter(prefix="/agent", tags=["ai-agent-status"])


@router.get("/health", response_model=AIAgentHealthCheckResponse)
async def get_agent_health(
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Get latest AI Agent health check result.

    Returns the most recent health check with all metrics and anomalies.

    Requires authentication.
    """
    # Get latest health check
    query = select(AIAgentHealthCheck).order_by(
        AIAgentHealthCheck.check_timestamp.desc()
    ).limit(1)

    health_check = db.exec(query).first()

    if not health_check:
        raise HTTPException(
            status_code=404,
            detail="No health check data available yet"
        )

    return AIAgentHealthCheckResponse.model_validate(health_check)


@router.get("/decisions", response_model=AIAgentDecisionListResponse)
async def get_agent_decisions(
    request: Request,
    user_id: str = Depends(require_authentication),
    invoice_id: Optional[UUID] = Query(None, description="Filter by invoice ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of AI Agent decision logs.

    Returns decision logs with optional filters for invoice, action, and status.

    Requires authentication.
    """
    # Build base query
    query = select(AutomationLog)

    # Apply filters
    if invoice_id:
        query = query.where(AutomationLog.automation_invoice_id == invoice_id)

    if action:
        query = query.where(AutomationLog.action == action)

    if status:
        query = query.where(AutomationLog.status == status)

    # Count total
    count_query = select(func.count(AutomationLog.id))
    if invoice_id:
        count_query = count_query.where(AutomationLog.automation_invoice_id == invoice_id)
    if action:
        count_query = count_query.where(AutomationLog.action == action)
    if status:
        count_query = count_query.where(AutomationLog.status == status)

    total = db.exec(count_query).one()

    # Order by timestamp (most recent first)
    query = query.order_by(AutomationLog.timestamp.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    decisions = db.exec(query).all()

    # Convert to response models
    decision_logs = [
        AIAgentDecisionLog.model_validate(decision)
        for decision in decisions
    ]

    return AIAgentDecisionListResponse(
        decisions=decision_logs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/status", response_model=AIAgentStatusSummary)
async def get_agent_status_summary(
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Get AI Agent status summary.

    Returns a quick overview of agent status including latest health check
    and current invoice counts.

    Requires authentication.
    """
    # Get latest health check
    latest_health_check = db.exec(
        select(AIAgentHealthCheck).order_by(
            AIAgentHealthCheck.check_timestamp.desc()
        ).limit(1)
    ).first()

    # Get current invoice counts
    pending_count = db.exec(
        select(func.count(AutomationInvoice.id)).where(
            AutomationInvoice.status == AutomationInvoiceStatus.PENDING
        )
    ).one() or 0

    failed_count = db.exec(
        select(func.count(AutomationInvoice.id)).where(
            AutomationInvoice.status == AutomationInvoiceStatus.FAILED
        )
    ).one() or 0

    # Calculate backlog
    now = datetime.utcnow()
    backlog_count = db.exec(
        select(func.count(AutomationInvoice.id)).where(
            AutomationInvoice.status == AutomationInvoiceStatus.PENDING,
            AutomationInvoice.scheduled_date < now.date()
        )
    ).one() or 0

    if latest_health_check:
        return AIAgentStatusSummary(
            is_running=True,  # If health check exists, agent is running
            last_health_check=latest_health_check.check_timestamp,
            overall_status=latest_health_check.overall_status,
            pending_invoices=pending_count,
            failed_invoices=failed_count,
            processing_backlog=backlog_count,
            anomalies_count=len(latest_health_check.anomalies_detected),
            agent_version=latest_health_check.agent_version,
            agent_uptime_seconds=latest_health_check.agent_uptime_seconds
        )
    else:
        return AIAgentStatusSummary(
            is_running=False,
            last_health_check=None,
            overall_status=None,
            pending_invoices=pending_count,
            failed_invoices=failed_count,
            processing_backlog=backlog_count,
            anomalies_count=0,
            agent_version="unknown",
            agent_uptime_seconds=0
        )
