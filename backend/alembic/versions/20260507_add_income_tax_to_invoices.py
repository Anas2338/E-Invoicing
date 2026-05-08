"""Add income_tax column to invoices

Revision ID: 20260507_add_income_tax
Revises: 20260507_add_saved_buyers
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260507_add_income_tax'
down_revision = '20260507_add_saved_buyers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add income_tax column to invoices table with default value
    op.add_column('invoices', sa.Column('income_tax', sa.String(), nullable=False, server_default='236G'))


def downgrade() -> None:
    # Remove income_tax column from invoices table
    op.drop_column('invoices', 'income_tax')
