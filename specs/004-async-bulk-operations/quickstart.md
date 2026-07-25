# Quickstart: Non-blocking Bulk Operations

**Feature**: 004-async-bulk-operations
**Date**: 2026-07-25

## Prerequisites

- Install backend deps: `cd backend && uv sync`
- Backend running: `cd backend && uv run uvicorn src.main:app --reload`
- Frontend running: `cd frontend && npm run dev`
- Database migrated: `cd backend && uv run alembic upgrade head`
- At least one draft invoice and one validated invoice in your account

## API Testing (Swagger)

1. Open `http://localhost:8001/docs`
2. Authenticate via the `/auth/login` endpoint
3. Test the new endpoints:

### A. Bulk Validate

```bash
# Start validation (get task_id back)
curl -X POST http://localhost:8001/api/v1/invoices/bulk-validate \
  -H "Content-Type: application/json" \
  -b "access_token=YOUR_TOKEN" \
  -d '{"invoice_ids": ["uuid-1", "uuid-2", "uuid-3"]}'

# Poll progress (replace with actual task_id)
curl http://localhost:8001/api/v1/invoices/bulk-task/TASK_ID \
  -b "access_token=YOUR_TOKEN"

# Recover active tasks after navigation
curl http://localhost:8001/api/v1/invoices/bulk-tasks/active \
  -b "access_token=YOUR_TOKEN"
```

### B. Bulk Post

```bash
# Start posting
curl -X POST http://localhost:8001/api/v1/invoices/bulk-post \
  -H "Content-Type: application/json" \
  -b "access_token=YOUR_TOKEN" \
  -d '{"invoice_ids": ["uuid-4", "uuid-5"], "environment": "SANDBOX"}'

# Poll progress
curl http://localhost:8001/api/v1/invoices/bulk-task/TASK_ID \
  -b "access_token=YOUR_TOKEN"
```

## Frontend Testing

1. Navigate to `http://localhost:3000/invoices/history`
2. Select 3-5 draft invoices using the checkboxes
3. Click the **Validate Selected** button (checkmark icon in sidebar)
4. Verify:
   - Confirmation toast appears immediately ("Validation started for X invoices")
   - Progress card appears below the sidebar showing percentage, processed count, success/failure
   - UI is responsive — you can filter, search, use single-invoice actions
5. Navigate to another page (e.g., Dashboard), then return to History
   - Verify the progress card is still visible and updating
6. Wait for completion:
   - Toast notification appears on whichever page you're on
   - Invoice list auto-refreshes showing updated statuses

## Running Backend Tests

```bash
cd backend
uv run pytest tests/test_bulk_operation_service.py -v
uv run pytest tests/test_bulk_operation_endpoints.py -v
```

## Running Frontend Tests

```bash
cd frontend
npm run test -- __tests__/BulkOperationContext.test.tsx
npm run test -- __tests__/BulkOperationProgress.test.tsx
```

## Verification Checklist

- [ ] Select draft invoices → Validate → UI freed immediately → progress visible
- [ ] Navigate away → return → progress still visible
- [ ] Close tab → reopen → login → completed result shown
- [ ] Attempt second operation while one running → blocked with message
- [ ] Single-invoice validate/post buttons still work (row-level)
- [ ] Existing invoice data unchanged
- [ ] Wait 10+ minutes → completed task row deleted from DB
