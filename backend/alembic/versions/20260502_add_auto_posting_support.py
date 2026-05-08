"""Add auto-posting support

Revision ID: 20260502_add_auto_posting
Revises: 20260428_remove_cross_database_foreign_keys
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = '20260502_add_auto_posting'
down_revision: Union[str, Sequence[str], None] = '20260428_remove_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add auto-posting support to users and invoices tables."""

    # 1. Add auto-posting columns to users table
    print("Adding auto-posting columns to users table...")
    op.add_column('users', sa.Column('auto_posting_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('auto_posting_start_time', sa.Time(), nullable=False, server_default='09:00:00'))
    op.add_column('users', sa.Column('auto_posting_end_time', sa.Time(), nullable=False, server_default='18:00:00'))
    op.add_column('users', sa.Column('auto_posting_environment', sa.String(20), nullable=False, server_default='SANDBOX'))
    op.add_column('users', sa.Column('auto_posting_daily_limit', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('users', sa.Column('auto_posting_paused_until', sa.DateTime(), nullable=True))

    # 2. Add FBR posting columns to invoices table
    print("Adding FBR posting columns to invoices table...")
    op.add_column('invoices', sa.Column('fbr_posted_at', sa.DateTime(), nullable=True))
    op.add_column('invoices', sa.Column('fbr_posting_error', sa.String(2000), nullable=True))
    op.add_column('invoices', sa.Column('fbr_retry_count', sa.Integer(), nullable=False, server_default='0'))

    # 3. Create daily_posting_counters table
    print("Creating daily_posting_counters table...")
    op.create_table(
        'daily_posting_counters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('posted_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('window_start_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_date')
    )

    # 4. Create posting_logs table
    print("Creating posting_logs table...")
    op.create_table(
        'posting_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('result', sa.String(20), nullable=False),
        sa.Column('environment', sa.String(20), nullable=False),
        sa.Column('error_details', postgresql.JSON(), nullable=True),
        sa.Column('agent_cycle_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )

    # 5. Create indexes for performance
    print("Creating indexes...")

    # Users table indexes
    op.create_index(
        'idx_users_auto_posting',
        'users',
        ['auto_posting_enabled'],
        postgresql_where=sa.text('auto_posting_enabled = true')
    )

    # Invoices table indexes
    op.create_index(
        'idx_invoices_fbr_posting',
        'invoices',
        ['user_id', 'status']
    )

    # Daily posting counters indexes
    op.create_index('idx_daily_counters_user_date', 'daily_posting_counters', ['user_id', 'date'])
    op.create_index('idx_daily_counters_date', 'daily_posting_counters', ['date'])

    # Posting logs indexes
    op.create_index('idx_posting_logs_user', 'posting_logs', ['user_id'])
    op.create_index('idx_posting_logs_invoice', 'posting_logs', ['invoice_id'])
    op.create_index('idx_posting_logs_created', 'posting_logs', ['created_at'])
    op.create_index(
        'idx_posting_logs_result',
        'posting_logs',
        ['result'],
        postgresql_where=sa.text("result = 'failure'")
    )

    print("Auto-posting migration completed successfully!")


def downgrade() -> None:
    """Remove auto-posting support."""

    # Drop indexes
    op.drop_index('idx_posting_logs_result', table_name='posting_logs')
    op.drop_index('idx_posting_logs_created', table_name='posting_logs')
    op.drop_index('idx_posting_logs_invoice', table_name='posting_logs')
    op.drop_index('idx_posting_logs_user', table_name='posting_logs')
    op.drop_index('idx_daily_counters_date', table_name='daily_posting_counters')
    op.drop_index('idx_daily_counters_user_date', table_name='daily_posting_counters')
    op.drop_index('idx_invoices_fbr_posting', table_name='invoices')
    op.drop_index('idx_users_auto_posting', table_name='users')

    # Drop tables
    op.drop_table('posting_logs')
    op.drop_table('daily_posting_counters')

    # Drop invoice columns
    op.drop_column('invoices', 'fbr_retry_count')
    op.drop_column('invoices', 'fbr_posting_error')
    op.drop_column('invoices', 'fbr_posted_at')

    # Drop user columns
    op.drop_column('users', 'auto_posting_paused_until')
    op.drop_column('users', 'auto_posting_daily_limit')
    op.drop_column('users', 'auto_posting_environment')
    op.drop_column('users', 'auto_posting_end_time')
    op.drop_column('users', 'auto_posting_start_time')
    op.drop_column('users', 'auto_posting_enabled')
