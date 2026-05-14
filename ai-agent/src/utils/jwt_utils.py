"""JWT utility functions for AI-agent (decode only)."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
import logging

from src.config.settings import settings

logger = logging.getLogger(__name__)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token using the shared secret."""
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=["HS256"],
            issuer=settings.auth_issuer,
            audience=settings.auth_audience,
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


def extract_user_id_from_token(token: str) -> Optional[str]:
    try:
        payload = decode_jwt_token(token)
        return payload.get("sub")
    except (ExpiredSignatureError, JWTError):
        return None
