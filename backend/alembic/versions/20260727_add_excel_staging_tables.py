"""Add excel_staging_session and excel_staging_row tables

Revision ID: 20260727_add_excel_staging
Revises: 20260725_merge_bulk_op
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = '20260727_add_excel_staging'
down_revision: Union[str, Sequence[str], None] = '20260725_merge_bulk_op'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create excel_staging_session and excel_staging_row tables."""

    # --- excel_staging_session ---
    op.create_table(
        'excel_staging_session',
        sa.Column('id', UUID, nullable=False),
        sa.Column('user_id', UUID, nullable=False, index=True),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=False,
                  server_default='parsing', index=True),
        sa.Column('total_rows', sa.Integer, nullable=False, server_default='0'),
        sa.Column('valid_rows', sa.Integer, nullable=False, server_default='0'),
        sa.Column('errored_rows', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_excel_staging_session_user_id',
        'excel_staging_session',
        ['user_id'],
    )

    # --- excel_staging_row ---
    op.create_table(
        'excel_staging_row',
        sa.Column('id', UUID, nullable=False),
        sa.Column('session_id', UUID, nullable=False, index=True),
        sa.Column('user_id', UUID, nullable=False, index=True),
        sa.Column('excel_row_number', sa.Integer, nullable=False),
        sa.Column('group_key', sa.String(100), nullable=False, server_default=''),
        sa.Column('is_valid', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('is_dirty', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('field_errors', JSON, nullable=False, server_default='{}'),
        # --- 16 template columns ---
        sa.Column('invoice_number', sa.String(50), nullable=False),
        sa.Column('invoice_type', sa.String(50), nullable=False,
                  server_default='Sale Invoice'),
        sa.Column('invoice_date', sa.String(20), nullable=False),
        sa.Column('buyer_ntn_cnic', sa.String(30), nullable=True, server_default=''),
        sa.Column('buyer_business_name', sa.String(255), nullable=False),
        sa.Column('buyer_province', sa.String(50), nullable=False),
        sa.Column('buyer_address', sa.String(500), nullable=False),
        sa.Column('buyer_registration_type', sa.String(20), nullable=False,
                  server_default='Registered'),
        sa.Column('saved_item_code', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('value_sales_excluding_st', sa.Numeric(14, 2), nullable=False),
        sa.Column('fixed_notified_value_or_retail_price',
                  sa.Numeric(14, 2), nullable=False),
        sa.Column('further_tax', sa.Numeric(12, 2), nullable=True),
        sa.Column('discount', sa.Numeric(12, 2), nullable=True),
        sa.Column('income_tax', sa.String(10), nullable=True,
                  server_default='236G'),
        sa.Column('withholding_tax_amount', sa.Numeric(12, 2), nullable=True),
        # --- Computed fields ---
        sa.Column('product_description', sa.String(500), nullable=True),
        sa.Column('hs_code', sa.String(50), nullable=True),
        sa.Column('rate', sa.String(10), nullable=True),
        sa.Column('uom', sa.String(50), nullable=True),
        sa.Column('sale_type', sa.String(100), nullable=True),
        sa.Column('transaction_type_id', sa.String(100), nullable=True),
        sa.Column('total_values', sa.Numeric(14, 2), nullable=True),
        sa.Column('sales_tax_applicable', sa.Numeric(14, 2), nullable=True),
        sa.Column('sales_tax_withheld_at_source',
                  sa.Numeric(12, 2), nullable=True),
        sa.Column('extra_tax', sa.Numeric(12, 2), nullable=True),
        sa.Column('fed_payable', sa.Numeric(12, 2), nullable=True),
        sa.Column('sro_schedule_no', sa.String(50), nullable=True),
        sa.Column('sro_item_serial_no', sa.String(50), nullable=True),
        sa.Column('item_rate', sa.Numeric(12, 2), nullable=True),
        # --- Seller fields ---
        sa.Column('seller_ntn_cnic', sa.String(30), nullable=True),
        sa.Column('seller_business_name', sa.String(255), nullable=True),
        sa.Column('seller_province', sa.String(50), nullable=True),
        sa.Column('seller_address', sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_excel_staging_row_session_id',
        'excel_staging_row',
        ['session_id'],
    )
    op.create_index(
        'ix_excel_staging_row_user_id',
        'excel_staging_row',
        ['user_id'],
    )


def downgrade() -> None:
    """Drop excel_staging_session and excel_staging_row tables."""

    op.drop_index('ix_excel_staging_row_user_id', 'excel_staging_row')
    op.drop_index('ix_excel_staging_row_session_id', 'excel_staging_row')
    op.drop_table('excel_staging_row')

    op.drop_index('ix_excel_staging_session_user_id', 'excel_staging_session')
    op.drop_table('excel_staging_session')
