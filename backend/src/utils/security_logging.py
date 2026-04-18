"""
Security event logging utility.

Logs all security-relevant events for audit trail and incident response:
- Authentication events (success/failure)
- Authorization failures
- Suspicious activity
- Data access patterns
- Configuration changes
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

# Configure security logger
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)


class SecurityEventType(str, Enum):
    """Security event types for categorization."""

    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token.refresh"
    AUTH_TOKEN_INVALID = "auth.token.invalid"
    AUTH_SESSION_EXPIRED = "auth.session.expired"

    # Authorization events
    AUTHZ_ACCESS_DENIED = "authz.access.denied"
    AUTHZ_PERMISSION_DENIED = "authz.permission.denied"
    AUTHZ_RESOURCE_FORBIDDEN = "authz.resource.forbidden"

    # Account events
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_LOCKED = "account.locked"
    ACCOUNT_UNLOCKED = "account.unlocked"
    ACCOUNT_DELETED = "account.deleted"
    ACCOUNT_PASSWORD_CHANGED = "account.password.changed"
    ACCOUNT_PASSWORD_RESET_REQUESTED = "account.password.reset.requested"
    ACCOUNT_PASSWORD_RESET_COMPLETED = "account.password.reset.completed"

    # Data access events
    DATA_INVOICE_CREATED = "data.invoice.created"
    DATA_INVOICE_UPDATED = "data.invoice.updated"
    DATA_INVOICE_DELETED = "data.invoice.deleted"
    DATA_INVOICE_VIEWED = "data.invoice.viewed"
    DATA_BULK_EXPORT = "data.bulk.export"

    # FBR integration events
    FBR_VALIDATION_SUCCESS = "fbr.validation.success"
    FBR_VALIDATION_FAILURE = "fbr.validation.failure"
    FBR_POST_SUCCESS = "fbr.post.success"
    FBR_POST_FAILURE = "fbr.post.failure"
    FBR_CREDENTIALS_UPDATED = "fbr.credentials.updated"

    # Suspicious activity
    SUSPICIOUS_RATE_LIMIT_EXCEEDED = "suspicious.rate_limit.exceeded"
    SUSPICIOUS_MULTIPLE_FAILED_LOGINS = "suspicious.multiple_failed_logins"
    SUSPICIOUS_INVALID_TOKEN_PATTERN = "suspicious.invalid_token.pattern"
    SUSPICIOUS_UNUSUAL_ACCESS_PATTERN = "suspicious.unusual_access.pattern"
    SUSPICIOUS_FILE_UPLOAD = "suspicious.file.upload"

    # Configuration changes
    CONFIG_SETTINGS_CHANGED = "config.settings.changed"
    CONFIG_PERMISSIONS_CHANGED = "config.permissions.changed"
    CONFIG_CORS_CHANGED = "config.cors.changed"

    # Security incidents
    INCIDENT_SQL_INJECTION_ATTEMPT = "incident.sql_injection.attempt"
    INCIDENT_XSS_ATTEMPT = "incident.xss.attempt"
    INCIDENT_CSRF_ATTEMPT = "incident.csrf.attempt"
    INCIDENT_FILE_UPLOAD_MALICIOUS = "incident.file_upload.malicious"


class SecurityEventSeverity(str, Enum):
    """Security event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def log_security_event(
    event_type: SecurityEventType,
    severity: SecurityEventSeverity,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
):
    """
    Log a security event with structured data.

    Args:
        event_type: Type of security event
        severity: Severity level
        user_id: User ID (if authenticated)
        ip_address: Client IP address
        user_agent: Client user agent
        details: Additional event details
        request_id: Request correlation ID
    """
    event_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type.value,
        "severity": severity.value,
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "request_id": request_id,
        "details": details or {}
    }

    # Log as JSON for easy parsing
    log_message = json.dumps(event_data)

    # Log at appropriate level
    if severity == SecurityEventSeverity.INFO:
        security_logger.info(log_message)
    elif severity == SecurityEventSeverity.WARNING:
        security_logger.warning(log_message)
    elif severity == SecurityEventSeverity.ERROR:
        security_logger.error(log_message)
    elif severity == SecurityEventSeverity.CRITICAL:
        security_logger.critical(log_message)


