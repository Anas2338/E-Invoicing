"""
Request/response logging middleware for API monitoring and debugging.
"""
import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses.

    Logs request method, path, headers, body, response status, and duration.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", f"req-{int(time.time() * 1000)}")

        # Start timer
        start_time = time.time()

        # Log request
        await self._log_request(request, request_id)

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log response
        self._log_response(request, response, request_id, duration_ms)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    async def _log_request(self, request: Request, request_id: str):
        """
        Log incoming request details.

        Args:
            request: HTTP request
            request_id: Unique request identifier
        """
        # Extract relevant headers (exclude sensitive ones)
        headers = dict(request.headers)
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "***REDACTED***"

        # Try to read body for POST/PUT/PATCH requests
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body = body_bytes.decode("utf-8")
                    # Try to parse as JSON for better logging
                    try:
                        body = json.loads(body)
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                logger.warning(f"Failed to read request body: {e}")

        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": headers,
                "body": body,
                "client_host": request.client.host if request.client else None
            }
        )

    def _log_response(self, request: Request, response: Response, request_id: str, duration_ms: int):
        """
        Log outgoing response details.

        Args:
            request: HTTP request
            response: HTTP response
            request_id: Unique request identifier
            duration_ms: Request duration in milliseconds
        """
        logger.info(
            "Outgoing response",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms
            }
        )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding request context to all requests.

    Adds request ID and user context to request state for use in handlers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add request context and process request.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", f"req-{int(time.time() * 1000)}")

        # Add to request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
