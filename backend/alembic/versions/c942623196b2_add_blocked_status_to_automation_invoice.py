"""add_blocked_status_to_automation_invoice

Revision ID: c942623196b2
Revises: a1b2c3d4e5f6
Create Date: 2026-04-11 17:51:55.569813

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c942623196b2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add 'blocked' status to automation_invoice status enum."""
    # Add 'blocked' value to the automationinvoicestatus enum
    # PostgreSQL requires ALTER TYPE ... ADD VALUE
    op.execute("ALTER TYPE automationinvoicestatus ADD VALUE IF NOT EXISTS 'blocked'")


def downgrade() -> None:
    """Downgrade schema - Remove 'blocked' status.

    Note: PostgreSQL does not support removing enum values directly.
    If you need to downgrade, you would need to:
    1. Create a new enum without 'blocked'
    2. Alter the column to use the new enum
    3. Drop the old enum

    This is complex and risky if data exists, so we leave it as a no-op.
    """
    pass

