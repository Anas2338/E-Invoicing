"""
Health check endpoints for FTE worker monitoring.
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from datetime import datetime, timedelta

from src.database.session import get_db
from src.models.automation_log import AutomationLog, AutomationLogAction

router = APIRouter(prefix="/health", tags=["automation-health"])


@router.get("/worker")
async def get_worker_health(db: Session = Depends(get_db)):
    """
    Health check endpoint for FTE worker monitoring.

    Returns worker status including:
    - Whether worker is healthy (processed invoices recently)
    - Last processing time
    - Recent activity count

    A worker is considered healthy if it has processed invoices
    within the last 2 hours.

    Returns:
        Health status with last activity timestamp
    """
    # Get the most recent worker activity
    statement = select(AutomationLog).where(
        AutomationLog.action.in_([
            AutomationLogAction.VALIDATE,
            AutomationLogAction.SUBMIT,
            AutomationLogAction.RETRY
        ])
    ).order_by(AutomationLog.timestamp.desc()).limit(1)

    last_activity = db.exec(statement).first()

    # Count recent activities (last 24 hours)
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    count_statement = select(func.count(AutomationLog.id)).where(
        AutomationLog.timestamp >= twenty_four_hours_ago
    )
    recent_activity_count = db.exec(count_statement).one()

    # Determine health status
    # Worker is healthy if it has activity within last 2 hours
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    is_healthy = last_activity is not None and last_activity.timestamp >= two_hours_ago

    return {
        "status": "healthy" if is_healthy else "inactive",
        "last_activity": last_activity.timestamp.isoformat() if last_activity else None,
        "recent_activity_count_24h": recent_activity_count,
        "checked_at": datetime.utcnow().isoformat()
    }


@router.get("/status")
async def get_system_status(db: Session = Depends(get_db)):
    """
    Overall system health status.

    Returns:
        System status including database connectivity
    """
    try:
        # Simple database connectivity check
        db.exec(select(func.count()).select_from(AutomationLog)).one()

        return {
            "status": "operational",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
