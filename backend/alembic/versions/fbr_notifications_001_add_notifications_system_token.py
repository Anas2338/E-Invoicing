"""Add FBR notifications and system token

Revision ID: fbr_notifications_001
Revises: fbr_master_data_001
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fbr_notifications_001'
down_revision = 'fbr_master_data_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add fbr_system_sync_token to users table
    op.add_column('users', sa.Column('fbr_system_sync_token', sa.String(), nullable=True))

    # Create FBR change notifications table
    op.create_table(
        'fbr_change_notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('record_code', sa.String(length=50), nullable=False),
        sa.Column('old_value', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('sync_log_id', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notification_type_date', 'fbr_change_notifications', ['data_type', 'created_at'])
    op.create_index('idx_notification_read', 'fbr_change_notifications', ['is_read', 'created_at'])

    # Create FBR data snapshots table
    op.create_table(
        'fbr_data_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('record_count', sa.Integer(), nullable=False),
        sa.Column('data_hash', sa.String(length=64), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('data_type')
    )


def downgrade() -> None:
    op.drop_table('fbr_data_snapshots')

    op.drop_index('idx_notification_read', table_name='fbr_change_notifications')
    op.drop_index('idx_notification_type_date', table_name='fbr_change_notifications')
    op.drop_table('fbr_change_notifications')

    op.drop_column('users', 'fbr_system_sync_token')
