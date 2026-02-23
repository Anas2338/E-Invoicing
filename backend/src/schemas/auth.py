"""
Authentication schemas for JWT tokens and auth-related requests/responses.
"""
from typing import Optional
from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    sub: str = Field(..., description="User ID (subject)")
    production_access: bool = Field(default=False, description="Whether user has production access")
    exp: Optional[int] = Field(None, description="Token expiration timestamp")
    iat: Optional[int] = Field(None, description="Token issued at timestamp")


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: str
    production_access: bool = False


class AuthUser(BaseModel):
    """Authenticated user information."""
    user_id: str
    production_access: bool = False
