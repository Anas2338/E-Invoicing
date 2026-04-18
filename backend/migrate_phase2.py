"""
Database migration script to add Phase 2 security fields.
Run with: python migrate_phase2.py
"""
import sys
sys.path.insert(0, '.')

from src.database.session import engine
from sqlalchemy import text

def migrate():
    """Add Phase 2 security fields to users table."""

    sql_commands = [
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;',
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;',
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;',
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS last_failed_login_at TIMESTAMP;',
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 0;',
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'user';",
    ]

    print("Starting Phase 2 database migration...")
    print("=" * 60)

    with engine.connect() as conn:
        for sql in sql_commands:
            try:
                conn.execute(text(sql))
                column_name = sql.split('ADD COLUMN IF NOT EXISTS ')[1].split(' ')[0]
                print(f'[OK] Added column: {column_name}')
            except Exception as e:
                print(f'[ERROR] {str(e)}')

        conn.commit()

    print("=" * 60)
    print("[SUCCESS] Phase 2 database migration complete!")
    print("\nNew columns added:")
    print("  - failed_login_attempts (INTEGER)")
    print("  - locked_until (TIMESTAMP)")
    print("  - last_login_at (TIMESTAMP)")
    print("  - last_failed_login_at (TIMESTAMP)")
    print("  - token_version (INTEGER)")
    print("  - role (VARCHAR)")

if __name__ == "__main__":
    migrate()
