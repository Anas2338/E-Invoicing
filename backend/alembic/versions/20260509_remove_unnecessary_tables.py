"""remove unnecessary tables

Revision ID: 20260509_remove_tables
Revises:
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260509_remove_tables'
down_revision = None  # Will be set to the latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Remove unnecessary tables from the database"""

    # Drop tables in order (respecting foreign key constraints)
    # Drop dependent tables first

    # Automation related tables
    op.drop_table('automation_log', if_exists=True)
    op.drop_table('automation_invoice', if_exists=True)
    op.drop_table('excel_upload_session', if_exists=True)

    # User saved data tables
    op.drop_table('user_saved_uoms', if_exists=True)
    op.drop_table('user_saved_tax_rates', if_exists=True)
    op.drop_table('user_saved_product_descriptions', if_exists=True)
    op.drop_table('user_saved_hs_codes', if_exists=True)
    op.drop_table('user_saved_buyers', if_exists=True)

    # Logging and tracking tables
    op.drop_table('transfer_log', if_exists=True)
    op.drop_table('posting_log', if_exists=True)
    op.drop_table('fbr_sync_logs', if_exists=True)
    op.drop_table('audit_logs', if_exists=True)
    op.drop_table('daily_posting_counters', if_exists=True)

    # FBR related tables
    op.drop_table('fbr_sro_items', if_exists=True)

    # Health check table
    op.drop_table('ai_agent_health_check', if_exists=True)


def downgrade():
    """
    Note: This migration is destructive and cannot be fully reversed.
    The downgrade would require recreating all tables with their original schemas,
    which is not practical. If you need these tables back, restore from backup.
    """
    pass
