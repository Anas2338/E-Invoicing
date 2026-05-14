"""Request Size Limit Middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import status
import logging

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                content_length_int = int(content_length)
                if content_length_int > self.max_request_size:
                    size_mb = content_length_int / (1024 * 1024)
                    max_mb = self.max_request_size / (1024 * 1024)
                    logger.warning(f"Request too large: {size_mb:.2f}MB (max: {max_mb:.0f}MB)")
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": f"Request body too large. Maximum size: {max_mb:.0f}MB"},
                    )
            except ValueError:
                pass
        return await call_next(request)
