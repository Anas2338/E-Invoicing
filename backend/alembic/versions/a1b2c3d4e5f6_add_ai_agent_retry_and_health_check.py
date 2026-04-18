"""add_ai_agent_retry_and_health_check

Revision ID: a1b2c3d4e5f6
Revises: c05b54c7bd14
Create Date: 2026-04-10 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c05b54c7bd14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add AI Agent retry tracking and health check table."""

    # Add retry tracking fields to automation_invoice
    op.add_column('automation_invoice',
                  sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('automation_invoice',
                  sa.Column('last_retry_at', sa.DateTime(), nullable=True))
    op.add_column('automation_invoice',
                  sa.Column('priority', sa.Integer(), nullable=False, server_default='5'))

    # Add retry tracking index
    op.create_index(
        'idx_retry_tracking',
        'automation_invoice',
        ['status', 'last_retry_at', 'retry_count']
    )

    # Add priority processing index
    op.create_index(
        'idx_priority_processing',
        'automation_invoice',
        ['priority', 'scheduled_date', 'scheduled_time']
    )

    # Create ai_agent_health_check table
    op.create_table(
        'ai_agent_health_check',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('check_timestamp', sa.DateTime(), nullable=False),
        sa.Column('overall_status', sa.String(20), nullable=False),
        sa.Column('pending_invoice_count', sa.Integer(), nullable=False),
        sa.Column('failed_invoice_count', sa.Integer(), nullable=False),
        sa.Column('processing_backlog', sa.Integer(), nullable=False),
        sa.Column('failure_patterns', postgresql.JSON(), nullable=False),
        sa.Column('common_errors', postgresql.JSON(), nullable=False),
        sa.Column('fbr_api_status', sa.String(50), nullable=False),
        sa.Column('fbr_api_latency_ms', sa.Integer(), nullable=True),
        sa.Column('database_status', sa.String(50), nullable=False),
        sa.Column('database_latency_ms', sa.Integer(), nullable=True),
        sa.Column('agent_cpu_percent', sa.Float(), nullable=True),
        sa.Column('agent_memory_mb', sa.Integer(), nullable=True),
        sa.Column('anomalies_detected', postgresql.JSON(), nullable=False),
        sa.Column('recommended_actions', postgresql.JSON(), nullable=False),
        sa.Column('agent_version', sa.String(50), nullable=False),
        sa.Column('agent_uptime_seconds', sa.Integer(), nullable=False),
    )

    # Create indexes for ai_agent_health_check
    op.create_index(
        'idx_health_check_timestamp',
        'ai_agent_health_check',
        ['check_timestamp'],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_health_check_status',
        'ai_agent_health_check',
        ['overall_status', 'check_timestamp'],
        postgresql_using='btree'
    )


def downgrade() -> None:
    """Downgrade schema: Remove AI Agent retry tracking and health check table."""

    # Drop ai_agent_health_check table and indexes
    op.drop_index('idx_health_check_status', table_name='ai_agent_health_check')
    op.drop_index('idx_health_check_timestamp', table_name='ai_agent_health_check')
    op.drop_table('ai_agent_health_check')

    # Drop retry tracking indexes from automation_invoice
    op.drop_index('idx_priority_processing', table_name='automation_invoice')
    op.drop_index('idx_retry_tracking', table_name='automation_invoice')

    # Drop retry tracking columns from automation_invoice
    op.drop_column('automation_invoice', 'priority')
    op.drop_column('automation_invoice', 'last_retry_at')
    op.drop_column('automation_invoice', 'retry_count')
