"""add_reason_and_updated_at_to_automation_invoice

Revision ID: ac863f48f1f9
Revises: eb8c6704d50a
Create Date: 2026-04-12 15:52:16.721290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac863f48f1f9'
down_revision: Union[str, Sequence[str], None] = 'eb8c6704d50a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add reason and updated_at columns to automation_invoice."""
    # Add reason column (nullable, for storing block reason)
    op.add_column('automation_invoice', sa.Column('reason', sa.String(length=1000), nullable=True))

    # Add updated_at column (not nullable, with default)
    op.add_column('automation_invoice', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))


def downgrade() -> None:
    """Downgrade schema - Remove reason and updated_at columns."""
    op.drop_column('automation_invoice', 'updated_at')
    op.drop_column('automation_invoice', 'reason')
