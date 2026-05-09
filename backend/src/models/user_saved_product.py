"""
Database model for user's saved products.
Allows users to save commonly used HS codes and product descriptions
for quick invoice creation.
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid

from .base import Base


class UserSavedProduct(Base, table=True):
    """User's saved product templates for quick invoice creation"""
    __tablename__ = "user_saved_products"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")

    # Product identification
    item_code: str = Field(max_length=50)  # User-defined code for the item (required)
    item_name: str = Field(max_length=255)  # User-friendly name for the item
    hs_code: str = Field(max_length=20)
    product_description: str

    # Default values for invoice items
    default_uom: Optional[str] = Field(default=None, max_length=10)
    default_rate: Optional[str] = Field(default=None, max_length=10)
    default_sale_type: Optional[str] = Field(default=None, max_length=10)
    transaction_type: Optional[str] = Field(default=None, max_length=10)  # Transaction type code

    # SRO fields (optional)
    sro_schedule_no: Optional[str] = Field(default=None, max_length=50)
    sro_item_serial_no: Optional[str] = Field(default=None, max_length=50)

    # FBR Validation
    fbr_validated: bool = Field(default=False)

    # Metadata
    is_active: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

