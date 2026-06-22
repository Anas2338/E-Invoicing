"""
Database models for FBR master data.
Stores reference data fetched from FBR APIs for offline access.
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Index, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
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


class FBRUserHSCodeUOM(FBRBase):
    """User-scoped cache of HS Code → UOM mappings fetched from FBR.

    Each user's cached data is isolated by user_id — User A cannot see
    User B's cached HS Code UOMs. Fetched on-demand using the user's
    own FBR token, not the admin system token.
    """
    __tablename__ = "fbr_user_hs_code_uom"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    hs_code = Column(String(20), nullable=False, index=True)
    uom_id = Column(String(10), nullable=False)
    uom_description = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'hs_code', 'uom_id', name='uq_user_hs_code_uom'),
        Index('idx_user_hs_code_uom_lookup', 'user_id', 'hs_code'),
    )


class FBRTaxRate(FBRBase):
    """System-wide cache of Tax Rates per Transaction Type fetched from FBR.

    Fetched by admin during Sync Now using the admin system sync token.
    Shared across ALL users — no user_id column. Mirrors how fbr_provinces,
    fbr_uom, fbr_hs_codes, etc. work (system-wide shared master data).
    """
    __tablename__ = "fbr_tax_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rate_id = Column(String(10), nullable=False)
    rate_desc = Column(String(500), nullable=False)
    rate_value = Column(String(10), nullable=False)
    transaction_type_code = Column(String(10), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('rate_id', 'transaction_type_code', name='uq_rate_trans_type'),
        Index('idx_tax_rate_trans_type', 'transaction_type_code'),
    )
