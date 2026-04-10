"""make_file_path_optional_in_excel_upload_session

Revision ID: c05b54c7bd14
Revises: f038b6c5a63d
Create Date: 2026-04-06 18:17:10.189642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c05b54c7bd14'
down_revision: Union[str, Sequence[str], None] = 'f038b6c5a63d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Make file_path nullable for in-memory parsing."""
    op.alter_column('excel_upload_session', 'file_path',
                   existing_type=sa.String(500),
                   nullable=True)


def downgrade() -> None:
    """Downgrade schema: Make file_path required again."""
    # Note: This will fail if any NULL values exist
    op.alter_column('excel_upload_session', 'file_path',
                   existing_type=sa.String(500),
                   nullable=False)
