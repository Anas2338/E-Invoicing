"""Add item fields to user_saved_products

Revision ID: 20260506_item_fields
Revises: 20260502_add_auto_posting_support
Create Date: 2026-05-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260506_item_fields'
down_revision = '20260502_add_auto_posting'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new fields to user_saved_products table
    op.add_column('user_saved_products',
        sa.Column('item_name', sa.String(length=255), nullable=False, server_default='')
    )
    op.add_column('user_saved_products',
        sa.Column('transaction_type', sa.String(length=10), nullable=True)
    )
    op.add_column('user_saved_products',
        sa.Column('sro_schedule_no', sa.String(length=50), nullable=True)
    )
    op.add_column('user_saved_products',
        sa.Column('sro_item_serial_no', sa.String(length=50), nullable=True)
    )


def downgrade() -> None:
    # Remove new fields from user_saved_products table
    op.drop_column('user_saved_products', 'sro_item_serial_no')
    op.drop_column('user_saved_products', 'sro_schedule_no')
    op.drop_column('user_saved_products', 'transaction_type')
    op.drop_column('user_saved_products', 'item_name')
