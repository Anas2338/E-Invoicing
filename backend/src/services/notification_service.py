"""
Notification service for auto-posting events.

Handles creation of notifications for:
- Daily summaries
- Daily limit reached
- High failure rate
- Auto-posting paused/resumed
"""
from datetime import datetime, date
from typing import Optional
from sqlmodel import Session, select
from sqlalchemy import and_, func
import uuid

from src.models.user import User
from src.models.posting_log import PostingLog
from src.models.daily_posting_counter import DailyPostingCounter


class NotificationService:
    """Service for creating auto-posting notifications."""

    def __init__(self, db: Session):
        self.db = db

    def create_daily_summary_notification(
        self,
        user_id: uuid.UUID,
        posted_count: int,
        failed_count: int,
        notification_date: date
    ) -> dict:
        """
        Create daily summary notification.

        Args:
            user_id: User ID
            posted_count: Number of invoices posted today
            failed_count: Number of invoices failed today
            notification_date: Date for the summary

        Returns:
            Notification data
        """
        return {
            'user_id': str(user_id),
            'type': 'auto_posting_daily_summary',
            'title': 'Auto-Posting Daily Summary',
            'message': f'Posted {posted_count} invoices, {failed_count} failed on {notification_date.isoformat()}',
            'data': {
                'posted_count': posted_count,
                'failed_count': failed_count,
                'date': notification_date.isoformat()
            },
            'created_at': datetime.utcnow().isoformat()
        }

    def create_daily_limit_reached_notification(
        self,
        user_id: uuid.UUID,
        daily_limit: int
    ) -> dict:
        """
        Create daily limit reached notification.

        Args:
            user_id: User ID
            daily_limit: Daily limit value

        Returns:
            Notification data
        """
        return {
            'user_id': str(user_id),
            'type': 'auto_posting_limit_reached',
            'title': 'Daily Posting Limit Reached',
            'message': f'You have reached your daily limit of {daily_limit} invoices. Auto-posting will resume tomorrow.',
            'data': {
                'daily_limit': daily_limit
            },
            'created_at': datetime.utcnow().isoformat()
        }

    def create_high_failure_rate_notification(
        self,
        user_id: uuid.UUID,
        failure_rate: float,
        failed_count: int,
        total_count: int
    ) -> dict:
        """
        Create high failure rate notification.

        Args:
            user_id: User ID
            failure_rate: Failure rate (0-1)
            failed_count: Number of failed invoices
            total_count: Total number of invoices

        Returns:
            Notification data
        """
        return {
            'user_id': str(user_id),
            'type': 'auto_posting_high_failure_rate',
            'title': 'High Auto-Posting Failure Rate',
            'message': f'Auto-posting has a high failure rate: {failed_count}/{total_count} ({failure_rate*100:.1f}%). Please review your invoices.',
            'data': {
                'failure_rate': failure_rate,
                'failed_count': failed_count,
                'total_count': total_count
            },
            'created_at': datetime.utcnow().isoformat(),
            'priority': 'high'
        }

    def create_auto_posting_paused_notification(
        self,
        user_id: uuid.UUID,
        reason: str
    ) -> dict:
        """
        Create auto-posting paused notification.

        Args:
            user_id: User ID
            reason: Reason for pause

        Returns:
            Notification data
        """
        return {
            'user_id': str(user_id),
            'type': 'auto_posting_paused',
            'title': 'Auto-Posting Paused',
            'message': f'Auto-posting has been paused: {reason}',
            'data': {
                'reason': reason
            },
            'created_at': datetime.utcnow().isoformat(),
            'priority': 'high'
        }

    def create_auto_posting_resumed_notification(
        self,
        user_id: uuid.UUID
    ) -> dict:
        """
        Create auto-posting resumed notification.

        Args:
            user_id: User ID

        Returns:
            Notification data
        """
        return {
            'user_id': str(user_id),
            'type': 'auto_posting_resumed',
            'title': 'Auto-Posting Resumed',
            'message': 'Auto-posting has been resumed and is now active.',
            'data': {},
            'created_at': datetime.utcnow().isoformat()
        }

    def check_and_create_limit_notification(
        self,
        user_id: uuid.UUID,
        user: User,
        current_date: date
    ) -> Optional[dict]:
        """
        Check if daily limit reached and create notification if needed.

        Args:
            user_id: User ID
            user: User instance
            current_date: Current date

        Returns:
            Notification data if limit reached, None otherwise
        """
        # Get counter for today
        statement = select(DailyPostingCounter).where(
            and_(
                DailyPostingCounter.user_id == user_id,
                DailyPostingCounter.date == current_date
            )
        )
        counter = self.db.exec(statement).first()

        if counter and counter.posted_count >= user.auto_posting_daily_limit:
            return self.create_daily_limit_reached_notification(
                user_id,
                user.auto_posting_daily_limit
            )

        return None

    def check_and_create_failure_notification(
        self,
        user_id: uuid.UUID,
        current_date: date,
        threshold: float = 0.2
    ) -> Optional[dict]:
        """
        Check failure rate and create notification if above threshold.

        Args:
            user_id: User ID
            current_date: Current date
            threshold: Failure rate threshold (default 20%)

        Returns:
            Notification data if failure rate high, None otherwise
        """
        # Count successes and failures today
        success_count = self.db.execute(
            select(func.count(PostingLog.id)).where(
                and_(
                    PostingLog.user_id == user_id,
                    PostingLog.result == 'success',
                    PostingLog.created_at >= datetime.combine(current_date, datetime.min.time())
                )
            )
        ).scalar() or 0

        failure_count = self.db.execute(
            select(func.count(PostingLog.id)).where(
                and_(
                    PostingLog.user_id == user_id,
                    PostingLog.result == 'failure',
                    PostingLog.created_at >= datetime.combine(current_date, datetime.min.time())
                )
            )
        ).scalar() or 0

        total_count = success_count + failure_count

        if total_count >= 5:  # Only check if at least 5 attempts
            failure_rate = failure_count / total_count
            if failure_rate >= threshold:
                return self.create_high_failure_rate_notification(
                    user_id,
                    failure_rate,
                    failure_count,
                    total_count
                )

        return None
