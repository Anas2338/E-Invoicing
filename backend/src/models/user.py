from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
import uuid
from sqlalchemy import Column, DateTime, String, JSON, Enum as SQLEnum
from sqlalchemy.types import Uuid
from enum import Enum
from .base import Base

if TYPE_CHECKING:
    from .invoice import Invoice
    from .automation_invoice import AutomationInvoice
    from .excel_upload_session import ExcelUploadSession


class UserRole(str, Enum):
    """User role enumeration for RBAC."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class UserBase(SQLModel):
    """
    Base fields for User model.
    """
    email: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    name: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    role: str = Field(default=UserRole.USER.value, sa_column=Column(String, nullable=False))
    approval_flags: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Account approval fields
    account_status: str = Field(default="pending", sa_column=Column(String, nullable=False))  # pending, approved, rejected
    approved_by: Optional[uuid.UUID] = Field(default=None, sa_column=Column(Uuid, nullable=True))
    approved_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    rejection_reason: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))

    # Account lockout fields
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    last_login_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    last_failed_login_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))

    # Session invalidation field
    token_version: int = Field(default=0)

    # FBR Integration fields
    fbr_access_token: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))  # Deprecated, kept for backward compatibility
    fbr_sandbox_token: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    fbr_production_token: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    fbr_environment: Optional[str] = Field(default="SANDBOX", sa_column=Column(String, nullable=True))
    fbr_seller_ntn: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    fbr_business_name: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    fbr_seller_province: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    fbr_seller_address: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))


class User(UserBase, Base, table=True):
    """
    User model representing a registered portal user.
    """
    __tablename__ = "users"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Additional fields for the table
    email: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    hashed_password: str = Field(sa_column=Column(String, nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Password reset fields
    reset_token: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    reset_token_expires: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))

    # Relationships
    invoices: list["Invoice"] = Relationship(back_populates="user")
    automation_invoices: list["AutomationInvoice"] = Relationship(back_populates="user")
    excel_upload_sessions: list["ExcelUploadSession"] = Relationship(back_populates="user")


# Model for creating new users
class UserCreate(UserBase):
    """
    Model for creating new users.
    """
    email: str
    password: Optional[str] = None  # Password would typically be handled separately


# Model for updating users
class UserUpdate(SQLModel):
    """
    Model for updating users.
    """
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    approval_flags: Optional[dict] = None

    # FBR Integration fields
    fbr_access_token: Optional[str] = None
    fbr_environment: Optional[str] = None
    fbr_seller_ntn: Optional[str] = None
    fbr_business_name: Optional[str] = None
    fbr_seller_province: Optional[str] = None
    fbr_seller_address: Optional[str] = None


# Model for user responses
class UserRead(UserBase):
    """
    Model for returning user data.
    """
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    # Exclude sensitive token from response
    fbr_access_token: Optional[str] = Field(default=None, exclude=True)


# Model for FBR credentials update
class FBRCredentialsUpdate(SQLModel):
    """
    Model for updating FBR credentials.
    """
    fbr_access_token: str
    fbr_environment: str = "SANDBOX"
    fbr_seller_ntn: Optional[str] = None
    fbr_business_name: Optional[str] = None