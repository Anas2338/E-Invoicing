"""add_seller_province_address_to_users

Revision ID: 5b3d9784d2a8
Revises: 07111a39d6db
Create Date: 2026-02-14 16:05:17.726538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b3d9784d2a8'
down_revision: Union[str, Sequence[str], None] = '07111a39d6db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add fbr_seller_province and fbr_seller_address columns to users table
    op.add_column('users', sa.Column('fbr_seller_province', sa.String(), nullable=True))
    op.add_column('users', sa.Column('fbr_seller_address', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove fbr_seller_province and fbr_seller_address columns from users table
    op.drop_column('users', 'fbr_seller_address')
    op.drop_column('users', 'fbr_seller_province')
