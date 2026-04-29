"""remove cross-database foreign keys

Revision ID: 20260428_remove_fk
Revises: 9606d8ab42a2
Create Date: 2026-04-28 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260428_remove_fk'
down_revision = '9606d8ab42a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Remove foreign key constraints that reference tables in different databases.

    The automation database (excel_upload_session, automation_invoice) cannot have
    foreign keys to the main database (users table) because PostgreSQL doesn't
    support cross-database foreign keys.
    """
    # Drop foreign key constraint from excel_upload_session.user_id
    op.drop_constraint(
        'excel_upload_session_user_id_fkey',
        'excel_upload_session',
        type_='foreignkey'
    )

    # Drop foreign key constraint from automation_invoice.user_id
    op.drop_constraint(
        'automation_invoice_user_id_fkey',
        'automation_invoice',
        type_='foreignkey'
    )


def downgrade() -> None:
    """
    Re-add foreign key constraints (only works if both tables are in same database).
    """
    # Re-add foreign key to automation_invoice.user_id
    op.create_foreign_key(
        'automation_invoice_user_id_fkey',
        'automation_invoice',
        'users',
        ['user_id'],
        ['id']
    )

    # Re-add foreign key to excel_upload_session.user_id
    op.create_foreign_key(
        'excel_upload_session_user_id_fkey',
        'excel_upload_session',
        'users',
        ['user_id'],
        ['id']
    )
