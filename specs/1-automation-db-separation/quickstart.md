# Quickstart Guide: Automation Database Separation

**Feature ID**: 1-automation-db-separation  
**Created**: 2026-04-24  
**Audience**: Developers

---

## Overview

This guide helps developers quickly set up and work with the new multi-database architecture for automation invoice separation.

---

## Prerequisites

- Python 3.11+
- PostgreSQL client tools
- Access to two Neon database projects (main + automation)
- uv package manager
- Docker (for AI agent)

---

## Quick Setup (5 minutes)

### Step 1: Environment Configuration

Create or update `.env` file in `backend/` directory:

```bash
# Main Database (existing)
DATABASE_URL=postgresql://....

# Automation Database (new)
AUTOMATION_DATABASE_URL=postgresql://....

# Transfer Configuration
TRANSFER_SCHEDULE_HOUR=19  # 7 PM PKT
TRANSFER_SCHEDULE_MINUTE=0
CLEANUP_SCHEDULE_HOUR=2    # 2 AM PKT
CLEANUP_RETENTION_DAYS=2
AUTOMATION_LOG_RETENTION_DAYS=90

# Existing settings
SECRET_KEY=your-secret-key
FBR_API_BASE_URL=https://gw.fbr.gov.pk
```

### Step 2: Install Dependencies

```bash
cd backend
uv sync
```

### Step 3: Run Database Migrations

```bash
# Migrate main database
uv run alembic upgrade head

# Migrate automation database (new)
uv run alembic -c alembic_automation.ini upgrade head
```

### Step 4: Start Backend

```bash
uv run uvicorn src.main:app --reload --port 8001
```

### Step 5: Verify Setup

```bash
# Check main database connection
curl http://localhost:8001/health

# Check scheduler status
curl http://localhost:8001/api/v1/admin/scheduler/status \
  -H "Cookie: session=your-session"
```

---

## Development Workflow

### Working with Two Databases

#### Getting Database Sessions

```python
from src.database.session import get_db, get_automation_db
from fastapi import Depends
from sqlmodel import Session

# Main database
@router.get("/invoices")
def get_invoices(db: Session = Depends(get_db)):
    # Query main database
    invoices = db.query(Invoice).all()
    return invoices

# Automation database
@router.get("/automation/invoices")
def get_automation_invoices(
    automation_db: Session = Depends(get_automation_db)
):
    # Query automation database
    invoices = automation_db.query(AutomationInvoice).all()
    return invoices
```

#### Cross-Database Operations

```python
from src.database.session import get_db, get_automation_db

def transfer_invoice(
    automation_invoice_id: UUID,
    main_db: Session = Depends(get_db),
    automation_db: Session = Depends(get_automation_db)
):
    # Query from automation DB
    auto_invoice = automation_db.get(AutomationInvoice, automation_invoice_id)
    
    # Transform and insert into main DB
    manual_invoice = transform_to_manual(auto_invoice)
    main_db.add(manual_invoice)
    main_db.commit()
    
    # Update automation DB
    auto_invoice.status = "transferred"
    automation_db.add(auto_invoice)
    automation_db.commit()
```

**Important**: No atomic transactions across databases. Handle errors carefully!

---

## Common Tasks

### Task 1: Manually Trigger Transfer

```bash
# Using curl
curl -X POST http://localhost:8001/api/v1/admin/transfer/trigger \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your-session" \
  -H "X-CSRF-Token: your-csrf-token" \
  -d '{"dry_run": false}'

# Using Python
from src.services.transfer_service import TransferService

transfer_service = TransferService()
result = await transfer_service.transfer_validated_invoices(
    automation_db=automation_db,
    main_db=main_db
)
print(f"Transferred: {result.invoices_transferred}")
```

### Task 2: Query Transferred Invoices

```python
from src.models.invoice import Invoice
from sqlmodel import select

# Get all automation-sourced invoices
statement = select(Invoice).where(Invoice.source == "automation")
transferred_invoices = db.exec(statement).all()

# Get invoices transferred today
from datetime import date
statement = select(Invoice).where(
    Invoice.source == "automation",
    Invoice.transferred_at >= date.today()
)
today_transfers = db.exec(statement).all()
```

### Task 3: Check Transfer Logs

```python
from src.models.transfer_log import TransferLog
from sqlmodel import select

# Get recent transfer logs
statement = select(TransferLog).order_by(
    TransferLog.transfer_timestamp.desc()
).limit(10)
recent_logs = automation_db.exec(statement).all()

for log in recent_logs:
    print(f"{log.transfer_timestamp}: {log.status}")
    print(f"  Transferred: {log.invoices_transferred}")
    print(f"  Failed: {log.invoices_failed}")
```

### Task 4: Retry Failed Transfer

