"""
Check if transaction_type_id column exists in the invoices table.
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def main():
    db_url = os.getenv('DATABASE_URL')
    print(f"Checking database: {db_url.split('@')[1].split('/')[0] if '@' in db_url else 'unknown'}")

    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name='invoices'
            ORDER BY ordinal_position
        """))

        columns = result.fetchall()
        print(f"\nFound {len(columns)} columns in 'invoices' table:")

        has_transaction_type_id = False
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
            if col[0] == 'transaction_type_id':
                has_transaction_type_id = True

        print()
        if has_transaction_type_id:
            print("[OK] Column 'transaction_type_id' EXISTS")
        else:
            print("[ERROR] Column 'transaction_type_id' DOES NOT EXIST")
            print("\nAdding column now...")
            conn.execute(text('ALTER TABLE invoices ADD COLUMN transaction_type_id VARCHAR'))
            conn.commit()
            print("[OK] Column added successfully!")

if __name__ == "__main__":
    main()
