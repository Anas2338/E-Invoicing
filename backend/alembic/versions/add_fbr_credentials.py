"""Add FBR credentials fields to users table

Revision ID: add_fbr_credentials
Revises:
Create Date: 2025-02-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_fbr_credentials'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add FBR credentials columns to users table."""

    # Add FBR integration fields to users table
    op.add_column('users', sa.Column('fbr_access_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('fbr_environment', sa.String(), nullable=True, server_default='SANDBOX'))
    op.add_column('users', sa.Column('fbr_seller_ntn', sa.String(), nullable=True))
    op.add_column('users', sa.Column('fbr_business_name', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove FBR credentials columns from users table."""

    op.drop_column('users', 'fbr_business_name')
    op.drop_column('users', 'fbr_seller_ntn')
    op.drop_column('users', 'fbr_environment')
    op.drop_column('users', 'fbr_access_token')
