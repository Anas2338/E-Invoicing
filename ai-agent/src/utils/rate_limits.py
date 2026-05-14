"""Rate limiting configuration for AI-agent endpoints."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


class RateLimits:
    FILE_UPLOAD = "5/hour"
    INVOICE_LIST = "300/hour"
    INVOICE_GET = "500/hour"
    DASHBOARD_STATS = "300/hour"
    AUTOMATION_UPLOAD = "5/hour"
    AUTOMATION_LIST = "100/hour"
    AUTOMATION_STATUS = "200/hour"


def get_rate_limit_message(limit: str) -> str:
    parts = limit.split("/")
    if len(parts) == 2:
        count, window = parts
        return f"Rate limit exceeded. Maximum {count} requests per {window}."
    return "Rate limit exceeded."
