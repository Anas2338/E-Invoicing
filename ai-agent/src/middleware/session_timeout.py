"""Activity-Based Session Timeout Middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import status
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout_minutes: int = 30):
        super().__init__(app)
        self.timeout_seconds = timeout_minutes * 60

    async def dispatch(self, request: Request, call_next):
        access_token = request.cookies.get("access_token")
        if access_token:
            last_activity_str = request.cookies.get("last_activity")
            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    now = datetime.utcnow()
                    if (now - last_activity).total_seconds() > self.timeout_seconds:
                        logger.info(f"Session expired due to inactivity.")
                        response = JSONResponse(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            content={"detail": "Session expired due to inactivity."},
                        )
                        response.delete_cookie("access_token")
                        response.delete_cookie("refresh_token")
                        response.delete_cookie("csrf_token")
                        response.delete_cookie("last_activity")
                        return response
                except (ValueError, TypeError):
                    pass

        response = await call_next(request)
        if access_token and response.status_code < 400:
            response.set_cookie(
                key="last_activity",
                value=datetime.utcnow().isoformat(),
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=self.timeout_seconds,
                path="/",
            )
        return response
