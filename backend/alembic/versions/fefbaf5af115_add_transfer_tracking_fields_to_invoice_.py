"""Add transfer tracking fields to Invoice model

Revision ID: fefbaf5af115
Revises: b0bfe27e372f
Create Date: 2026-04-25 14:48:57.717230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fefbaf5af115'
down_revision: Union[str, Sequence[str], None] = 'b0bfe27e372f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add transfer tracking fields to automation_invoice
    op.add_column('automation_invoice', sa.Column('transferred_at', sa.DateTime(), nullable=True))
    op.add_column('automation_invoice', sa.Column('transfer_error', sa.String(length=2000), nullable=True))

    # Add transfer tracking fields to invoices
    op.add_column('invoices', sa.Column('source', sa.String(), nullable=False, server_default='manual'))
    op.add_column('invoices', sa.Column('transferred_at', sa.DateTime(), nullable=True))
    op.add_column('invoices', sa.Column('automation_invoice_id', sa.Uuid(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove transfer tracking fields from invoices
    op.drop_column('invoices', 'automation_invoice_id')
    op.drop_column('invoices', 'transferred_at')
    op.drop_column('invoices', 'source')

    # Remove transfer tracking fields from automation_invoice
    op.drop_column('automation_invoice', 'transfer_error')
    op.drop_column('automation_invoice', 'transferred_at')
