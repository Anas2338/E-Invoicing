"""
User Saved HS Codes Model
Stores HS codes that users have validated against FBR master data.
"""

from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserSavedHSCode(SQLModel, table=True):
    """
    Model for storing user's saved HS codes with FBR validation status.
    Users can save HS codes separately and use them when creating invoices.
    """
    __tablename__ = "user_saved_hs_codes"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    hs_code: str = Field(max_length=20, index=True)

    # FBR Validation fields
    fbr_validated: bool = Field(default=False)
    fbr_validation_date: Optional[datetime] = Field(default=None)
    fbr_validation_error: Optional[str] = Field(default=None)

    # Metadata
    is_active: int = Field(default=1)  # 1 = active, 0 = soft deleted
    display_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "hs_code": "5904.9000",
                "fbr_validated": True,
                "fbr_validation_date": "2024-01-15T10:30:00",
                "fbr_validation_error": None,
                "is_active": 1,
                "display_order": 0
            }
        }
