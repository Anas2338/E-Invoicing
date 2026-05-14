"""
Database models for FBR master data.
Stores reference data fetched from FBR APIs for offline access.
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

# Create a separate base for FBR models (not using the UUID-based Base)
FBRBase = declarative_base()


class FBRProvince(FBRBase):
    """FBR Province master data"""
    __tablename__ = "fbr_provinces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class FBRUOM(FBRBase):
    """FBR Unit of Measure master data"""
    __tablename__ = "fbr_uom"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class FBRHSCode(FBRBase):
    """FBR HS Code master data"""
    __tablename__ = "fbr_hs_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_hs_code_search', 'code', 'description'),
    )


class FBRTransactionType(FBRBase):
    """FBR Transaction Type master data"""
    __tablename__ = "fbr_transaction_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class FBRInvoiceType(FBRBase):
    """FBR Invoice Type master data"""
    __tablename__ = "fbr_invoice_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class FBRSROItem(FBRBase):
    """FBR SRO Item master data"""
    __tablename__ = "fbr_sro_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class FBRSyncLog(FBRBase):
    """Log of FBR master data sync operations"""
    __tablename__ = "fbr_sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(50), nullable=False)  # e.g., 'provinces', 'uom', 'hs_codes', 'all'
    status = Column(String(20), nullable=False)  # 'success', 'failed', 'partial'
    records_synced = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    __table_args__ = (
        Index('idx_sync_log_status', 'sync_type', 'status', 'started_at'),
    )
