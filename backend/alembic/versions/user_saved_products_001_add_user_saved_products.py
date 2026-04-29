"""Add user saved products table

Revision ID: user_saved_products_001
Revises: fbr_notifications_001
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'user_saved_products_001'
down_revision = 'fbr_notifications_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user saved products table
    op.create_table(
        'user_saved_products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hs_code', sa.String(length=20), nullable=False),
        sa.Column('product_description', sa.Text(), nullable=False),
        sa.Column('default_uom', sa.String(length=10), nullable=True),
        sa.Column('default_rate', sa.String(length=10), nullable=True),
        sa.Column('default_sale_type', sa.String(length=10), nullable=True),
        sa.Column('default_unit_price', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_saved_products_user_id', 'user_saved_products', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_user_saved_products_user_id', table_name='user_saved_products')
    op.drop_table('user_saved_products')
