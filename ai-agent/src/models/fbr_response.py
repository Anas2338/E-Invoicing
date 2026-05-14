from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
import uuid
from enum import Enum
from sqlalchemy import Column, DateTime, String, JSON, Text
from sqlalchemy.types import Uuid
from .base import Base

if TYPE_CHECKING:
    from .invoice import Invoice


class Environment(str, Enum):
    """
    Enum for environments.
    """
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


class FBRResponseBase(SQLModel):
    """
    Base fields for FBR Response model.
    """
    request_payload: dict = Field(sa_column=Column(JSON, nullable=False))
    response_payload: dict = Field(sa_column=Column(JSON, nullable=False))
    endpoint: str = Field(sa_column=Column(String, nullable=False))
    method: str = Field(sa_column=Column(String, nullable=False))
    status_code: int = Field(nullable=False)
    timestamp: datetime = Field(sa_column=Column(DateTime, nullable=False))
    environment: Environment = Field(sa_column=Column(String, nullable=False))
    correlation_id: str = Field(sa_column=Column(String, index=True))
    processing_duration_ms: Optional[int] = Field(default=None)


class FBRResponse(FBRResponseBase, Base, table=True):
    """
    FBR Response model representing the complete audit trail of FBR API interactions.
    """
    __tablename__ = "fbr_responses"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Additional fields for the table
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    invoices: list["Invoice"] = Relationship(back_populates="fbr_response")


# Model for creating new FBR responses
class FBRResponseCreate(SQLModel):
    """
    Model for creating new FBR responses.
    """
    request_payload: dict
    response_payload: dict
    endpoint: str
    method: str
    status_code: int
    timestamp: datetime
    environment: Environment
    correlation_id: str
    processing_duration_ms: Optional[int] = None


# Model for FBR response responses
class FBRResponseRead(FBRResponseBase):
    """
    Model for returning FBR response data.
    """
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime