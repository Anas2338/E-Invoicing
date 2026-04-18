"""update_automation_log_for_file_management

Revision ID: eb8c6704d50a
Revises: c942623196b2
Create Date: 2026-04-12 00:59:31.650981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb8c6704d50a'
down_revision: Union[str, Sequence[str], None] = 'c942623196b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Update automation_log for file management features."""
    # Add new action types to automationlogaction enum
    op.execute("ALTER TYPE automationlogaction ADD VALUE IF NOT EXISTS 'block'")
    op.execute("ALTER TYPE automationlogaction ADD VALUE IF NOT EXISTS 'unblock'")
    op.execute("ALTER TYPE automationlogaction ADD VALUE IF NOT EXISTS 'delete'")
    op.execute("ALTER TYPE automationlogaction ADD VALUE IF NOT EXISTS 'delete_session'")

    # Make automation_invoice_id nullable (for session-level actions)
    op.alter_column('automation_log', 'automation_invoice_id',
                    existing_type=sa.UUID(),
                    nullable=True)

    # Make status nullable (for actions without success/failure)
    op.alter_column('automation_log', 'status',
                    existing_type=sa.Enum('SUCCESS', 'FAILURE', name='automationlogstatus'),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    pass
