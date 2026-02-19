from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class UserBase(BaseModel):
    """
    Base schema for user.
    """
    email: str
    name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """
    Schema for creating users.
    """
    password: Optional[str] = None  # Password would typically be handled separately


class UserUpdate(BaseModel):
    """
    Schema for updating users.
    """
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    approval_flags: Optional[dict] = None


class UserResponse(UserBase):
    """
    Schema for user response.
    """
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    approval_flags: Optional[dict] = None


class UserLogin(BaseModel):
    """
    Schema for user login.
    """
    email: str
    password: str


class UserToken(BaseModel):
    """
    Schema for user token response.
    """
    access_token: str
    token_type: str
    user: UserResponse


class UserProfile(UserResponse):
    """
    Schema for user profile with additional access information.
    """
    has_production_access: bool = False
    can_post_to_production: bool = False

    # FBR Integration fields
    fbr_seller_ntn: Optional[str] = None
    fbr_business_name: Optional[str] = None
    fbr_seller_province: Optional[str] = None
    fbr_seller_address: Optional[str] = None