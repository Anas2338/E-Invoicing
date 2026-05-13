"""fix invoice settings column types

Revision ID: 20260509_fix_invoice_types
Revises: 20260509_increase_lengths
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260509_fix_invoice_types'
down_revision = '20260509_increase_lengths'
branch_labels = None
depends_on = None


def upgrade():
    """Change invoice settings from String to proper types"""
    # Convert invoice_start_number from VARCHAR to INTEGER
    op.alter_column('users', 'invoice_start_number',
                    type_=sa.Integer(),
                    existing_type=sa.String(),
                    existing_nullable=True,
                    postgresql_using='invoice_start_number::integer')

    # Convert invoice_padding from VARCHAR to INTEGER
    op.alter_column('users', 'invoice_padding',
                    type_=sa.Integer(),
                    existing_type=sa.String(),
                    existing_nullable=True,
                    postgresql_using='invoice_padding::integer')

    # Convert invoice_include_year from VARCHAR to BOOLEAN
    op.alter_column('users', 'invoice_include_year',
                    type_=sa.Boolean(),
                    existing_type=sa.String(),
                    existing_nullable=True,
                    postgresql_using="invoice_include_year::boolean")


def downgrade():
    """Revert invoice settings back to VARCHAR"""
    # Revert invoice_start_number from INTEGER to VARCHAR
    op.alter_column('users', 'invoice_start_number',
                    type_=sa.String(),
                    existing_type=sa.Integer(),
                    existing_nullable=True)

    # Revert invoice_padding from INTEGER to VARCHAR
    op.alter_column('users', 'invoice_padding',
                    type_=sa.String(),
                    existing_type=sa.Integer(),
                    existing_nullable=True)

    # Revert invoice_include_year from BOOLEAN to VARCHAR
    op.alter_column('users', 'invoice_include_year',
                    type_=sa.String(),
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
