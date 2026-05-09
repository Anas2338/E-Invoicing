"""remove unnecessary saved product columns

Revision ID: 20260509_remove_cols
Revises:
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260509_remove_cols'
down_revision = None  # Will be set to the latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Remove unnecessary columns from user_saved_products table"""
    # Remove default_unit_price column
    op.drop_column('user_saved_products', 'default_unit_price')

    # Remove display_order column
    op.drop_column('user_saved_products', 'display_order')

    # Remove fbr_validation_date column
    op.drop_column('user_saved_products', 'fbr_validation_date')

    # Remove fbr_validation_error column
    op.drop_column('user_saved_products', 'fbr_validation_error')


def downgrade():
    """Restore the removed columns"""
    # Restore fbr_validation_error
    op.add_column('user_saved_products',
                  sa.Column('fbr_validation_error', sa.String(), nullable=True))

    # Restore fbr_validation_date
    op.add_column('user_saved_products',
                  sa.Column('fbr_validation_date', sa.DateTime(), nullable=True))

    # Restore display_order
    op.add_column('user_saved_products',
                  sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'))

    # Restore default_unit_price
    op.add_column('user_saved_products',
                  sa.Column('default_unit_price', sa.Float(), nullable=True))
