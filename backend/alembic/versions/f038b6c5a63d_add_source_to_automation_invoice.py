"""add_source_to_automation_invoice

Revision ID: f038b6c5a63d
Revises: 5a391983efbf
Create Date: 2026-04-06 00:21:24.142508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f038b6c5a63d'
down_revision: Union[str, Sequence[str], None] = '5a391983efbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add source field to automation_invoice."""
    # Add source column to automation_invoice table
    op.add_column('automation_invoice',
                  sa.Column('source', sa.String(length=20),
                           server_default='excel_upload',
                           nullable=False))
    op.create_index(op.f('ix_automation_invoice_source'), 'automation_invoice', ['source'], unique=False)


def downgrade() -> None:
    """Downgrade schema: Remove source field from automation_invoice."""
    op.drop_index(op.f('ix_automation_invoice_source'), table_name='automation_invoice')
    op.drop_column('automation_invoice', 'source')
