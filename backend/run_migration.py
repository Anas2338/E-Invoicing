"""
Apply user approval migration directly using SQLAlchemy.
Run this from the backend directory: python run_migration.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from src.database.session import engine

def run_migration():
    """Apply user approval migration."""
    try:
        print("Connecting to database...")

        with engine.connect() as conn:
            print("Applying migration...")

            # Add account_status column
            print("  - Adding account_status column...")
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status VARCHAR NOT NULL DEFAULT 'pending'
            """))

            # Add approved_by column
            print("  - Adding approved_by column...")
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS approved_by UUID
            """))

            # Add approved_at column
            print("  - Adding approved_at column...")
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP
            """))

            # Add rejection_reason column
            print("  - Adding rejection_reason column...")
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR
            """))

            # Create index
            print("  - Creating index on account_status...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_users_account_status ON users(account_status)
            """))

            # Update existing users to approved
            print("  - Updating existing users to 'approved' status...")
            result = conn.execute(text("""
                UPDATE users SET account_status = 'approved' WHERE account_status = 'pending'
            """))
            print(f"    Updated {result.rowcount} existing users")

            conn.commit()

        print("\n[SUCCESS] Migration completed successfully!")
        print("\nNext steps:")
        print("1. Make your first admin user:")
        print("   uv run python make_admin.py your-email@example.com")
        print("\n2. Access admin panel at:")
        print("   http://localhost:3000/admin/users")

        return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
