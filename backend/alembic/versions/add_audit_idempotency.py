"""Add audit_log and idempotency_cache tables

Revision ID: add_audit_idempotency
Revises: 5b3d9784d2a8
Create Date: 2026-02-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = 'add_audit_idempotency'
down_revision = '5b3d9784d2a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_logs and idempotency_cache tables."""

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('environment', sa.String(), nullable=False),
        sa.Column('request_payload', JSON, nullable=True),
        sa.Column('response_payload', JSON, nullable=True),
        sa.Column('endpoint', sa.String(), nullable=True),
        sa.Column('method', sa.String(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('error_code', sa.String(), nullable=True),
        sa.Column('correlation_id', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for audit_logs
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_environment', 'audit_logs', ['environment'])
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'])
    op.create_index('ix_audit_logs_status_code', 'audit_logs', ['status_code'])
    op.create_index('ix_audit_logs_correlation_id', 'audit_logs', ['correlation_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # Create idempotency_cache table
    op.create_table(
        'idempotency_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('invoice_id', sa.String(), nullable=False),
        sa.Column('environment', sa.String(), nullable=False),
        sa.Column('response_payload', JSON, nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )

    # Create indexes for idempotency_cache
    op.create_index('ix_idempotency_cache_idempotency_key', 'idempotency_cache', ['idempotency_key'], unique=True)
    op.create_index('ix_idempotency_cache_user_id', 'idempotency_cache', ['user_id'])
    op.create_index('ix_idempotency_cache_invoice_id', 'idempotency_cache', ['invoice_id'])
    op.create_index('ix_idempotency_cache_created_at', 'idempotency_cache', ['created_at'])
    op.create_index('ix_idempotency_cache_expires_at', 'idempotency_cache', ['expires_at'])


def downgrade() -> None:
    """Drop audit_logs and idempotency_cache tables."""

    # Drop idempotency_cache indexes and table
    op.drop_index('ix_idempotency_cache_expires_at', 'idempotency_cache')
    op.drop_index('ix_idempotency_cache_created_at', 'idempotency_cache')
    op.drop_index('ix_idempotency_cache_invoice_id', 'idempotency_cache')
    op.drop_index('ix_idempotency_cache_user_id', 'idempotency_cache')
    op.drop_index('ix_idempotency_cache_idempotency_key', 'idempotency_cache')
    op.drop_table('idempotency_cache')

    # Drop audit_logs indexes and table
    op.drop_index('ix_audit_logs_created_at', 'audit_logs')
    op.drop_index('ix_audit_logs_correlation_id', 'audit_logs')
    op.drop_index('ix_audit_logs_status_code', 'audit_logs')
    op.drop_index('ix_audit_logs_resource_id', 'audit_logs')
    op.drop_index('ix_audit_logs_environment', 'audit_logs')
    op.drop_index('ix_audit_logs_action', 'audit_logs')
    op.drop_index('ix_audit_logs_user_id', 'audit_logs')
    op.drop_table('audit_logs')
