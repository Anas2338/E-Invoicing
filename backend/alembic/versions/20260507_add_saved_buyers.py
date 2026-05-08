"""Add user_saved_buyers table

Revision ID: 20260507_add_saved_buyers
Revises: 20260506_item_fields
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260507_add_saved_buyers'
down_revision = '20260506_item_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_saved_buyers table
    op.create_table(
        'user_saved_buyers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('buyer_ntn_cnic', sa.String(length=20), nullable=False),
        sa.Column('buyer_business_name', sa.String(length=255), nullable=False),
        sa.Column('buyer_province', sa.String(length=100), nullable=True),
        sa.Column('buyer_address', sa.String(length=500), nullable=True),
        sa.Column('buyer_registration_type', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('idx_user_saved_buyers_user_id', 'user_saved_buyers', ['user_id'])
    op.create_index('idx_user_saved_buyers_business_name', 'user_saved_buyers', ['buyer_business_name'])
    op.create_index('idx_user_saved_buyers_ntn_cnic', 'user_saved_buyers', ['buyer_ntn_cnic'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_user_saved_buyers_ntn_cnic', table_name='user_saved_buyers')
    op.drop_index('idx_user_saved_buyers_business_name', table_name='user_saved_buyers')
    op.drop_index('idx_user_saved_buyers_user_id', table_name='user_saved_buyers')

    # Drop table
    op.drop_table('user_saved_buyers')
