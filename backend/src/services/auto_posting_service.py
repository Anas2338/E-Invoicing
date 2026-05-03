"""
Auto-posting service for FBR invoice posting automation.

Handles time window logic, daily limit tracking, and sequential posting.
"""
from datetime import datetime, time, date, timedelta
from typing import Optional, Tuple
from sqlmodel import Session, select
from sqlalchemy import and_
import uuid

from src.models.user import User
from src.models.invoice import Invoice, InvoiceStatus
from src.models.daily_posting_counter import DailyPostingCounter
from src.models.posting_log import PostingLog


class AutoPostingService:
    """Service for managing auto-posting functionality."""

    def __init__(self, db: Session):
        self.db = db

    def is_within_time_window(
        self,
        current_time: time,
        start_time: time,
        end_time: time
    ) -> bool:
        """
        Check if current time is within configured window.

        Handles midnight-spanning windows (e.g., 22:00-02:00).

        Args:
            current_time: Current time to check
            start_time: Window start time
            end_time: Window end time

        Returns:
            True if within window, False otherwise
        """
        if start_time <= end_time:
            # Normal case: 09:00 - 18:00
            return start_time <= current_time <= end_time
        else:
            # Midnight-spanning case: 22:00 - 02:00
            return current_time >= start_time or current_time <= end_time

    def get_window_start_date(
        self,
        current_datetime: datetime,
        start_time: time,
        end_time: time
    ) -> date:
        """
        Get the date when the current posting window started.

        For midnight-spanning windows, if current time is before end_time,
        the window started on the previous day.

        Args:
            current_datetime: Current datetime
            start_time: Window start time
            end_time: Window end time

        Returns:
            Date when window started
        """
        current_time = current_datetime.time()
        current_date = current_datetime.date()

        # Check if this is a midnight-spanning window
        if start_time > end_time:
            # If current time is before end_time, window started yesterday
            if current_time <= end_time:
                return current_date - timedelta(days=1)

        return current_date

    def get_or_create_daily_counter(
        self,
        user_id: uuid.UUID,
        counter_date: date,
        window_start_date: date
    ) -> DailyPostingCounter:
        """
        Get or create daily posting counter for user and date.

        Args:
            user_id: User ID
            counter_date: Date for counter
            window_start_date: Date when window started

        Returns:
            DailyPostingCounter instance
        """
        # Try to get existing counter
        statement = select(DailyPostingCounter).where(
            and_(
                DailyPostingCounter.user_id == user_id,
                DailyPostingCounter.date == counter_date
            )
        )
        counter = self.db.exec(statement).first()

        if not counter:
            # Create new counter
            counter = DailyPostingCounter(
                id=uuid.uuid4(),
                user_id=user_id,
                date=counter_date,
                posted_count=0,
                window_start_date=window_start_date
            )
            self.db.add(counter)
            self.db.commit()
            self.db.refresh(counter)

        return counter

    def get_daily_limit_remaining(
        self,
        user: User,
        current_datetime: datetime
    ) -> int:
        """
        Get remaining posting capacity for today.

        Handles midnight-spanning window continuity.

        Args:
            user: User instance
            current_datetime: Current datetime

        Returns:
            Number of invoices that can still be posted today
        """
        # Determine which date's counter to use
        window_start_date = self.get_window_start_date(
            current_datetime,
            user.auto_posting_start_time,
            user.auto_posting_end_time
        )

        # Get counter for the window start date
        counter = self.get_or_create_daily_counter(
            user.id,
            window_start_date,
            window_start_date
        )

        remaining = user.auto_posting_daily_limit - counter.posted_count
        return max(0, remaining)

    def increment_daily_counter(
        self,
        user_id: uuid.UUID,
        current_datetime: datetime,
        start_time: time,
        end_time: time
    ) -> None:
        """
        Increment the daily posting counter.

        Args:
            user_id: User ID
            current_datetime: Current datetime
            start_time: Window start time
            end_time: Window end time
        """
        window_start_date = self.get_window_start_date(
            current_datetime,
            start_time,
            end_time
        )

        counter = self.get_or_create_daily_counter(
            user_id,
            window_start_date,
            window_start_date
        )

        counter.posted_count += 1
        self.db.add(counter)
        self.db.commit()

        # Check if daily limit reached and create notification
        from src.services.notification_service import NotificationService
        notification_service = NotificationService(self.db)

        user = self.db.get(User, user_id)
        if user and counter.posted_count >= user.auto_posting_daily_limit:
            notification = notification_service.create_daily_limit_reached_notification(
                user_id,
                user.auto_posting_daily_limit
            )
            # In production, send notification to notification system
            # For now, just log it
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Daily limit notification: {notification}")

    def create_posting_log(
        self,
        user_id: uuid.UUID,
        invoice_id: uuid.UUID,
        action: str,
        result: str,
        environment: str,
        error_details: Optional[dict] = None,
        agent_cycle_id: Optional[str] = None
    ) -> PostingLog:
        """
        Create a posting log entry.

        Args:
            user_id: User ID
            invoice_id: Invoice ID
            action: 'auto' or 'manual'
            result: 'success' or 'failure'
            environment: 'SANDBOX' or 'PRODUCTION'
            error_details: Error details if failed
            agent_cycle_id: Agent cycle ID for auto posts

        Returns:
            PostingLog instance
        """
        log = PostingLog(
            id=uuid.uuid4(),
            user_id=user_id,
            invoice_id=invoice_id,
            action=action,
            result=result,
            environment=environment,
            error_details=error_details,
            agent_cycle_id=agent_cycle_id
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def validate_time_window(
        self,
        start_time: time,
        end_time: time
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate time window configuration.

        Args:
            start_time: Window start time
            end_time: Window end time

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Both times are valid - midnight-spanning is allowed
        return True, None

    def validate_daily_limit(
        self,
        daily_limit: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate daily limit configuration.

        Args:
            daily_limit: Daily limit value

        Returns:
            Tuple of (is_valid, error_message)
        """
        if daily_limit < 1:
            return False, "Daily limit must be at least 1"
        if daily_limit > 1000:
            return False, "Daily limit cannot exceed 1000"
        return True, None

    def validate_environment(
        self,
        environment: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate environment configuration.

        Args:
            environment: Environment value

        Returns:
            Tuple of (is_valid, error_message)
        """
        if environment not in ['SANDBOX', 'PRODUCTION']:
            return False, "Environment must be SANDBOX or PRODUCTION"
        return True, None
