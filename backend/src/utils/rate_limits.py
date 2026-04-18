"""
Rate limiting configuration for API endpoints.

Provides tiered rate limiting to prevent abuse:
- Authentication endpoints: Strict limits (prevent brute force)
- Data modification endpoints: Moderate limits (prevent spam)
- Read-only endpoints: Generous limits (allow normal usage)
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


class RateLimits:
    """
    Centralized rate limit definitions.

    Format: "requests/time_window"
    Time units: second, minute, hour, day
    """

    # Authentication endpoints (strict)
    AUTH_LOGIN = "5/15minutes"  # 5 attempts per 15 minutes
    AUTH_REGISTER = "3/hour"  # 3 registrations per hour
    AUTH_REFRESH = "10/hour"  # 10 token refreshes per hour

    # Password reset (strict)
    PASSWORD_RESET_REQUEST = "3/hour"  # 3 reset requests per hour
    PASSWORD_RESET_CONFIRM = "5/hour"  # 5 reset confirmations per hour

    # File uploads (moderate)
    FILE_UPLOAD = "5/hour"  # 5 file uploads per hour

    # Invoice operations (moderate)
    INVOICE_CREATE = "30/hour"  # 30 invoice creations per hour
    INVOICE_UPDATE = "60/hour"  # 60 invoice updates per hour
    INVOICE_DELETE = "20/hour"  # 20 invoice deletions per hour
    INVOICE_VALIDATE = "100/hour"  # 100 validations per hour
    INVOICE_POST = "50/hour"  # 50 FBR posts per hour

    # Read operations (generous)
    INVOICE_LIST = "300/hour"  # 300 list requests per hour
    INVOICE_GET = "500/hour"  # 500 get requests per hour
    PROFILE_GET = "200/hour"  # 200 profile requests per hour
    DASHBOARD_STATS = "300/hour"  # 300 dashboard stats requests per hour

    # FBR operations (moderate - external API)
    FBR_VALIDATE = "100/hour"  # 100 FBR validations per hour
    FBR_POST = "50/hour"  # 50 FBR posts per hour
    FBR_STATUS = "200/hour"  # 200 status checks per hour

    # Admin operations (moderate)
    ADMIN_USER_APPROVE = "50/hour"  # 50 user approvals per hour
    ADMIN_USER_LIST = "100/hour"  # 100 user list requests per hour

    # Automation operations (moderate)
    AUTOMATION_UPLOAD = "5/hour"  # 5 Excel uploads per hour
    AUTOMATION_LIST = "100/hour"  # 100 automation list requests per hour
    AUTOMATION_STATUS = "200/hour"  # 200 status checks per hour


def get_rate_limit_message(limit: str) -> str:
    """
    Generate user-friendly rate limit error message.

    Args:
        limit: Rate limit string (e.g., "5/15minutes")

    Returns:
        User-friendly error message
    """
    parts = limit.split("/")
    if len(parts) == 2:
        count, window = parts
        return f"Rate limit exceeded. Maximum {count} requests per {window}. Please try again later."
    return "Rate limit exceeded. Please try again later."
