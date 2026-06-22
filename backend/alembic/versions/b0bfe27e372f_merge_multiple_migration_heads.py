"""Merge multiple migration heads

Revision ID: b0bfe27e372f
Revises: 20260424_002816, a1b2c3d4e5f7, phase2_security_fields, user_saved_products_001
Create Date: 2026-04-25 14:46:46.490097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0bfe27e372f'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f7', 'c05b54c7bd14', 'phase2_security_fields', 'user_saved_products_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
