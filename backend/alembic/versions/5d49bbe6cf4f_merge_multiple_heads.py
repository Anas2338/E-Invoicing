"""merge_multiple_heads

Revision ID: 5d49bbe6cf4f
Revises: 20260509_remove_cols, 20260509_remove_tables, 3612d6d131aa
Create Date: 2026-05-09 11:54:07.389470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d49bbe6cf4f'
down_revision: Union[str, Sequence[str], None] = ('20260509_remove_cols', '20260509_remove_tables', '3612d6d131aa')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
