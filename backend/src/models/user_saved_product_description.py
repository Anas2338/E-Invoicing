"""
User Saved Product Descriptions Model
Stores product descriptions that users commonly use.
"""

from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserSavedProductDescription(SQLModel, table=True):
    """
    Model for storing user's saved product descriptions.
    Users can save product descriptions separately and pair them with HS codes when creating invoices.
    """
    __tablename__ = "user_saved_product_descriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    product_description: str = Field(max_length=500)

    # Metadata
    is_active: int = Field(default=1)  # 1 = active, 0 = soft deleted
    display_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "product_description": "Linoleum floor covering",
                "is_active": 1,
                "display_order": 0
            }
        }
