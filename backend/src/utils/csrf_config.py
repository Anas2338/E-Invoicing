"""
CSRF Protection Configuration

Implements Double Submit Cookie pattern for CSRF protection.
Protects all state-changing operations (POST, PUT, DELETE, PATCH).
"""

from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel
import secrets


class CsrfSettings(BaseModel):
    """CSRF protection settings."""
    secret_key: str = secrets.token_urlsafe(32)
    cookie_name: str = "csrf_token"
    header_name: str = "X-CSRF-Token"
    cookie_samesite: str = "lax"
    cookie_secure: bool = True  # Always use secure cookies
    cookie_httponly: bool = False  # Must be False so JavaScript can read it
    cookie_domain: str = None


# Initialize CSRF settings
csrf_settings = CsrfSettings()


@CsrfProtect.load_config
def get_csrf_config():
    """Load CSRF configuration."""
    return csrf_settings


# Endpoints that should be excluded from CSRF protection
# (typically authentication endpoints that don't have a prior session)
CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/password-reset/with-pin",
    "/api/v1/auth/password-reset/verify-pin",
    "/api/v1/password-reset/request",
    "/api/v1/password-reset/verify",
    "/api/v1/password-reset/confirm",
    "/health",
    "/",
}


def is_csrf_exempt(path: str) -> bool:
    """
    Check if a path is exempt from CSRF protection.

    Args:
        path: Request path

    Returns:
        True if exempt, False otherwise
    """
    return path in CSRF_EXEMPT_PATHS or path.startswith("/api/v1/docs") or path.startswith("/api/v1/openapi")
