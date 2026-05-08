"""merge_heads

Revision ID: c328752906b2
Revises: 20260506_add_item_code, 20260507_add_income_tax
Create Date: 2026-05-08 13:51:48.236389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c328752906b2'
down_revision: Union[str, Sequence[str], None] = ('20260506_add_item_code', '20260507_add_income_tax')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
