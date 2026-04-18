"""
CSRF Protection Middleware

Validates CSRF tokens on all state-changing requests.
Uses Double Submit Cookie pattern.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import status
import logging

from src.utils.csrf_config import is_csrf_exempt

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate CSRF tokens on state-changing requests.

    SECURITY: Protects against Cross-Site Request Forgery attacks by validating
    that requests include a valid CSRF token that matches the cookie.
    """

    # HTTP methods that require CSRF protection
    PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate CSRF token if needed.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            Response from handler or 403 if CSRF validation fails
        """
        # Only check CSRF for state-changing methods
        if request.method not in self.PROTECTED_METHODS:
            return await call_next(request)

        # Check if path is exempt from CSRF protection
        if is_csrf_exempt(request.url.path):
            return await call_next(request)

        # Get CSRF token from cookie
        csrf_cookie = request.cookies.get("csrf_token")

        # Get CSRF token from header
        csrf_header = request.headers.get("X-CSRF-Token") or request.headers.get("x-csrf-token")

        # Validate CSRF token
        if not csrf_cookie or not csrf_header:
            logger.warning(f"CSRF validation failed: Missing token. Path: {request.url.path}, Method: {request.method}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing. Include X-CSRF-Token header."}
            )

        # Compare tokens (constant-time comparison to prevent timing attacks)
        if not self._constant_time_compare(csrf_cookie, csrf_header):
            logger.warning(f"CSRF validation failed: Token mismatch. Path: {request.url.path}, Method: {request.method}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token invalid."}
            )

        # CSRF validation passed
        return await call_next(request)

    @staticmethod
    def _constant_time_compare(a: str, b: str) -> bool:
        """
        Constant-time string comparison to prevent timing attacks.

        Args:
            a: First string
            b: Second string

        Returns:
            True if strings are equal, False otherwise
        """
        if len(a) != len(b):
            return False

        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)

        return result == 0
