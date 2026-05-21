"""add reset pin fields to users

Revision ID: a1b2c3d4e5f8
Revises: ff92d41609c2
Create Date: 2026-05-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f8'
down_revision: Union[str, Sequence[str], None] = 'ff92d41609c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('reset_pin_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_pin_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'reset_pin_expires_at')
    op.drop_column('users', 'reset_pin_hash')
