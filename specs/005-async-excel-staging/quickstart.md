# Quickstart: Async Excel Staging

**Feature**: 005-async-excel-staging  
**Date**: 2026-07-27

## Prerequisites

- Python 3.11+ with `uv` package manager
- Node.js 20+ (frontend)
- PostgreSQL database (Neon)
- Project already set up per CLAUDE.md

## Setup

### 1. Backend: Install dependencies

```bash
cd backend
uv pip install -e .
```

### 2. Backend: Run migrations

```bash
cd backend
alembic upgrade head
```

This applies the new `excel_staging_session` and `excel_staging_row` tables.

### 3. Backend: Start development server

```bash
cd backend
uvicorn src.main:app --reload --port 8001
```

### 4. Frontend: Install and start

```bash
cd frontend
npm install
npm run dev
```

## Testing

### Run backend tests

```bash
cd backend
uv run pytest tests/unit/test_excel_staging_parser.py -v
uv run pytest tests/unit/test_excel_staging_service.py -v
uv run pytest tests/integration/test_excel_staging_api.py -v
```

### Run frontend tests

```bash
cd frontend
npx vitest run src/__tests__/ExcelStagingGrid.test.tsx
npx vitest run src/__tests__/ExcelStagingContext.test.tsx
```

## Manual Test Flow

1. **Login** at `http://localhost:3000/login`
2. **Navigate** to Dashboard, click "Bulk Excel Upload"
3. **Download template** — click "Download Template"
4. **Fill template** with a mix of valid and intentionally invalid data
5. **Upload** — select the file and click "Upload & Parse"
6. **Review grid** — verify all rows appear, errors highlighted red
7. **Edit cells** — click errored cells, fix values, press Enter
8. **Recheck** — click "Recheck", verify errors update
9. **Repeat** steps 7-8 until all errors cleared
10. **Upload All** — click the enabled button, verify invoices appear in history
11. **Test Cancel** — upload another file, click Cancel, verify session deleted
12. **Test Persistence** — upload, navigate away, come back, verify session resumes

## Database Verification

After commit, verify staging tables are empty:
```sql
SELECT COUNT(*) FROM excel_staging_session;  -- Should be 0
SELECT COUNT(*) FROM excel_staging_row;       -- Should be 0
```

Verify invoices were created:
```sql
SELECT id, external_id, status FROM invoices WHERE source = 'manual' ORDER BY created_at DESC LIMIT 10;
```