def log_authentication_success(user_id: str, ip_address: str, user_agent: str):
    """Log successful authentication."""
    log_security_event(
        event_type=SecurityEventType.AUTH_LOGIN_SUCCESS,
        severity=SecurityEventSeverity.INFO,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )


def log_authentication_failure(email: str, ip_address: str, user_agent: str, reason: str):
    """Log failed authentication attempt."""
    log_security_event(
        event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
        severity=SecurityEventSeverity.WARNING,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"email": email, "reason": reason}
    )


def log_authorization_failure(user_id: str, resource: str, action: str, ip_address: str):
    """Log authorization failure."""
    log_security_event(
        event_type=SecurityEventType.AUTHZ_ACCESS_DENIED,
        severity=SecurityEventSeverity.WARNING,
        user_id=user_id,
        ip_address=ip_address,
        details={"resource": resource, "action": action}
    )


def log_account_locked(user_id: str, reason: str, ip_address: str):
    """Log account lockout."""
    log_security_event(
        event_type=SecurityEventType.ACCOUNT_LOCKED,
        severity=SecurityEventSeverity.WARNING,
        user_id=user_id,
        ip_address=ip_address,
        details={"reason": reason}
    )


def log_suspicious_activity(
    activity_type: str,
    user_id: Optional[str],
    ip_address: str,
    details: Dict[str, Any]
):
    """Log suspicious activity."""
    log_security_event(
        event_type=SecurityEventType.SUSPICIOUS_UNUSUAL_ACCESS_PATTERN,
        severity=SecurityEventSeverity.ERROR,
        user_id=user_id,
        ip_address=ip_address,
        details={"activity_type": activity_type, **details}
    )


def log_rate_limit_exceeded(user_id: Optional[str], ip_address: str, endpoint: str, limit: str):
    """Log rate limit exceeded."""
    log_security_event(
        event_type=SecurityEventType.SUSPICIOUS_RATE_LIMIT_EXCEEDED,
        severity=SecurityEventSeverity.WARNING,
        user_id=user_id,
        ip_address=ip_address,
        details={"endpoint": endpoint, "limit": limit}
    )


def log_password_reset_requested(email: str, ip_address: str):
    """Log password reset request."""
    log_security_event(
        event_type=SecurityEventType.ACCOUNT_PASSWORD_RESET_REQUESTED,
        severity=SecurityEventSeverity.INFO,
        ip_address=ip_address,
        details={"email": email}
    )


def log_password_reset_completed(user_id: str, ip_address: str):
    """Log password reset completion."""
    log_security_event(
        event_type=SecurityEventType.ACCOUNT_PASSWORD_RESET_COMPLETED,
        severity=SecurityEventSeverity.INFO,
        user_id=user_id,
        ip_address=ip_address
    )


def log_fbr_operation(
    operation: str,
    success: bool,
    user_id: str,
    environment: str,
    details: Dict[str, Any]
):
    """Log FBR API operation."""
    event_type = (
        SecurityEventType.FBR_POST_SUCCESS if success and operation == "post"
        else SecurityEventType.FBR_POST_FAILURE if not success and operation == "post"
        else SecurityEventType.FBR_VALIDATION_SUCCESS if success
        else SecurityEventType.FBR_VALIDATION_FAILURE
    )

    severity = SecurityEventSeverity.INFO if success else SecurityEventSeverity.WARNING

    log_security_event(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        details={"operation": operation, "environment": environment, **details}
    )


def log_malicious_file_upload(user_id: str, ip_address: str, filename: str, reason: str):
    """Log malicious file upload attempt."""
    log_security_event(
        event_type=SecurityEventType.INCIDENT_FILE_UPLOAD_MALICIOUS,
        severity=SecurityEventSeverity.CRITICAL,
        user_id=user_id,
        ip_address=ip_address,
        details={"filename": filename, "reason": reason}
    )
