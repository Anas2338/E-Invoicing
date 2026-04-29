"""Initial automation database - transfer_log table

Revision ID: 001_initial
Revises:
Create Date: 2026-04-25 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create transfer_log table in automation database."""
    op.create_table(
        'transfer_log',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('transfer_timestamp', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('invoices_transferred', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('invoices_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('triggered_by', sa.String(), nullable=False, server_default='scheduled'),
        sa.Column('triggered_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('error_details', sa.String(), nullable=True),
        sa.Column('failed_invoice_ids', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create index for querying transfer logs
    op.create_index(
        'ix_transfer_log_timestamp',
        'transfer_log',
        ['transfer_timestamp'],
        unique=False
    )
    op.create_index(
        'ix_transfer_log_status',
        'transfer_log',
        ['status', 'transfer_timestamp'],
        unique=False
    )


def downgrade() -> None:
    """Drop transfer_log table."""
    op.drop_index('ix_transfer_log_status', table_name='transfer_log')
    op.drop_index('ix_transfer_log_timestamp', table_name='transfer_log')
    op.drop_table('transfer_log')
