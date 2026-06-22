"""Drop FK constraint on fbr_user_hs_code_uom.user_id

Revision ID: 20260620_drop_hs_uom_fk
Revises: 20260620_add_hs_uom_tax
Create Date: 2026-06-20

The users table is on SQLModel's Base metadata, but fbr_user_hs_code_uom
is on FBRBase (separate schema). The FK constraint cannot be resolved
when FBRBase.metadata.create_all() runs at startup. We keep the column
and index, just without the database-level FK.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260620_drop_hs_uom_fk'
down_revision = '20260620_add_hs_uom_tax'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        'fbr_user_hs_code_uom_user_id_fkey',
        'fbr_user_hs_code_uom',
        type_='foreignkey'
    )


def downgrade() -> None:
    op.create_foreign_key(
        'fbr_user_hs_code_uom_user_id_fkey',
        'fbr_user_hs_code_uom',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
