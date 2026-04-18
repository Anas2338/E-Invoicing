"""add_user_approval_fields

Revision ID: a1b2c3d4e5f7
Revises: f038b6c5a63d
Create Date: 2026-04-13 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'f038b6c5a63d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add user approval fields."""
    # Add account_status column with default 'pending'
    op.add_column('users', sa.Column('account_status', sa.String(), nullable=False, server_default='pending'))

    # Add approved_by column (UUID of admin who approved)
    op.add_column('users', sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True))

    # Add approved_at timestamp
    op.add_column('users', sa.Column('approved_at', sa.DateTime(), nullable=True))

    # Add rejection_reason column
    op.add_column('users', sa.Column('rejection_reason', sa.String(), nullable=True))

    # Create index on account_status for faster queries
    op.create_index(op.f('ix_users_account_status'), 'users', ['account_status'], unique=False)

    # Update existing users to 'approved' status so they can continue using the system
    op.execute("UPDATE users SET account_status = 'approved' WHERE account_status = 'pending'")


def downgrade() -> None:
    """Downgrade schema: Remove user approval fields."""
    op.drop_index(op.f('ix_users_account_status'), table_name='users')
    op.drop_column('users', 'rejection_reason')
    op.drop_column('users', 'approved_at')
    op.drop_column('users', 'approved_by')
    op.drop_column('users', 'account_status')
