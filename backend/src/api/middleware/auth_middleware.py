from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from typing import Optional
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.config.settings import settings
from src.utils.jwt_utils import decode_jwt_token


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
        """
        # Extract token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # Allow unauthenticated requests to pass through
            # Individual endpoints should enforce authentication
            request.state.user_id = None
            request.state.current_user = None
        else:
            token = auth_header.split(" ")[1]

            try:
                # Verify JWT token locally
                payload = decode_jwt_token(token)

                # Extract user ID from the token
                user_id = payload.get("sub")
                if not user_id:
                    # Set user_id to None so endpoints can handle it
                    request.state.user_id = None
                    request.state.current_user = None
                else:
                    # Store user ID in request state for downstream handlers
                    request.state.user_id = user_id
                    request.state.current_user = None

                    # Also store other useful claims if needed
                    request.state.token_payload = payload

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