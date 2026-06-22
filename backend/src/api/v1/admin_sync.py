"""
Admin API endpoints for FBR master data sync management.
Allows administrators to manually trigger sync, check sync status, and manage system FBR token.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import logging

from src.middleware.rbac import require_admin
from src.api.deps import get_database_session
from src.services.fbr_master_data_sync_service import FBRMasterDataSyncService
from src.services.scheduler import get_scheduler_status
from src.models.fbr_master_data import FBRSyncLog
from src.models.user import User, UserRole
from src.utils.encryption import get_encryption_service

router = APIRouter()
logger = logging.getLogger(__name__)


def get_admin_fbr_token(db) -> str:
    """Get FBR system sync token from admin user."""
    try:
        admin_user = db.query(User).filter(
            User.role == UserRole.ADMIN.value,
            User.fbr_system_sync_token.isnot(None)
        ).first()

        if not admin_user or not admin_user.fbr_system_sync_token:
            return None

        encryption_service = get_encryption_service()
        try:
            decrypted_token = encryption_service.decrypt(admin_user.fbr_system_sync_token)
            return decrypted_token
        except Exception as decrypt_error:
            logger.error(f"Failed to decrypt FBR system sync token: {decrypt_error}")
            return None

    except Exception as e:
        logger.error(f"Error getting admin FBR token: {str(e)}")
        return None


@router.post("/sync/trigger", response_model=Dict[str, Any])
async def trigger_manual_sync(
    db=Depends(get_database_session),
    user_id: str = Depends(require_admin)
):
    """
    Manually trigger FBR master data sync.
    Only accessible by admin users.
    Uses admin-controlled system FBR token.

    Returns:
        Sync results with status and record counts
    """
    logger.info(f"Manual sync triggered by admin user: {user_id}")

    # Get FBR token from admin user
    fbr_token = get_admin_fbr_token(db)

    if not fbr_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System FBR token not configured. Please set the token in your admin profile under FBR credentials."
        )

    try:
        sync_service = FBRMasterDataSyncService(db, fbr_token)
        result = await sync_service.sync_all()

        return {
            "message": "Manual sync completed",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error during manual sync: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


@router.get("/sync/status", response_model=Dict[str, Any])
async def get_sync_status(
    db=Depends(get_database_session),
    user_id: str = Depends(require_admin)
):
    """
    Get FBR master data sync status.
    Shows scheduler status and recent sync logs.

    Returns:
        Scheduler status and recent sync history
    """
    try:
        # Get scheduler status
        scheduler_status = get_scheduler_status()

        # Get recent sync logs (last 10)
        recent_syncs = db.query(FBRSyncLog).order_by(
            FBRSyncLog.started_at.desc()
        ).limit(10).all()

        sync_history = []
        for log in recent_syncs:
            sync_history.append({
                "id": log.id,
                "sync_type": log.sync_type,
                "status": log.status,
                "records_synced": log.records_synced,
                "error_message": log.error_message,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "duration_seconds": log.duration_seconds
            })

        # Get record counts from database
        from src.models.fbr_master_data import (
            FBRProvince, FBRUOM, FBRHSCode, FBRTransactionType,
            FBRInvoiceType, FBRTaxRate
        )

        record_counts = {
            "provinces": db.query(FBRProvince).count(),
            "uom": db.query(FBRUOM).count(),
            "hs_codes": db.query(FBRHSCode).count(),
            "transaction_types": db.query(FBRTransactionType).count(),
            "invoice_types": db.query(FBRInvoiceType).count(),
            "tax_rates": db.query(FBRTaxRate).count()
        }

        # Check if system token is configured
        token_configured = get_admin_fbr_token(db) is not None

        return {
            "scheduler": scheduler_status,
            "recent_syncs": sync_history,
            "current_record_counts": record_counts,
            "system_token_configured": token_configured
        }
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )


@router.get("/sync/logs", response_model=List[Dict[str, Any]])
async def get_sync_logs(
    limit: int = 50,
    db=Depends(get_database_session),
    user_id: str = Depends(require_admin)
):
    """
    Get FBR master data sync logs.

    Args:
        limit: Maximum number of logs to return (default: 50, max: 100)

    Returns:
        List of sync logs
    """
    try:
        # Limit to max 100
        limit = min(limit, 100)

        logs = db.query(FBRSyncLog).order_by(
            FBRSyncLog.started_at.desc()
        ).limit(limit).all()

        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "sync_type": log.sync_type,
                "status": log.status,
                "records_synced": log.records_synced,
                "error_message": log.error_message,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "duration_seconds": log.duration_seconds
            })

        return result
    except Exception as e:
        logger.error(f"Error getting sync logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync logs: {str(e)}"
        )
