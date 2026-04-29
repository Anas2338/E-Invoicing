"""add_user_saved_hs_codes_and_descriptions_tables

Revision ID: 5f987947718f
Revises: 20260426_fbr_validation
Create Date: 2026-04-26 16:16:07.274235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '5f987947718f'
down_revision: Union[str, Sequence[str], None] = '20260426_fbr_validation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user_saved_hs_codes table
    op.create_table(
        'user_saved_hs_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('hs_code', sa.String(length=20), nullable=False),
        sa.Column('fbr_validated', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('fbr_validation_date', sa.DateTime(), nullable=True),
        sa.Column('fbr_validation_error', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_user_saved_hs_codes_user_id', 'user_saved_hs_codes', ['user_id'])
    op.create_index('ix_user_saved_hs_codes_hs_code', 'user_saved_hs_codes', ['hs_code'])

    # Create user_saved_product_descriptions table
    op.create_table(
        'user_saved_product_descriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('product_description', sa.String(length=500), nullable=False),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_user_saved_product_descriptions_user_id', 'user_saved_product_descriptions', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_user_saved_product_descriptions_user_id', 'user_saved_product_descriptions')
    op.drop_table('user_saved_product_descriptions')

    op.drop_index('ix_user_saved_hs_codes_hs_code', 'user_saved_hs_codes')
    op.drop_index('ix_user_saved_hs_codes_user_id', 'user_saved_hs_codes')
    op.drop_table('user_saved_hs_codes')
