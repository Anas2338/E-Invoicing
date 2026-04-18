from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from typing import Optional
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlmodel import Session

from src.config.settings import settings
from src.utils.jwt_utils import decode_jwt_token
from src.database.session import get_db


logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for JWT token verification.
    """
    def __init__(self, app):
        super().__init__(app)
        self.security = HTTPBearer(auto_error=False)

    async def dispatch(self, request: Request, call_next):
        """
        Process the incoming request and verify JWT token.
        Extracts user ID and stores it in request.state for downstream handlers.

        Token priority:
        1. Cookie (httpOnly) - preferred for security
        2. Authorization header - backward compatibility
        """
        token = None

        # First, try to get token from httpOnly cookie (preferred)
        token = request.cookies.get("access_token")

        # Fall back to Authorization header for backward compatibility
        if not token:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        # If no token found, allow unauthenticated request
        if not token:
            request.state.user_id = None
            request.state.current_user = None
        else:
            try:
                # Verify JWT token locally
                payload = decode_jwt_token(token)

                # Extract user ID from the token
                user_id = payload.get("sub")
                token_version = payload.get("token_version", 0)

                if not user_id:
                    # Set user_id to None so endpoints can handle it
                    request.state.user_id = None
                    request.state.current_user = None
                else:
                    # Verify token version matches user's current version
                    # This invalidates all tokens when password changes
                    from src.models.user import User
                    db_gen = get_db()
                    db = next(db_gen)
                    try:
                        user = db.get(User, user_id)
                        if user and user.token_version != token_version:
                            # Token version mismatch - token has been invalidated
                            logger.warning(f"Token version mismatch for user {user_id}")
                            request.state.user_id = None
                            request.state.current_user = None
                        else:
                            # Store user ID in request state for downstream handlers
                            request.state.user_id = user_id
                            request.state.current_user = None

                            # Also store other useful claims if needed
                            request.state.token_payload = payload
                    finally:
                        db.close()

            except JWTError as e:
                logger.warning(f"JWT verification failed: {str(e)}")
                # Set user_id to None instead of raising exception
                # Let the endpoint's require_authentication dependency handle it
                request.state.user_id = None
                request.state.current_user = None
            except Exception as e:
                logger.error(f"Unexpected error during authentication: {str(e)}")
                # Set user_id to None instead of raising exception
                request.state.user_id = None
                request.state.current_user = None

        response = await call_next(request)
        return response


# Helper function to verify user is authenticated
def require_authentication(request: Request):
    """
    Dependency to enforce that a user is authenticated.
    Should be used in route handlers that require authentication.
    """
    if not request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return request.state.user_id


# Helper function to verify user permissions for specific resources
def verify_user_owns_resource(user_id: str, resource_user_id: str):
    """
    Verify that the authenticated user owns the requested resource.
    Raises HTTPException if user doesn't have access.
    """
    if user_id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient permissions"
        )