```python
from src.services.transfer_service import TransferService

transfer_service = TransferService()

# Retry specific invoices
invoice_ids = [
    "123e4567-e89b-12d3-a456-426614174000",
    "223e4567-e89b-12d3-a456-426614174001"
]

result = await transfer_service.retry_failed_transfers(
    invoice_ids=invoice_ids,
    automation_db=automation_db,
    main_db=main_db
)

print(f"Successful: {result.successful}")
print(f"Failed: {result.failed}")
```

### Task 5: Test Transfer Transformation

```python
from src.services.transfer_service import TransferService

transfer_service = TransferService()

# Get an automation invoice
auto_invoice = automation_db.get(AutomationInvoice, invoice_id)

# Transform to manual invoice format
manual_invoice = transfer_service.transform_invoice_data(auto_invoice)

# Validate transformation
assert manual_invoice.invoice_number == auto_invoice.invoice_number
assert manual_invoice.source == "automation"
assert manual_invoice.status == "validated"
```

---

## Testing

### Unit Tests

```bash
# Run all tests
cd backend
uv run pytest

# Run transfer service tests only
uv run pytest tests/unit/test_transfer_service.py

# Run with coverage
uv run pytest --cov=src/services/transfer_service
```

### Integration Tests

```bash
# Run integration tests (requires test databases)
uv run pytest tests/integration/test_transfer_flow.py

# Test with real databases (careful!)
TEST_DATABASE_URL=postgresql://... \
TEST_AUTOMATION_DATABASE_URL=postgresql://... \
uv run pytest tests/integration/
```

### Manual Testing

```bash
# 1. Upload test Excel file
curl -X POST http://localhost:8001/api/v1/automation/excel/upload \
  -H "Cookie: session=your-session" \
  -F "file=@test_data/test_invoices.xlsx"

# 2. Check automation database
psql $AUTOMATION_DATABASE_URL -c \
  "SELECT id, invoice_number, status FROM automation_invoice;"

# 3. Trigger transfer
curl -X POST http://localhost:8001/api/v1/admin/transfer/trigger \
  -H "Cookie: session=your-session" \
  -H "X-CSRF-Token: your-csrf-token"

# 4. Check main database
psql $DATABASE_URL -c \
  "SELECT id, invoice_number, source, transferred_at FROM invoice WHERE source='automation';"

# 5. Verify in UI
# Navigate to http://localhost:3000/invoices/history?source=automation
```

---

## Debugging

### Check Database Connections

```python
from src.database.session import engine, automation_engine

# Test main database
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("Main DB connected:", result.scalar())

# Test automation database
with automation_engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("Automation DB connected:", result.scalar())
```

### View Scheduler Jobs

```python
from src.services.scheduler import scheduler

# List all scheduled jobs
for job in scheduler.get_jobs():
    print(f"Job: {job.name}")
    print(f"  Next run: {job.next_run_time}")
    print(f"  Trigger: {job.trigger}")
```

### Check Transfer Job Status

```bash
# View logs
tail -f logs/transfer.log

# Check last transfer
curl http://localhost:8001/api/v1/admin/transfer/logs?limit=1 \
  -H "Cookie: session=your-session"
```

### Common Issues

**Issue**: `sqlalchemy.exc.OperationalError: could not connect to server`

**Solution**: Check database URLs in `.env` and verify network connectivity

```bash
# Test connection
psql $AUTOMATION_DATABASE_URL -c "SELECT 1"
```

**Issue**: `Transfer job not running at scheduled time`

**Solution**: Check scheduler is started and timezone is correct

```python
from src.services.scheduler import scheduler
print(f"Scheduler running: {scheduler.running}")
print(f"Timezone: {scheduler.timezone}")
```

**Issue**: `Duplicate invoice number error during transfer`

**Solution**: Check for existing invoice with same number

```sql
-- In main database
SELECT id, invoice_number, source, created_at 
FROM invoice 
WHERE invoice_number = 'INV-001' AND user_id = 'user-uuid';
```

---

## Database Management

### Backup Automation Database

```bash
# Using pg_dump
pg_dump $AUTOMATION_DATABASE_URL > automation_backup_$(date +%Y%m%d).sql

# Restore
psql $AUTOMATION_DATABASE_URL < automation_backup_20260424.sql
```

### Clean Up Old Data Manually

```sql
-- Connect to automation database
psql $AUTOMATION_DATABASE_URL

-- Check data age
SELECT 
  status,
  COUNT(*) as count,
  MIN(created_at) as oldest,
  MAX(created_at) as newest
FROM automation_invoice
GROUP BY status;

-- Delete old transferred invoices (older than 2 days)
DELETE FROM automation_invoice
WHERE status = 'transferred'
  AND created_at < NOW() - INTERVAL '2 days';

-- Delete old upload sessions
DELETE FROM excel_upload_session
WHERE created_at < NOW() - INTERVAL '2 days';
```

