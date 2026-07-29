"""
Notification API endpoints for FBR data change notifications.
Displays FBR master data changes as a news feed in the dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
import logging

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.fbr_notifications import FBRChangeNotification

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/unread-count", response_model=Dict[str, int])
async def get_unread_notification_count(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get count of unread FBR change notifications.
    Used to display notification badge in UI.

    Returns:
        Dictionary with unread count
    """
    try:
        count = db.query(FBRChangeNotification).filter(
            FBRChangeNotification.is_read == False
        ).count()

        return {"unread_count": count}
    except Exception as e:
        logger.error(f"Error getting unread notification count: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification count"
        )


@router.get("/feed", response_model=List[Dict[str, Any]])
async def get_notification_feed(
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get FBR change notification feed.
    Shows recent changes in FBR master data as a news feed.

    Args:
        limit: Maximum number of notifications to return (default: 50, max: 100)
        offset: Number of notifications to skip (for pagination)
        unread_only: If True, only return unread notifications

    Returns:
        List of notifications
    """
    try:
        # Limit to max 100
        limit = min(limit, 100)

        query = db.query(FBRChangeNotification)

        if unread_only:
            query = query.filter(FBRChangeNotification.is_read == False)

        notifications = query.order_by(
            FBRChangeNotification.created_at.desc()
        ).offset(offset).limit(limit).all()

        result = []
        for notif in notifications:
            result.append({
                "id": notif.id,
                "data_type": notif.data_type,
                "change_type": notif.change_type,
                "record_code": notif.record_code,
                "summary": notif.summary,
                "old_value": notif.old_value,
                "new_value": notif.new_value,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat() if notif.created_at else None
            })

        return result
    except Exception as e:
        logger.error(f"Error getting notification feed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notifications"
        )


@router.post("/mark-read/{notification_id}")
async def mark_notification_read(
    notification_id: int,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Mark a specific notification as read.

    Args:
        notification_id: ID of the notification to mark as read

    Returns:
        Success message
    """
    try:
        notification = db.query(FBRChangeNotification).filter(
            FBRChangeNotification.id == notification_id
        ).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        notification.is_read = True
        db.commit()

        return {"message": "Notification marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Mark all notifications as read.

    Returns:
        Number of notifications marked as read
    """
    try:
        count = db.query(FBRChangeNotification).filter(
            FBRChangeNotification.is_read == False
        ).update({"is_read": True})

        db.commit()

        return {"message": f"Marked {count} notifications as read", "count": count}
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notifications as read"
        )


@router.delete("/cleanup")
async def cleanup_old_notifications(
    days: int = 2,
    db=Depends(get_database_session),
    _user_id: str = Depends(require_authentication)
):
    """
    Delete FBR change notifications older than the specified number of days.

    Args:
        days: Age threshold in days (default: 2). Notifications older than this are deleted.

    Returns:
        Number of deleted notifications
    """
    try:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = db.query(FBRChangeNotification).filter(
            FBRChangeNotification.created_at < cutoff
        ).delete()
        db.commit()
        return {"message": f"Deleted {count} notifications older than {days} days", "deleted_count": count}
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clean up notifications"
        )


@router.get("/summary", response_model=Dict[str, Any])
async def get_notification_summary(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get summary of recent FBR data changes.
    Shows counts by data type and change type.

    Returns:
        Summary statistics
    """
    try:
        # Get counts by data type
        from sqlalchemy import func

        data_type_counts = db.query(
            FBRChangeNotification.data_type,
            func.count(FBRChangeNotification.id).label('count')
        ).filter(
            FBRChangeNotification.is_read == False
        ).group_by(FBRChangeNotification.data_type).all()

        # Get counts by change type
        change_type_counts = db.query(
            FBRChangeNotification.change_type,
            func.count(FBRChangeNotification.id).label('count')
        ).filter(
            FBRChangeNotification.is_read == False
        ).group_by(FBRChangeNotification.change_type).all()

        return {
            "by_data_type": {item.data_type: item.count for item in data_type_counts},
            "by_change_type": {item.change_type: item.count for item in change_type_counts},
            "total_unread": sum(item.count for item in data_type_counts)
        }
    except Exception as e:
        logger.error(f"Error getting notification summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification summary"
        )
