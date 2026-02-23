"""
Idempotency service for preventing duplicate invoice postings.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import Session, select
from ..models.idempotency import IdempotencyCache


class IdempotencyService:
    """Service for managing idempotency cache."""

    @staticmethod
    def check_cache(
        db: Session,
        idempotency_key: str,
        user_id: str
    ) -> Optional[IdempotencyCache]:
        """
        Check if an idempotency key exists in the cache and is still valid.

        Args:
            db: Database session
            idempotency_key: Unique idempotency key
            user_id: User ID for authorization check

        Returns:
            Cached entry if found and not expired, None otherwise
        """
        query = select(IdempotencyCache).where(
            IdempotencyCache.idempotency_key == idempotency_key,
            IdempotencyCache.user_id == user_id,
            IdempotencyCache.expires_at > datetime.utcnow()
        )

        return db.exec(query).first()

    @staticmethod
    def store_result(
        db: Session,
        idempotency_key: str,
        user_id: str,
        invoice_id: str,
        environment: str,
        response_payload: Dict[str, Any],
        status_code: int,
        success: bool,
        error_message: Optional[str] = None
    ) -> IdempotencyCache:
        """
        Store a posting result in the idempotency cache with 24h TTL.

        Args:
            db: Database session
            idempotency_key: Unique idempotency key
            user_id: User who initiated the request
            invoice_id: Invoice ID that was posted
            environment: Environment (SANDBOX or PRODUCTION)
            response_payload: Response from FBR
            status_code: HTTP status code
            success: Whether the posting was successful
            error_message: Error message if posting failed

        Returns:
            Created cache entry
        """
        cache_entry = IdempotencyCache(
            idempotency_key=idempotency_key,
            user_id=user_id,
            invoice_id=invoice_id,
            environment=environment,
            response_payload=response_payload,
            status_code=status_code,
            success=success,
            error_message=error_message
        )

        db.add(cache_entry)
        db.commit()
        db.refresh(cache_entry)

        return cache_entry

    @staticmethod
    def cleanup_expired(db: Session) -> int:
        """
        Clean up expired cache entries.

        Args:
            db: Database session

        Returns:
            Number of entries deleted
        """
        query = select(IdempotencyCache).where(
            IdempotencyCache.expires_at <= datetime.utcnow()
        )

        expired_entries = db.exec(query).all()
        count = len(expired_entries)

        for entry in expired_entries:
            db.delete(entry)

        db.commit()

        return count

    @staticmethod
    def generate_key(user_id: str, invoice_id: str, timestamp: Optional[datetime] = None) -> str:
        """
        Generate a standard idempotency key.

        Args:
            user_id: User ID
            invoice_id: Invoice ID
            timestamp: Optional timestamp (defaults to current time)

        Returns:
            Generated idempotency key
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        timestamp_str = timestamp.strftime("%Y%m%d%H%M%S")
        return f"{user_id}-{invoice_id}-{timestamp_str}"
