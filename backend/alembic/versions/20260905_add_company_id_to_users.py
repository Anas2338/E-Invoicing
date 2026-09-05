"""Add company_id to users (and merge the two pre-existing heads)

Revision ID: 20260905_add_company_id_to_users
Revises: 20260727_add_excel_staging, 20260509_fix_invoice_types
Create Date: 2026-09-05

Semantics (specs/006-company-linked-accounts/data-model.md §1):
- company_id == id        -> company owner (or standalone single-member company)
- company_id == <other>   -> employee account linked to that owner
Backfill makes every existing account its own company, so current behavior
is unchanged for all existing customers.

Also merges the two heads left behind by 20260725_merge_bulk_op (it merged
only three of four heads, leaving 20260509_fix_invoice_types dangling).
Deploys run ``alembic upgrade head`` (deploy-vps.yml), which requires a
single head — this migration restores that.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20260905_add_company_id_to_users'
down_revision: Union[str, Sequence[str], None] = (
    '20260727_add_excel_staging',
    '20260509_fix_invoice_types',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable users.company_id + index, backfill every row to its own id."""
    op.add_column('users', sa.Column('company_id', UUID(), nullable=True))
    op.create_index('ix_users_company_id', 'users', ['company_id'])

    # Backfill: every existing account becomes a single-member company owner.
    # Idempotent-safe — rows already linked are never re-pointed.
    op.execute("UPDATE users SET company_id = id WHERE company_id IS NULL")


def downgrade() -> None:
    """Drop the company_id index and column."""
    op.drop_index('ix_users_company_id', table_name='users')
    op.drop_column('users', 'company_id')
