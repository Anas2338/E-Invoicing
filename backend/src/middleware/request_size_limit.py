"""
Request Size Limit Middleware

Prevents DoS attacks via large request payloads.
Limits request body size to prevent memory exhaustion.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import status
import logging

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size.

    SECURITY: Prevents DoS attacks via large payloads that could exhaust memory.
    """

    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            max_request_size: Maximum request size in bytes (default: 10MB)
        """
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next):
        """
        Process request and check size.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            Response from handler or 413 if request too large
        """
        # Check Content-Length header
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                content_length_int = int(content_length)

                if content_length_int > self.max_request_size:
                    size_mb = content_length_int / (1024 * 1024)
                    max_mb = self.max_request_size / (1024 * 1024)

                    logger.warning(
                        f"Request too large: {size_mb:.2f}MB (max: {max_mb:.0f}MB). "
                        f"Path: {request.url.path}, Method: {request.method}"
                    )

                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "detail": f"Request body too large. Maximum size: {max_mb:.0f}MB"
                        }
                    )

            except ValueError:
                # Invalid Content-Length header
                logger.warning(f"Invalid Content-Length header: {content_length}")

        return await call_next(request)
