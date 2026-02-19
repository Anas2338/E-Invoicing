"""add_separate_sandbox_production_tokens

Revision ID: 9937d061521d
Revises: add_fbr_credentials
Create Date: 2026-02-13 16:36:16.669917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9937d061521d'
down_revision: Union[str, Sequence[str], None] = 'add_fbr_credentials'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns for separate sandbox and production tokens
    op.add_column('users', sa.Column('fbr_sandbox_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('fbr_production_token', sa.String(), nullable=True))

    # Migrate existing fbr_access_token data to the appropriate field based on fbr_environment
    connection = op.get_bind()

    # Update SANDBOX tokens
    connection.execute(
        sa.text("""
            UPDATE users
            SET fbr_sandbox_token = fbr_access_token
            WHERE fbr_environment = 'SANDBOX' AND fbr_access_token IS NOT NULL
        """)
    )

    # Update PRODUCTION tokens
    connection.execute(
        sa.text("""
            UPDATE users
            SET fbr_production_token = fbr_access_token
            WHERE fbr_environment = 'PRODUCTION' AND fbr_access_token IS NOT NULL
        """)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the new columns
    op.drop_column('users', 'fbr_production_token')
    op.drop_column('users', 'fbr_sandbox_token')
