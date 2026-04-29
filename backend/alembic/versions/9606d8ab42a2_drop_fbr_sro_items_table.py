"""drop_fbr_sro_items_table

Revision ID: 9606d8ab42a2
Revises: add_invoice_settings
Create Date: 2026-04-27 17:07:01.034583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9606d8ab42a2'
down_revision: Union[str, Sequence[str], None] = 'add_invoice_settings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop fbr_sro_items table to free up database space."""
    op.drop_table('fbr_sro_items')


def downgrade() -> None:
    """Recreate fbr_sro_items table if needed."""
    op.create_table(
        'fbr_sro_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_fbr_sro_items_code', 'fbr_sro_items', ['code'])
