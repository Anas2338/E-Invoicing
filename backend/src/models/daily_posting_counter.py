from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime as dt
from datetime import date as date_type
import uuid
from sqlalchemy import Column, Date, DateTime, Integer, UniqueConstraint, ForeignKey
from sqlalchemy.types import Uuid


class DailyPostingCounter(SQLModel, table=True):
    """
    Tracks daily posting counts per user for limit enforcement.

    Supports midnight-spanning windows by tracking window_start_date.
    """
    __tablename__ = "daily_posting_counters"
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_user_date'),
    )

    # Primary key
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(Uuid, primary_key=True)
    )

    # Foreign key
    user_id: uuid.UUID = Field(
        sa_column=Column(Uuid, ForeignKey('users.id'), nullable=False, index=True)
    )

    # Counter fields
    date: date_type = Field(
        sa_column=Column(Date, nullable=False, index=True),
        description="Calendar date for this counter (PKT timezone)"
    )
    posted_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
        description="Number of invoices posted on this date"
    )
    window_start_date: date_type = Field(
        sa_column=Column(Date, nullable=False),
        description="Date when posting window started (for midnight-spanning windows)"
    )

    # Timestamps
    created_at: dt = Field(
        default_factory=dt.utcnow,
        sa_column=Column(DateTime, default=dt.utcnow)
    )
    updated_at: dt = Field(
        default_factory=dt.utcnow,
        sa_column=Column(DateTime, default=dt.utcnow, onupdate=dt.utcnow)
    )
