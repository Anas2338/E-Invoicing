"""
Script to create all database tables from SQLModel models.
Run this to initialize a fresh database.
"""
from sqlalchemy import text, inspect
from sqlmodel import SQLModel
from src.database.session import engine, automation_engine
from src.models.fbr_master_data import FBRBase

# All models are already imported in session.py, so they're registered


def create_main_db_tables():
    """Create all tables in the main database."""
    print("Creating tables in main database...")

    # Create SQLModel tables
    SQLModel.metadata.create_all(bind=engine)

    # Create FBR model tables (using separate declarative base)
    FBRBase.metadata.create_all(bind=engine)

    print("Main database tables created successfully")


def create_automation_db_tables():
    """Create all tables in the automation database."""
    print("\nCreating tables in automation database...")

    # Create SQLModel tables in automation database
    SQLModel.metadata.create_all(bind=automation_engine)

    # Create FBR model tables in automation database
    FBRBase.metadata.create_all(bind=automation_engine)

    print("Automation database tables created successfully")


def verify_tables():
    """Verify that tables were created."""
    print("\nVerifying main database tables...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"Found {len(tables)} tables in main database:")
        for table in tables:
            print(f"  - {table}")

    print("\nVerifying automation database tables...")
    with automation_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"Found {len(tables)} tables in automation database:")
        for table in tables:
            print(f"  - {table}")


def main():
    """Main execution function."""
    try:
        create_main_db_tables()
        create_automation_db_tables()
        verify_tables()
        print("\nAll database tables created successfully!")
    except Exception as e:
        print(f"\nError creating tables: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        engine.dispose()
        automation_engine.dispose()


if __name__ == "__main__":
    main()
