"""
CSRF Protection Middleware for AI-agent.
All rejection responses include CORS headers.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import status
import logging

from src.utils.csrf_config import is_csrf_exempt
from src.config.settings import settings

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

    def _cors_headers(self, request: Request) -> dict:
        origin = request.headers.get("origin", "")
        allowed = settings.allowed_origins
        if origin in allowed or "*" in allowed:
            return {
                "Access-Control-Allow-Origin": origin if origin in allowed else "*",
                "Access-Control-Allow-Credentials": "true",
            }
        return {}

    async def dispatch(self, request: Request, call_next):
        if request.method not in self.PROTECTED_METHODS:
            return await call_next(request)

        if is_csrf_exempt(request.url.path):
            return await call_next(request)

        # Bearer token auth (Authorization header) doesn't need CSRF cookie check.
        # The token is stored in sessionStorage, inaccessible to cross-origin attackers,
        # so CSRF attacks cannot forge the Authorization header.
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token") or request.headers.get("x-csrf-token")

        if not csrf_cookie or not csrf_header:
            logger.warning(f"CSRF validation failed: Missing token. Path: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing. Include X-CSRF-Token header."},
                headers=self._cors_headers(request),
            )

        if not self._constant_time_compare(csrf_cookie, csrf_header):
            logger.warning(f"CSRF validation failed: Token mismatch. Path: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token invalid."},
                headers=self._cors_headers(request),
            )

        return await call_next(request)

    @staticmethod
    def _constant_time_compare(a: str, b: str) -> bool:
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        return result == 0
