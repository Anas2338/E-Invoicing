"""add transaction_type_id to invoices

Revision ID: add_transaction_type_id
Revises: 266bed74645b
Create Date: 2026-04-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_transaction_type_id'
down_revision = '266bed74645b'
branch_labels = None
depends_on = None


def upgrade():
    # Add transaction_type_id column to invoices table
    op.add_column('invoices', sa.Column('transaction_type_id', sa.String(), nullable=True))


def downgrade():
    # Remove transaction_type_id column from invoices table
    op.drop_column('invoices', 'transaction_type_id')
