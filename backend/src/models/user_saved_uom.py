"""
User Saved UOM Model
Stores UOMs that users have selected from FBR master data.
"""

from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserSavedUOM(SQLModel, table=True):
    """
    Model for storing user's saved UOMs selected from FBR master data.
    Users can select UOMs from FBR list and use them when creating invoices.
    """
    __tablename__ = "user_saved_uoms"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    uom_code: str = Field(max_length=20, index=True)
    uom_name: str = Field(max_length=200)

    # Metadata
    is_active: int = Field(default=1)  # 1 = active, 0 = soft deleted
    display_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "uom_code": "MTR",
                "uom_name": "Meter",
                "is_active": 1,
                "display_order": 0
            }
        }
