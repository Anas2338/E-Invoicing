"""
Admin Transfer Management Endpoints.

Provides admin-only endpoints for managing invoice transfers.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlmodel import Session, select
from typing import Annotated, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

from src.database.session import get_db, get_automation_db
from src.middleware.rbac import require_admin
from src.services.transfer_service import TransferService
from src.models.transfer_log import TransferLog
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


class RetryRequest(BaseModel):
    """Request model for retry endpoint."""
    invoice_ids: Optional[List[UUID]] = None  # If None, retry all failed invoices


@router.post("/trigger")
@limiter.limit("10/hour")
async def trigger_transfer(
    request: Request,
    dry_run: bool = False,
    main_db: Session = Depends(get_db),
    automation_db: Session = Depends(get_automation_db),
    admin_user_id: str = Depends(require_admin)
):
    """
    Manually trigger invoice transfer job.

    Admin only. Rate limited to 10 requests/hour per admin.
    """
    logger.info(f"Manual transfer triggered by admin {admin_user_id}, dry_run={dry_run}")
    
    if dry_run:
        # Count invoices that would be transferred
        from datetime import date
        today = date.today()
        statement = select(AutomationInvoice).where(
            AutomationInvoice.status == AutomationInvoiceStatus.VALIDATED,
            AutomationInvoice.scheduled_date <= today
        )
        invoices = automation_db.exec(statement).all()
        
        return {
            "success": True,
            "dry_run": True,
            "message": f"Would transfer {len(invoices)} invoices",
            "invoices_to_transfer": len(invoices)
        }
    
    # Execute actual transfer
    transfer_service = TransferService()
    result = await transfer_service.transfer_validated_invoices(
        automation_db=automation_db,
        main_db=main_db,
        triggered_by="manual",
        triggered_by_user_id=UUID(admin_user_id)
    )
    
    return {
        "success": result.success,
        "message": "Transfer completed" if result.success else "Transfer failed",
        "transfer_id": str(result.transfer_log_id) if result.transfer_log_id else None,
        "summary": {
            "invoices_transferred": result.invoices_transferred,
            "invoices_failed": result.invoices_failed,
            "duration_seconds": result.duration_seconds
        },
        "failed_invoice_ids": [str(id) for id in result.failed_invoice_ids]
    }


@router.post("/retry")
@limiter.limit("10/hour")
async def retry_failed_transfers(
    request: Request,
    retry_request: RetryRequest = Body(...),
    main_db: Session = Depends(get_db),
    automation_db: Session = Depends(get_automation_db),
    admin_user_id: str = Depends(require_admin)
):
    """
    Retry previously failed invoice transfers.

    Admin only. Rate limited to 10 requests/hour per admin.

    Args:
        retry_request: Optional list of invoice IDs to retry. If empty, retries all failed.
    """
    logger.info(f"Retry transfer triggered by admin {admin_user_id}")

    # Validate invoice_ids if provided
    if retry_request.invoice_ids:
        if len(retry_request.invoice_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invoice_ids array cannot be empty. Omit the field to retry all failed invoices."
            )

        if len(retry_request.invoice_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot retry more than 100 invoices at once"
            )

        # Verify all invoice IDs exist and are in TRANSFER_FAILED status
        statement = select(AutomationInvoice).where(
            AutomationInvoice.id.in_(retry_request.invoice_ids)
        )
        invoices = automation_db.exec(statement).all()

        if len(invoices) != len(retry_request.invoice_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more invoice IDs not found"
            )

        non_failed = [
            str(inv.id) for inv in invoices
            if inv.status != AutomationInvoiceStatus.TRANSFER_FAILED
        ]
        if non_failed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invoices not in TRANSFER_FAILED status: {', '.join(non_failed)}"
            )

    # Execute retry
    transfer_service = TransferService()
    result = await transfer_service.retry_failed_transfers(
        automation_db=automation_db,
        main_db=main_db,
        invoice_ids=retry_request.invoice_ids,
        triggered_by_user_id=UUID(admin_user_id)
    )

    return {
        "success": result.success,
        "message": "Retry completed" if result.success else "Retry failed",
        "transfer_log_id": str(result.transfer_log_id) if result.transfer_log_id else None,
        "summary": {
            "invoices_retried": result.invoices_transferred + result.invoices_failed,
            "invoices_succeeded": result.invoices_transferred,
            "invoices_failed": result.invoices_failed,
            "duration_seconds": result.duration_seconds
        },
        "failed_invoice_ids": [str(id) for id in result.failed_invoice_ids],
        "error_message": result.error_message
    }


@router.get("/logs")
async def get_transfer_logs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    automation_db: Session = Depends(get_automation_db),
    admin_user_id: str = Depends(require_admin)
):
    """
    Get transfer operation logs.
    
    Admin only.
    """
    statement = select(TransferLog).order_by(TransferLog.transfer_timestamp.desc())
    
    if status:
        statement = statement.where(TransferLog.status == status)
    
    statement = statement.offset(offset).limit(min(limit, 200))
    
    logs = automation_db.exec(statement).all()
    
    # Count total
    count_statement = select(TransferLog)
    if status:
        count_statement = count_statement.where(TransferLog.status == status)
    total = len(automation_db.exec(count_statement).all())
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": [
            {
                "id": str(log.id),
                "transfer_timestamp": log.transfer_timestamp.isoformat(),
                "status": log.status,
                "invoices_transferred": log.invoices_transferred,
                "invoices_failed": log.invoices_failed,
                "duration_seconds": log.duration_seconds,
                "triggered_by": log.triggered_by,
                "error_details": log.error_details
            }
            for log in logs
        ]
    }


@router.get("/stats")
async def get_transfer_stats(
    days: int = 30,
    automation_db: Session = Depends(get_automation_db),
    admin_user_id: str = Depends(require_admin)
):
    """
    Get aggregate transfer statistics.
    
    Admin only.
    """
    from_date = datetime.utcnow() - timedelta(days=days)
    
    statement = select(TransferLog).where(
        TransferLog.transfer_timestamp >= from_date
    )
    logs = automation_db.exec(statement).all()
    
    if not logs:
        return {
            "period": {"from": from_date.date().isoformat(), "to": datetime.utcnow().date().isoformat(), "days": days},
            "summary": {
                "total_transfers": 0,
                "successful_transfers": 0,
                "failed_transfers": 0,
                "total_invoices_transferred": 0,
                "total_invoices_failed": 0
            }
        }
    
    total_transfers = len(logs)
    successful = sum(1 for log in logs if log.status == "success")
    partial = sum(1 for log in logs if log.status == "partial_success")
    failed = sum(1 for log in logs if log.status == "failed")
    total_invoices_transferred = sum(log.invoices_transferred for log in logs)
    total_invoices_failed = sum(log.invoices_failed for log in logs)
    avg_duration = sum(log.duration_seconds for log in logs) / len(logs)
    
    return {
        "period": {
            "from": from_date.date().isoformat(),
            "to": datetime.utcnow().date().isoformat(),
            "days": days
        },
        "summary": {
            "total_transfers": total_transfers,
            "successful_transfers": successful,
            "partial_success_transfers": partial,
            "failed_transfers": failed,
            "success_rate": round((successful / total_transfers * 100), 1) if total_transfers > 0 else 0,
            "total_invoices_transferred": total_invoices_transferred,
            "total_invoices_failed": total_invoices_failed,
            "average_duration_seconds": round(avg_duration, 2)
        }
    }
