"""add_user_saved_uoms_and_tax_rates_tables

Revision ID: 266bed74645b
Revises: 5f987947718f
Create Date: 2026-04-26 18:49:39.216043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '266bed74645b'
down_revision: Union[str, Sequence[str], None] = '5f987947718f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user_saved_uoms table
    op.create_table(
        'user_saved_uoms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('uom_code', sa.String(length=20), nullable=False),
        sa.Column('uom_name', sa.String(length=200), nullable=False),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_user_saved_uoms_user_id', 'user_saved_uoms', ['user_id'])
    op.create_index('ix_user_saved_uoms_uom_code', 'user_saved_uoms', ['uom_code'])

    # Create user_saved_tax_rates table
    op.create_table(
        'user_saved_tax_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('tax_rate', sa.String(length=10), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_user_saved_tax_rates_user_id', 'user_saved_tax_rates', ['user_id'])
    op.create_index('ix_user_saved_tax_rates_tax_rate', 'user_saved_tax_rates', ['tax_rate'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_user_saved_tax_rates_tax_rate', 'user_saved_tax_rates')
    op.drop_index('ix_user_saved_tax_rates_user_id', 'user_saved_tax_rates')
    op.drop_table('user_saved_tax_rates')

    op.drop_index('ix_user_saved_uoms_uom_code', 'user_saved_uoms')
    op.drop_index('ix_user_saved_uoms_user_id', 'user_saved_uoms')
    op.drop_table('user_saved_uoms')

