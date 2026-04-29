"""add invoice numbering settings to users

Revision ID: add_invoice_settings
Revises: add_transaction_type_id
Create Date: 2026-04-27 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_invoice_settings'
down_revision = 'add_transaction_type_id'
branch_labels = None
depends_on = None


def upgrade():
    # Add invoice numbering settings columns to users table
    op.add_column('users', sa.Column('invoice_prefix', sa.String(length=20), nullable=True, server_default='INV-'))
    op.add_column('users', sa.Column('invoice_start_number', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('users', sa.Column('invoice_padding', sa.Integer(), nullable=True, server_default='4'))
    op.add_column('users', sa.Column('invoice_include_year', sa.Boolean(), nullable=True, server_default='false'))


def downgrade():
    # Remove invoice numbering settings columns from users table
    op.drop_column('users', 'invoice_include_year')
    op.drop_column('users', 'invoice_padding')
    op.drop_column('users', 'invoice_start_number')
    op.drop_column('users', 'invoice_prefix')
