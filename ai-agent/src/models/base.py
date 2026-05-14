from sqlmodel import SQLModel
from typing import Any
from datetime import datetime
import uuid
from sqlalchemy import Column, DateTime
from sqlalchemy.types import Uuid


class Base(SQLModel):
    """
    Base model that all other models inherit from.
    Provides common fields like id, timestamps, etc.
    """
    id: uuid.UUID = Column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def dict(self, **kwargs) -> dict[str, Any]:
        """
        Override the default dict method to handle UUID serialization.
        """
        result = super().dict(**kwargs)
        if 'id' in result and isinstance(result['id'], uuid.UUID):
            result['id'] = str(result['id'])
        if 'created_at' in result and isinstance(result['created_at'], datetime):
            result['created_at'] = result['created_at'].isoformat()
        if 'updated_at' in result and isinstance(result['updated_at'], datetime):
            result['updated_at'] = result['updated_at'].isoformat()
        return result