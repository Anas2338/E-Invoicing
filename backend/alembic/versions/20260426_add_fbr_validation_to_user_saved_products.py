"""Add FBR validation fields to user_saved_products

Revision ID: 20260426_fbr_validation
Revises: user_saved_products_001
Create Date: 2026-04-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260426_fbr_validation'
down_revision = 'fefbaf5af115'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add FBR validation fields to user_saved_products table
    op.add_column('user_saved_products',
        sa.Column('fbr_validated', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('user_saved_products',
        sa.Column('fbr_validation_date', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('user_saved_products',
        sa.Column('fbr_validation_error', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    # Remove FBR validation fields from user_saved_products table
    op.drop_column('user_saved_products', 'fbr_validation_error')
    op.drop_column('user_saved_products', 'fbr_validation_date')
    op.drop_column('user_saved_products', 'fbr_validated')