### Monitor Database Size

```sql
-- Check automation database size
SELECT 
  pg_size_pretty(pg_database_size(current_database())) as db_size;

-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Performance Tips

### Optimize Transfer Job

```python
# Use batch inserts
from sqlmodel import Session

def transfer_batch(invoices: list[AutomationInvoice], main_db: Session):
    manual_invoices = [transform_invoice_data(inv) for inv in invoices]
    
    # Batch insert (faster than one-by-one)
    main_db.add_all(manual_invoices)
    main_db.commit()
```

### Index Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_invoice_source_status ON invoice(source, status);
CREATE INDEX idx_automation_invoice_transfer_query 
  ON automation_invoice(status, scheduled_date, scheduled_time);
```

### Connection Pooling

```python
# Adjust pool size in session.py
engine = create_engine(
    DATABASE_URL,
    pool_size=10,        # Increase for high load
    max_overflow=20,     # Allow more overflow connections
    pool_pre_ping=True,  # Verify connections before use
)
```

---

## Monitoring

### Key Metrics to Track

```python
from prometheus_client import Counter, Histogram

# Transfer metrics
transfer_success = Counter('transfer_success_total', 'Successful transfers')
transfer_failure = Counter('transfer_failure_total', 'Failed transfers')
transfer_duration = Histogram('transfer_duration_seconds', 'Transfer duration')

# Usage
with transfer_duration.time():
    result = await transfer_service.transfer_validated_invoices(...)
    if result.success:
        transfer_success.inc()
    else:
        transfer_failure.inc()
```

### Health Checks

```python
@router.get("/health/databases")
async def check_databases(
    main_db: Session = Depends(get_db),
    automation_db: Session = Depends(get_automation_db)
):
    try:
        main_db.execute("SELECT 1")
        automation_db.execute("SELECT 1")
        return {"status": "healthy", "databases": ["main", "automation"]}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

---

## Deployment

### Environment-Specific Configuration

**Development**:
```bash
DATABASE_URL=postgresql://....
AUTOMATION_DATABASE_URL=postgresql://....
TRANSFER_SCHEDULE_HOUR=19
```

**Staging**:
```bash
DATABASE_URL=postgresql://....
AUTOMATION_DATABASE_URL=postgresql://....
TRANSFER_SCHEDULE_HOUR=19
```

**Production**:
```bash
DATABASE_URL=postgresql://....
AUTOMATION_DATABASE_URL=postgresql://....
TRANSFER_SCHEDULE_HOUR=19
```

### Migration Checklist

- [ ] Create automation database in Neon
- [ ] Update environment variables
- [ ] Run database migrations
- [ ] Test database connections
- [ ] Deploy backend code
- [ ] Verify scheduler jobs running
- [ ] Test manual transfer trigger
- [ ] Monitor first scheduled transfer
- [ ] Verify cleanup job
- [ ] Update monitoring dashboards

---

## Troubleshooting

### Transfer Job Not Running

1. Check scheduler status:
```python
from src.services.scheduler import scheduler
print(scheduler.get_jobs())
```

2. Check logs:
```bash
tail -f logs/scheduler.log | grep transfer
```

3. Manually trigger:
```bash
curl -X POST http://localhost:8001/api/v1/admin/transfer/trigger
```

### Invoices Not Appearing in Main Database

1. Check automation database:
```sql
SELECT id, invoice_number, status, scheduled_date, scheduled_time
FROM automation_invoice
WHERE status = 'validated';
```

2. Check transfer logs:
```sql
SELECT * FROM transfer_log ORDER BY transfer_timestamp DESC LIMIT 5;
```

3. Check for errors:
```sql
SELECT id, invoice_number, transfer_error
FROM automation_invoice
WHERE status = 'transfer_failed';
```

### Performance Issues

1. Check connection pool:
```python
from src.database.session import engine
print(f"Pool size: {engine.pool.size()}")
print(f"Checked out: {engine.pool.checkedout()}")
```

2. Check slow queries:
```sql
-- Enable slow query logging
ALTER DATABASE automation_db SET log_min_duration_statement = 1000;

-- View slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

## Additional Resources

- [Implementation Plan](./plan.md)
- [Data Model Documentation](./data-model.md)
- [API Contracts](./contracts/api-contracts.md)
- [Feature Specification](./spec.md)

---

## Getting Help

**Issues**: Report bugs at project issue tracker  
**Questions**: Ask in team Slack channel  
**Documentation**: Check `/docs` directory

---

## Next Steps

After completing this quickstart:

1. Review the [Implementation Plan](./plan.md) for detailed architecture
2. Read the [Data Model](./data-model.md) to understand database schema
3. Explore the [API Contracts](./contracts/api-contracts.md) for endpoint details
4. Run the test suite to verify your setup
5. Try manually triggering a transfer with test data

Happy coding! 🚀
