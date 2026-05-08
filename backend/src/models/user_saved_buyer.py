"""
User Saved Buyer model for storing frequently used buyer information.
Each user can save buyer details for quick auto-fill in invoice forms.
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid

from .base import Base


class UserSavedBuyer(Base, table=True):
    """
    Model for storing user's saved buyer information.
    Allows users to quickly fill buyer details in invoices by selecting from saved buyers.
    """
    __tablename__ = "user_saved_buyers"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")

    # Buyer information fields
    buyer_ntn_cnic: str = Field(max_length=20)
    buyer_business_name: str = Field(max_length=255, index=True)
    buyer_province: Optional[str] = Field(default=None, max_length=100)
    buyer_address: Optional[str] = Field(default=None, max_length=500)
    buyer_registration_type: Optional[str] = Field(default=None, max_length=20)  # 'Registered' or 'Unregistered'

    # Metadata
    is_active: int = Field(default=1)  # 1 = active, 0 = soft deleted
    display_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def __repr__(self):
        return f"<UserSavedBuyer(id={self.id}, user_id={self.user_id}, business_name='{self.buyer_business_name}')>"
