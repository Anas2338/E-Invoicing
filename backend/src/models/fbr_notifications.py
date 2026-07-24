"""
Database models for FBR change notifications.
Tracks changes in FBR master data and displays them as a news feed.
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

# Use the same base as fbr_master_data (relative import within the models package)
from .fbr_master_data import FBRBase


class FBRChangeNotification(FBRBase):
    """FBR master data change notifications"""
    __tablename__ = "fbr_change_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Change details
    data_type = Column(String(50), nullable=False)  # 'provinces', 'uom', 'hs_codes', etc.
    change_type = Column(String(20), nullable=False)  # 'added', 'modified', 'deleted'

    # What changed
    record_code = Column(String(50), nullable=False)  # The code/ID of the changed record
    old_value = Column(JSON, nullable=True)  # Previous value (for modifications/deletions)
    new_value = Column(JSON, nullable=True)  # New value (for additions/modifications)

    # Human-readable summary
    summary = Column(Text, nullable=False)  # e.g., "New HS Code added: 1234.5678 - Description"

    # Metadata
    sync_log_id = Column(Integer, nullable=True)  # Reference to the sync that detected this change
    is_read = Column(Boolean, default=False, nullable=False)  # Track if user has seen this
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_notification_type_date', 'data_type', 'created_at'),
        Index('idx_notification_read', 'is_read', 'created_at'),
    )


class FBRDataSnapshot(FBRBase):
    """
    Stores hash/checksum of FBR data for change detection.
    Used to quickly detect if data has changed without comparing all records.
    """
    __tablename__ = "fbr_data_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_type = Column(String(50), nullable=False, unique=True)  # 'provinces', 'uom', etc.
    record_count = Column(Integer, nullable=False)
    data_hash = Column(String(64), nullable=False)  # SHA256 hash of all records
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
