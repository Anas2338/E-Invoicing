"""add_is_deleted_to_invoices

Revision ID: 07111a39d6db
Revises: 9937d061521d
Create Date: 2026-02-14 15:52:40.574151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07111a39d6db'
down_revision: Union[str, Sequence[str], None] = '9937d061521d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_deleted column to invoices table
    op.add_column('invoices', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove is_deleted column from invoices table
    op.drop_column('invoices', 'is_deleted')
