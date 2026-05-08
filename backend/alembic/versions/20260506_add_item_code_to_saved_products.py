"""add item_code to saved_products

Revision ID: 20260506_add_item_code
Revises:
Create Date: 2026-05-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260506_add_item_code'
down_revision = None  # Will be set by alembic
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add item_code column to user_saved_products table
    # Use a default value for existing rows, then make it NOT NULL
    op.add_column('user_saved_products',
        sa.Column('item_code', sa.String(length=50), nullable=True)
    )

    # Update existing rows with a default item_code based on item_name or id
    op.execute("""
        UPDATE user_saved_products
        SET item_code = CONCAT('ITEM-', id)
        WHERE item_code IS NULL
    """)

    # Now make the column NOT NULL
    op.alter_column('user_saved_products', 'item_code',
        existing_type=sa.String(length=50),
        nullable=False
    )


def downgrade() -> None:
    # Remove item_code column
    op.drop_column('user_saved_products', 'item_code')
