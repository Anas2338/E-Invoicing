"""
Quick migration script to add transaction_type_id column to invoices table.
Run this with: uv run python add_transaction_type_id.py
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text, inspect
from src.config.settings import settings

def main():
    print("Connecting to database...")
    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        # Check if column exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('invoices')]

        if 'transaction_type_id' in columns:
            print("[OK] Column 'transaction_type_id' already exists in invoices table!")
            return

        print("Adding 'transaction_type_id' column to invoices table...")
        conn.execute(text('ALTER TABLE invoices ADD COLUMN transaction_type_id VARCHAR'))
        conn.commit()
        print("[OK] Column added successfully!")
        print("\nYou can now restart the AI agent.")

if __name__ == "__main__":
    main()
