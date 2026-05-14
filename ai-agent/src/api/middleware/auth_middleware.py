"""Authentication middleware for AI-agent. JWT-only validation (no User table lookup)."""

from fastapi import Request, HTTPException, status
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from src.config.settings import settings
from src.utils.jwt_utils import decode_jwt_token

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for JWT token verification.
    Validates tokens cryptographically using the shared JWT secret.
    Does NOT query the User table (token_version check is deferred to main backend).
    """

    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get("access_token")

        if not token:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            request.state.user_id = None
            request.state.current_user = None
        else:
            try:
                payload = decode_jwt_token(token)
                user_id = payload.get("sub")
                if not user_id:
                    request.state.user_id = None
                    request.state.current_user = None
                else:
                    request.state.user_id = user_id
                    request.state.current_user = None
                    request.state.token_payload = payload
            except JWTError as e:
                logger.warning(f"JWT verification failed: {str(e)}")
                request.state.user_id = None
                request.state.current_user = None
            except Exception as e:
                logger.error(f"Unexpected error during authentication: {str(e)}")
                request.state.user_id = None
                request.state.current_user = None

        response = await call_next(request)
        return response


def require_authentication(request: Request):
    """Dependency to enforce that a user is authenticated."""
    if not request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return request.state.user_id


def verify_user_owns_resource(user_id: str, resource_user_id: str):
    if user_id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient permissions",
        )
