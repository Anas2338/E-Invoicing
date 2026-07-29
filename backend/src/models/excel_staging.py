"""
Excel staging models for the async staging workflow.

Two-table design: ExcelStagingSession (parent) + ExcelStagingRow (child).
Staging rows are temporary — deleted after commit or cancel.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, JSON, Numeric, String
from sqlalchemy.types import Uuid
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------


class ExcelStagingStatus(str, Enum):
    """Current state of a staging session."""
    PARSING = "parsing"
    READY_FOR_REVIEW = "ready_for_review"
    RECHECKING = "rechecking"
    COMMITTING = "committing"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# ExcelStagingSession
# ---------------------------------------------------------------------------


class ExcelStagingSession(SQLModel, table=True):
    """
    Represents one file upload that is in progress.
    Parent row for all staging rows.
    Deleted after successful commit or cancel.
    """
    __tablename__ = "excel_staging_session"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(Uuid, primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(Uuid, nullable=False, index=True),
    )
    original_filename: str = Field(
        sa_column=Column(String(255), nullable=False),
    )
    status: str = Field(
        default="parsing",
        sa_column=Column(
            String(20),
            nullable=False,
            server_default="parsing",
            index=True,
        ),
    )
    total_rows: int = Field(default=0)
    valid_rows: int = Field(default=0)
    errored_rows: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )

    def __repr__(self) -> str:
        return (
            f"<ExcelStagingSession id={self.id} "
            f"filename='{self.original_filename}' "
            f"status='{self.status}' "
            f"rows={self.total_rows}>"
        )


# ---------------------------------------------------------------------------
# ExcelStagingRow
# ---------------------------------------------------------------------------


class ExcelStagingRow(SQLModel, table=True):
    """
    One row from the uploaded Excel file.
    Belongs to exactly one staging session.
    Deleted after commit or cancel.
    """
    __tablename__ = "excel_staging_row"

    # --- Identity & ownership ---
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(Uuid, primary_key=True),
    )
    session_id: uuid.UUID = Field(
        sa_column=Column(Uuid, nullable=False, index=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(Uuid, nullable=False, index=True),
    )

    # --- Parse metadata ---
    excel_row_number: int = Field(default=0)
    group_key: str = Field(
        default="",
        sa_column=Column(String(100), nullable=False, server_default=""),
    )

    # --- Validation state ---
    is_valid: bool = Field(default=True)
    is_dirty: bool = Field(default=False)
    field_errors: dict = Field(
        default={},
        sa_column=Column(JSON, default={}),
    )

    # --- 16 template columns (from Excel) ---
    invoice_number: str = Field(default="")
    invoice_type: str = Field(default="Sale Invoice", sa_column=Column(String(50), nullable=False, server_default="Sale Invoice"))
    invoice_date: str = Field(default="", sa_column=Column(String(20), nullable=False))
    buyer_ntn_cnic: str = Field(default="", sa_column=Column(String(30), nullable=True, server_default=""))
    buyer_business_name: str = Field(default="", sa_column=Column(String(255), nullable=False))
    buyer_province: str = Field(default="", sa_column=Column(String(50), nullable=False))
    buyer_address: str = Field(default="", sa_column=Column(String(500), nullable=False))
    buyer_registration_type: str = Field(default="Registered", sa_column=Column(String(20), nullable=False, server_default="Registered"))
    saved_item_code: str = Field(default="", sa_column=Column(String(50), nullable=False))
    quantity: float = Field(default=0.0)
    value_sales_excluding_st: float = Field(default=0.0)
    fixed_notified_value_or_retail_price: float = Field(default=0.0)
    further_tax: float = Field(default=0.0)
    discount: float = Field(default=0.0)
    income_tax: str = Field(default="236G")
    withholding_tax_amount: Optional[float] = Field(default=None)

    # --- Computed fields (resolved from saved item) ---
    product_description: Optional[str] = Field(default=None, sa_column=Column(String(500), nullable=True))
    hs_code: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True))
    rate: Optional[str] = Field(default=None, sa_column=Column(String(10), nullable=True))
    uom: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True))
    sale_type: Optional[str] = Field(default=None, sa_column=Column(String(100), nullable=True))
    transaction_type_id: Optional[str] = Field(default=None, sa_column=Column(String(100), nullable=True))
    total_values: Optional[float] = Field(default=None)
    sales_tax_applicable: Optional[float] = Field(default=None)
    sales_tax_withheld_at_source: float = Field(default=0.0)
    extra_tax: float = Field(default=0.0)
    fed_payable: float = Field(default=0.0)
    sro_schedule_no: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True))
    sro_item_serial_no: Optional[str] = Field(default=None, sa_column=Column(String(50), nullable=True))
    item_rate: Optional[float] = Field(default=None)

    # --- Seller fields (captured from user profile at parse time) ---
    seller_ntn_cnic: str = Field(default="", sa_column=Column(String(30), nullable=True, server_default=""))
    seller_business_name: str = Field(default="", sa_column=Column(String(255), nullable=True, server_default=""))
    seller_province: str = Field(default="", sa_column=Column(String(50), nullable=True, server_default=""))
    seller_address: str = Field(default="", sa_column=Column(String(500), nullable=True, server_default=""))

    def __repr__(self) -> str:
        return (
            f"<ExcelStagingRow id={self.id} "
            f"session_id={self.session_id} "
            f"row={self.excel_row_number} "
            f"inv='{self.invoice_number}' "
            f"valid={self.is_valid}>"
        )
