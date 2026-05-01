"""
Definitive test to diagnose the transaction_type_id issue.
This will test the exact same code path the AI agent uses.
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text, inspect
from sqlmodel import Session, select
from src.config.settings import settings
from src.models.invoice import Invoice
from uuid import uuid4

print("=" * 70)
print("DEFINITIVE DIAGNOSIS TEST")
print("=" * 70)

# Test 1: Raw SQL query
print("\n1. Testing with RAW SQL query...")
engine = create_engine(settings.database_url, connect_args={'connect_timeout': 60})
with engine.connect() as conn:
    try:
        result = conn.execute(text("""
            SELECT transaction_type_id
            FROM invoices
            LIMIT 1
        """))
        print("   [OK] Raw SQL query succeeded - column exists!")
    except Exception as e:
        print(f"   [FAIL] Raw SQL query failed: {e}")

# Test 2: SQLAlchemy Inspector
print("\n2. Testing with SQLAlchemy Inspector...")
inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('invoices')]
if 'transaction_type_id' in columns:
    print(f"   [OK] Inspector sees column (total columns: {len(columns)})")
else:
    print(f"   [FAIL] Inspector does NOT see column (total columns: {len(columns)})")

# Test 3: SQLModel query (what AI agent uses)
print("\n3. Testing with SQLModel query (AI agent's method)...")
try:
    with Session(engine) as session:
        # This is the exact query the AI agent uses
        statement = select(Invoice).where(
            Invoice.user_id == uuid4(),  # Dummy UUID
            Invoice.automation_invoice_id == uuid4()
        )
        # Just compile the query, don't execute
        compiled = statement.compile(compile_kwargs={"literal_binds": True})
        query_str = str(compiled)

        if 'transaction_type_id' in query_str:
            print("   [OK] SQLModel query includes transaction_type_id column")
            print(f"   Query preview: ...{query_str[200:300]}...")
        else:
            print("   [FAIL] SQLModel query does NOT include transaction_type_id")
            print(f"   Query: {query_str[:500]}")

except Exception as e:
    print(f"   [ERROR] Failed to compile query: {e}")

# Test 4: Check Invoice model metadata
print("\n4. Checking Invoice model metadata...")
from sqlalchemy import inspect as sa_inspect
mapper = sa_inspect(Invoice)
column_names = [col.key for col in mapper.columns]
if 'transaction_type_id' in column_names:
    print(f"   [OK] Invoice model has transaction_type_id field")
    print(f"   Total fields in model: {len(column_names)}")
else:
    print(f"   [FAIL] Invoice model missing transaction_type_id field")
    print(f"   Available fields: {', '.join(column_names[:10])}...")

print("\n" + "=" * 70)
print("DIAGNOSIS COMPLETE")
print("=" * 70)
