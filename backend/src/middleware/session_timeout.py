"""
Activity-Based Session Timeout Middleware

Implements sliding session expiration based on user activity.
Sessions expire after 30 minutes of inactivity.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import status
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to implement activity-based session timeout.

    SECURITY: Automatically expires sessions after period of inactivity
    to prevent unauthorized access via abandoned sessions.
    """

    def __init__(self, app, timeout_minutes: int = 30):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            timeout_minutes: Session timeout in minutes (default: 30)
        """
        super().__init__(app)
        self.timeout_seconds = timeout_minutes * 60

    async def dispatch(self, request: Request, call_next):
        """
        Process request and check session activity.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            Response from handler or 401 if session expired
        """
        # Only check authenticated requests
        access_token = request.cookies.get("access_token")

        if access_token:
            # Get last activity timestamp from cookie
            last_activity_str = request.cookies.get("last_activity")

            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    now = datetime.utcnow()

                    # Check if session has expired due to inactivity
                    if (now - last_activity).total_seconds() > self.timeout_seconds:
                        logger.info(
                            f"Session expired due to inactivity. "
                            f"Last activity: {last_activity}, Now: {now}"
                        )

                        # Clear session cookies
                        response = JSONResponse(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            content={
                                "detail": "Session expired due to inactivity. Please login again."
                            }
                        )
                        response.delete_cookie("access_token")
                        response.delete_cookie("refresh_token")
                        response.delete_cookie("csrf_token")
                        response.delete_cookie("last_activity")

                        return response

                except (ValueError, TypeError):
                    # Invalid timestamp format, continue without checking
                    pass

        # Process request
        response = await call_next(request)

        # Update last activity timestamp for authenticated requests
        if access_token and response.status_code < 400:
            # Detect HTTPS for cookie secure flag
            is_https = (
                request.url.scheme == "https" or
                request.headers.get("X-Forwarded-Proto") == "https"
            )
            response.set_cookie(
                key="last_activity",
                value=datetime.utcnow().isoformat(),
                httponly=True,
                secure=is_https,
                samesite="lax",
                max_age=self.timeout_seconds,
                path="/"
            )

        return response
