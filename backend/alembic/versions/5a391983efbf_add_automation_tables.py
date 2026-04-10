"""Add automation tables

Revision ID: 5a391983efbf
Revises: add_audit_idempotency
Create Date: 2026-04-04 18:22:16.529060

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = '5a391983efbf'
down_revision: Union[str, Sequence[str], None] = 'add_audit_idempotency'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create excel_upload_session table
    op.create_table(
        'excel_upload_session',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('upload_timestamp', sa.DateTime(), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processing_status', sa.String(20), nullable=False, server_default='uploading'),
        sa.Column('error_message', sa.String(2000), nullable=True),
    )

    # Create indexes for excel_upload_session
    op.create_index('ix_excel_upload_session_user_id', 'excel_upload_session', ['user_id'])
    op.create_index('ix_excel_upload_session_processing_status', 'excel_upload_session', ['processing_status'])
    op.create_index('ix_excel_upload_session_upload_timestamp', 'excel_upload_session', ['upload_timestamp'])
    op.create_index(
        'idx_one_processing_per_user',
        'excel_upload_session',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text("processing_status = 'processing'")
    )
    op.create_index(
        'idx_user_sessions',
        'excel_upload_session',
        ['user_id', 'processing_status', 'upload_timestamp']
    )

    # Create automation_invoice table
    op.create_table(
        'automation_invoice',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('excel_upload_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('excel_upload_session.id'), nullable=False),
        sa.Column('invoice_number', sa.String(100), nullable=False),
        sa.Column('invoice_data', postgresql.JSON(), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('scheduled_time', sa.Time(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('validation_errors', sa.String(5000), nullable=True),
        sa.Column('fbr_response', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
    )

    # Create indexes for automation_invoice
    op.create_index('ix_automation_invoice_user_id', 'automation_invoice', ['user_id'])
    op.create_index('ix_automation_invoice_excel_upload_session_id', 'automation_invoice', ['excel_upload_session_id'])
    op.create_index('ix_automation_invoice_invoice_number', 'automation_invoice', ['invoice_number'])
    op.create_index('ix_automation_invoice_scheduled_date', 'automation_invoice', ['scheduled_date'])
    op.create_index('ix_automation_invoice_scheduled_time', 'automation_invoice', ['scheduled_time'])
    op.create_index('ix_automation_invoice_status', 'automation_invoice', ['status'])
    op.create_index(
        'idx_unique_invoice_per_user',
        'automation_invoice',
        ['user_id', 'invoice_number'],
        unique=True
    )
    op.create_index(
        'idx_pending_scheduled',
        'automation_invoice',
        ['status', 'scheduled_date', 'scheduled_time']
    )

    # Create automation_log table
    op.create_table(
        'automation_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('automation_invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('automation_invoice.id'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('details', postgresql.JSON(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
    )

    # Create indexes for automation_log
    op.create_index('ix_automation_log_automation_invoice_id', 'automation_log', ['automation_invoice_id'])
    op.create_index('ix_automation_log_action', 'automation_log', ['action'])
    op.create_index('ix_automation_log_timestamp', 'automation_log', ['timestamp'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('automation_log')
    op.drop_table('automation_invoice')
    op.drop_table('excel_upload_session')
