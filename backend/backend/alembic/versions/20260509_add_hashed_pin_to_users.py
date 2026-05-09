"""Add hashed_pin column to users table

Revision ID: 20260509_add_hashed_pin
Revises: 3612d6d131aa
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260509_add_hashed_pin'
down_revision = '3612d6d131aa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add hashed_pin column to users table (nullable for existing users)
    op.add_column('users', sa.Column('hashed_pin', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove hashed_pin column from users table
    op.drop_column('users', 'hashed_pin')
