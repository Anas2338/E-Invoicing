"""Merge migration heads and add bulk_operation_task table

Revision ID: 20260725_merge_bulk_op
Revises: 20260620_drop_hs_uom_fk, a1b2c3d4e5f8, add_audit_idempotency
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID


# revision identifiers, used by Alembic.
revision: str = '20260725_merge_bulk_op'
down_revision: Union[str, Sequence[str], None] = (
    '20260620_drop_hs_uom_fk',
    'a1b2c3d4e5f8',
    'add_audit_idempotency',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create bulk_operation_task table for tracking background operations."""

    op.create_table(
        'bulk_operation_task',
        sa.Column('id', UUID, nullable=False),
        sa.Column('user_id', UUID, nullable=False, index=True),
        sa.Column('operation_type', sa.String(20), nullable=False),
        sa.Column('invoice_ids', JSON, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='processing'),
        sa.Column('total_count', sa.Integer, nullable=False),
        sa.Column('processed_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('errors', JSON, nullable=False, server_default='[]'),
        sa.Column('environment', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_bulk_operation_task_user_id',
        'bulk_operation_task',
        ['user_id'],
    )


def downgrade() -> None:
    """Drop bulk_operation_task table."""

    op.drop_index('ix_bulk_operation_task_user_id', 'bulk_operation_task')
    op.drop_table('bulk_operation_task')
