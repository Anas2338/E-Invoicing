"""
Verify AI Agent database connection and tables.
"""
import sys
from pathlib import Path
from sqlalchemy import text, inspect

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add backend to path for model imports
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

from database import engine, get_db_session, test_database_connection


def verify_connection():
    """Test database connection."""
    print("Testing AI Agent database connection...")
    is_connected, latency_ms = test_database_connection()

    if is_connected:
        print(f"[OK] Connected successfully (latency: {latency_ms}ms)")
        return True
    else:
        print("[ERROR] Connection failed")
        return False


def list_tables():
    """List all tables in the database."""
    print("\nListing tables in AI Agent database...")

    with get_db_session() as db:
        result = db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]

        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")

        return tables


def verify_required_tables():
    """Verify that all required tables exist."""
    print("\nVerifying required tables for AI Agent...")

    required_tables = [
        'automation_invoice',
        'automation_log',
        'excel_upload_session',
        'ai_agent_health_check',
        'users',
        'fbr_responses',
        'invoices'
    ]

    with get_db_session() as db:
        result = db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
        existing_tables = {row[0] for row in result}

    all_present = True
    for table in required_tables:
        if table in existing_tables:
            print(f"  [OK] {table}")
        else:
            print(f"  [X] {table} - MISSING")
            all_present = False

    return all_present


def main():
    """Main verification function."""
    print("=" * 60)
    print("AI Agent Database Verification")
    print("=" * 60)

    try:
        # Test connection
        if not verify_connection():
            print("\n[ERROR] Database connection failed!")
            return False

        # List all tables
        tables = list_tables()

        # Verify required tables
        if verify_required_tables():
            print("\n[OK] All required tables are present!")
            print("[OK] AI Agent database is ready!")
            return True
        else:
            print("\n[ERROR] Some required tables are missing!")
            return False

    except Exception as e:
        print(f"\n[ERROR] Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
