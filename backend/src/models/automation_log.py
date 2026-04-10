from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .automation_invoice import AutomationInvoice


class AutomationLogAction(str, Enum):
    """Action types for automation logs."""
    VALIDATE = "validate"
    SUBMIT = "submit"
    UPDATE_EXCEL = "update_excel"
    RETRY = "retry"


class AutomationLogStatus(str, Enum):
    """Status for automation log entries."""
    SUCCESS = "success"
    FAILURE = "failure"


class AutomationLog(SQLModel, table=True):
    """
    Model for automation activity logs.
    Provides complete audit trail for all automation operations.
    """
    __tablename__ = "automation_log"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign key
    automation_invoice_id: UUID = Field(
        foreign_key="automation_invoice.id",
        index=True
    )

    # Action details
    action: AutomationLogAction = Field(index=True)
    status: AutomationLogStatus

    # Action-specific details (JSON)
    details: dict = Field(sa_column=Column(JSON))

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationship
    automation_invoice: Optional["AutomationInvoice"] = Relationship(
        back_populates="automation_logs"
    )
