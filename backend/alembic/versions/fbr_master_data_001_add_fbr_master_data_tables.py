"""Add FBR master data tables

Revision ID: fbr_master_data_001
Revises: c942623196b2
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fbr_master_data_001'
down_revision = 'add_fbr_credentials'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create FBR provinces table
    op.create_table(
        'fbr_provinces',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_fbr_provinces_code', 'fbr_provinces', ['code'])

    # Create FBR UOM table
    op.create_table(
        'fbr_uom',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_fbr_uom_code', 'fbr_uom', ['code'])

    # Create FBR HS codes table
    op.create_table(
        'fbr_hs_codes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_fbr_hs_codes_code', 'fbr_hs_codes', ['code'])
    op.create_index('idx_hs_code_search', 'fbr_hs_codes', ['code', 'description'])

    # Create FBR transaction types table
    op.create_table(
        'fbr_transaction_types',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_fbr_transaction_types_code', 'fbr_transaction_types', ['code'])

    # Create FBR invoice types table
    op.create_table(
        'fbr_invoice_types',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_fbr_invoice_types_code', 'fbr_invoice_types', ['code'])

    # Create FBR SRO items table
    op.create_table(
        'fbr_sro_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_fbr_sro_items_code', 'fbr_sro_items', ['code'])

    # Create FBR sync logs table
    op.create_table(
        'fbr_sync_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sync_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('records_synced', sa.Integer(), default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sync_log_status', 'fbr_sync_logs', ['sync_type', 'status', 'started_at'])


def downgrade() -> None:
    op.drop_index('idx_sync_log_status', table_name='fbr_sync_logs')
    op.drop_table('fbr_sync_logs')

    op.drop_index('ix_fbr_sro_items_code', table_name='fbr_sro_items')
    op.drop_table('fbr_sro_items')

    op.drop_index('ix_fbr_invoice_types_code', table_name='fbr_invoice_types')
    op.drop_table('fbr_invoice_types')

    op.drop_index('ix_fbr_transaction_types_code', table_name='fbr_transaction_types')
    op.drop_table('fbr_transaction_types')

    op.drop_index('idx_hs_code_search', table_name='fbr_hs_codes')
    op.drop_index('ix_fbr_hs_codes_code', table_name='fbr_hs_codes')
    op.drop_table('fbr_hs_codes')

    op.drop_index('ix_fbr_uom_code', table_name='fbr_uom')
    op.drop_table('fbr_uom')

    op.drop_index('ix_fbr_provinces_code', table_name='fbr_provinces')
    op.drop_table('fbr_provinces')
