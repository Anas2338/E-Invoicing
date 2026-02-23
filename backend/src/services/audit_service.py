"""
Audit service for logging and retrieving audit logs.
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, select, and_
from ..models.audit_log import AuditLog, AuditAction


class AuditService:
    """Service for managing audit logs."""

    @staticmethod
    def log_fbr_interaction(
        db: Session,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        environment: str,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        request_payload: Optional[dict] = None,
        response_payload: Optional[dict] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an FBR API interaction or critical operation.

        Args:
            db: Database session
            user_id: User who performed the action
            action: Action performed (e.g., validate_invoice, post_invoice)
            resource_type: Type of resource (e.g., invoice, user)
            resource_id: ID of the resource
            environment: Environment (SANDBOX or PRODUCTION)
            endpoint: FBR API endpoint called
            method: HTTP method (GET, POST, etc.)
            request_payload: Request payload sent to FBR
            response_payload: Response received from FBR
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            error_message: Error message if request failed
            error_code: Error code if request failed
            correlation_id: Correlation ID for tracking related requests
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created audit log entry
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            environment=environment,
            endpoint=endpoint,
            method=method,
            request_payload=request_payload,
            response_payload=response_payload,
            status_code=status_code,
            duration_ms=duration_ms,
            error_message=error_message,
            error_code=error_code,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)

        return audit_log

    @staticmethod
    def list_audit_logs(
        db: Session,
        user_id: str,
        environment: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[AuditLog], int]:
        """
        List audit logs with filtering and pagination.

        Args:
            db: Database session
            user_id: User ID to filter by
            environment: Environment filter (SANDBOX or PRODUCTION)
            action: Action filter
            resource_type: Resource type filter
            resource_id: Resource ID filter
            start_date: Start date for date range filter
            end_date: End date for date range filter
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Tuple of (audit logs list, total count)
        """
        # Build query with filters
        query = select(AuditLog).where(AuditLog.user_id == user_id)

        if environment:
            query = query.where(AuditLog.environment == environment)

        if action:
            query = query.where(AuditLog.action == action)

        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)

        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)

        if start_date:
            query = query.where(AuditLog.created_at >= start_date)

        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        # Get total count
        count_query = select(AuditLog).where(AuditLog.user_id == user_id)
        if environment:
            count_query = count_query.where(AuditLog.environment == environment)
        if action:
            count_query = count_query.where(AuditLog.action == action)
        if resource_type:
            count_query = count_query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            count_query = count_query.where(AuditLog.resource_id == resource_id)
        if start_date:
            count_query = count_query.where(AuditLog.created_at >= start_date)
        if end_date:
            count_query = count_query.where(AuditLog.created_at <= end_date)

        total = len(db.exec(count_query).all())

        # Apply pagination and ordering
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)

        audit_logs = db.exec(query).all()

        return audit_logs, total

    @staticmethod
    def get_audit_log_by_id(db: Session, audit_log_id: int, user_id: str) -> Optional[AuditLog]:
        """
        Get a specific audit log by ID.

        Args:
            db: Database session
            audit_log_id: Audit log ID
            user_id: User ID for authorization check

        Returns:
            Audit log if found and user has access, None otherwise
        """
        query = select(AuditLog).where(
            and_(
                AuditLog.id == audit_log_id,
                AuditLog.user_id == user_id
            )
        )

        return db.exec(query).first()
