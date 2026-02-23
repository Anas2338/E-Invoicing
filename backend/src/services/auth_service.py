"""
Authentication service for JWT token validation and authorization checks.
"""
from typing import Optional
from jose import jwt, JWTError
from ..config.settings import settings
from ..schemas.auth import TokenPayload, TokenData


class AuthService:
    """Service for authentication and authorization operations."""

    @staticmethod
    def decode_token(token: str) -> Optional[TokenData]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.AUTH_JWT_SECRET,
                algorithms=[settings.AUTH_JWT_ALGORITHM]
            )

            user_id = payload.get("sub")
            if user_id is None:
                return None

            production_access = payload.get("production_access", False)

            return TokenData(
                user_id=user_id,
                production_access=production_access
            )
        except JWTError:
            return None

    @staticmethod
    def check_production_access(token_data: TokenData) -> bool:
        """
        Check if user has production access from JWT claims.

        Args:
            token_data: Decoded token data

        Returns:
            True if user has production access, False otherwise
        """
        return token_data.production_access

    @staticmethod
    def validate_production_request(token_data: TokenData, environment: str) -> tuple[bool, Optional[str]]:
        """
        Validate if user can make requests to the specified environment.

        Args:
            token_data: Decoded token data
            environment: Target environment (SANDBOX or PRODUCTION)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if environment.upper() == "PRODUCTION":
            if not token_data.production_access:
                return False, "User does not have production access. Please contact administrator."

        return True, None
