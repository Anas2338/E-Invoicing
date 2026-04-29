"""add automation_enabled field to users

Revision ID: 20260424_002816
Revises: ac863f48f1f9
Create Date: 2026-04-24 00:28:16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260424_002816'
down_revision = 'ac863f48f1f9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add automation_enabled column to users table."""
    # Add automation_enabled column with default False
    op.add_column('users', sa.Column('automation_enabled', sa.Boolean(), nullable=True))

    # Set default value for existing users
    op.execute('UPDATE users SET automation_enabled = FALSE WHERE automation_enabled IS NULL')

    # Make column non-nullable after setting defaults
    op.alter_column('users', 'automation_enabled', nullable=False, server_default='false')


def downgrade() -> None:
    """Remove automation_enabled column from users table."""
    op.drop_column('users', 'automation_enabled')
