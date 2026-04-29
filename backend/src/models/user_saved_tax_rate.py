"""
User Saved Tax Rate Model
Stores tax rates that users have manually entered.
"""

from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserSavedTaxRate(SQLModel, table=True):
    """
    Model for storing user's saved tax rates.
    Users can manually enter tax rates and use them when creating invoices.
    """
    __tablename__ = "user_saved_tax_rates"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    tax_rate: str = Field(max_length=10, index=True)  # e.g., "18", "24"
    description: Optional[str] = Field(default=None, max_length=200)  # Optional description like "Standard Rate", "Reduced Rate"

    # Metadata
    is_active: int = Field(default=1)  # 1 = active, 0 = soft deleted
    display_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "tax_rate": "18",
                "description": "Standard Rate",
                "is_active": 1,
                "display_order": 0
            }
        }
