"""
Script to apply user approval migration manually.
Run this from the backend directory: python apply_migration.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from alembic.config import Config
from alembic import command

def apply_migration():
    """Apply pending migrations."""
    try:
        # Create Alembic config
        alembic_cfg = Config("alembic.ini")

        # Run upgrade to head
        print("Applying database migrations...")
        command.upgrade(alembic_cfg, "head")
        print("✓ Migrations applied successfully!")

    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    apply_migration()
