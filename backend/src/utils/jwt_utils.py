from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
import logging

from src.config.settings import settings


logger = logging.getLogger(__name__)


def create_access_token(data: Dict[str, Any], user_token_version: int = 0, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new access token with the provided data.

    Args:
        data: Dictionary containing the claims to include in the token
        user_token_version: User's current token version for session invalidation
        expires_delta: Optional timedelta for token expiration (defaults to 1 hour)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default to 1 hour if no expiration is provided
        expire = datetime.utcnow() + timedelta(hours=1)

    to_encode.update({
        "exp": expire,
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
        "token_version": user_token_version
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.auth_jwt_secret,
        algorithm="HS256"
    )

    return encoded_jwt


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary containing the token payload

    Raises:
        jose.exceptions.ExpiredSignatureError: If the token has expired
        jose.exceptions.JWTError: If the token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=["HS256"],
            issuer=settings.auth_issuer,
            audience=settings.auth_audience
        )
        return payload
    except ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise
    except JWTError:
        logger.warning("Invalid JWT token")
        raise
    except Exception as e:
        logger.error(f"Error decoding JWT token: {str(e)}")
        raise


def verify_token_expiration(token: str) -> bool:
    """
    Verify if a token is still valid (not expired).

    Args:
        token: JWT token string to check

    Returns:
        True if token is valid, False if expired
    """
    try:
        payload = decode_jwt_token(token)
        exp_time = datetime.utcfromtimestamp(payload.get("exp", 0))
        return datetime.utcnow() < exp_time
    except (ExpiredSignatureError, JWTError):
        return False


def extract_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from a JWT token.

    Args:
        token: JWT token string

    Returns:
        User ID string if found, None otherwise
    """
    try:
        payload = decode_jwt_token(token)
        return payload.get("sub")
    except (ExpiredSignatureError, JWTError):
        return None


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a refresh token with extended expiration.

    Args:
        data: Dictionary containing the claims to include in the token

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()

    # Refresh tokens typically last longer (e.g., 7 days)
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.auth_jwt_secret,
        algorithm="HS256"
    )

    return encoded_jwt