"""increase saved products field lengths for storing names

Revision ID: 20260509_increase_lengths
Revises: ff92d41609c2
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260509_increase_lengths'
down_revision = 'ff92d41609c2'
branch_labels = None
depends_on = None


def upgrade():
    """Increase field lengths to store names instead of codes"""
    # Increase default_uom from VARCHAR(10) to VARCHAR(200)
    op.alter_column('user_saved_products', 'default_uom',
                    type_=sa.String(200),
                    existing_type=sa.String(10),
                    existing_nullable=True)

    # Increase default_sale_type from VARCHAR(10) to VARCHAR(200)
    op.alter_column('user_saved_products', 'default_sale_type',
                    type_=sa.String(200),
                    existing_type=sa.String(10),
                    existing_nullable=True)

    # Increase transaction_type from VARCHAR(10) to VARCHAR(200)
    op.alter_column('user_saved_products', 'transaction_type',
                    type_=sa.String(200),
                    existing_type=sa.String(10),
                    existing_nullable=True)


def downgrade():
    """Revert field lengths back to VARCHAR(10)"""
    # Revert default_uom from VARCHAR(200) to VARCHAR(10)
    op.alter_column('user_saved_products', 'default_uom',
                    type_=sa.String(10),
                    existing_type=sa.String(200),
                    existing_nullable=True)

    # Revert default_sale_type from VARCHAR(200) to VARCHAR(10)
    op.alter_column('user_saved_products', 'default_sale_type',
                    type_=sa.String(10),
                    existing_type=sa.String(200),
                    existing_nullable=True)

    # Revert transaction_type from VARCHAR(200) to VARCHAR(10)
    op.alter_column('user_saved_products', 'transaction_type',
                    type_=sa.String(10),
                    existing_type=sa.String(200),
                    existing_nullable=True)
