"""Add fbr_user_hs_code_uom and fbr_tax_rates tables

Revision ID: 20260620_add_hs_uom_tax
Revises: 20260509_increase_saved_products_field_lengths
Create Date: 2026-06-20

This migration adds two new tables:
1. fbr_user_hs_code_uom — User-scoped cache for HS Code → UOM mappings
2. fbr_tax_rates — System-wide tax rates per transaction type
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260620_add_hs_uom_tax'
down_revision = '9606d8ab42a2'
branch_labels = None
depends_on = ('20260509_fix_invoice_types',)


def upgrade() -> None:
    # ── Table 1: fbr_user_hs_code_uom ──────────────────────────────
    op.create_table(
        'fbr_user_hs_code_uom',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hs_code', sa.String(length=20), nullable=False),
        sa.Column('uom_id', sa.String(length=10), nullable=False),
        sa.Column('uom_description', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'hs_code', 'uom_id',
                           name='uq_user_hs_code_uom'),
    )
    op.create_index('idx_user_hs_code_uom_lookup', 'fbr_user_hs_code_uom',
                    ['user_id', 'hs_code'])

    # ── Table 2: fbr_tax_rates ─────────────────────────────────────
    op.create_table(
        'fbr_tax_rates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rate_id', sa.String(length=10), nullable=False),
        sa.Column('rate_desc', sa.String(length=500), nullable=False),
        sa.Column('rate_value', sa.String(length=10), nullable=False),
        sa.Column('transaction_type_code', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rate_id', 'transaction_type_code',
                           name='uq_rate_trans_type'),
    )
    op.create_index('idx_tax_rate_trans_type', 'fbr_tax_rates',
                    ['transaction_type_code'])


def downgrade() -> None:
    op.drop_index('idx_tax_rate_trans_type', table_name='fbr_tax_rates')
    op.drop_table('fbr_tax_rates')
    op.drop_index('idx_user_hs_code_uom_lookup', table_name='fbr_user_hs_code_uom')
    op.drop_table('fbr_user_hs_code_uom')
