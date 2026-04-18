"""Add Phase 2 security fields

Revision ID: phase2_security_fields
Revises:
Create Date: 2026-04-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'phase2_security_fields'
down_revision = None  # Will be set based on current head
branch_labels = None
depends_on = None


def upgrade():
    # Add account lockout fields
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_failed_login_at', sa.DateTime(), nullable=True))

    # Add session invalidation field
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))

    # Add RBAC role field
    op.add_column('users', sa.Column('role', sa.String(), nullable=False, server_default='user'))


def downgrade():
    # Remove Phase 2 fields
    op.drop_column('users', 'role')
    op.drop_column('users', 'token_version')
    op.drop_column('users', 'last_failed_login_at')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
