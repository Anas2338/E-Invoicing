---
id: 004-async-bulk-operations-impl-001
title: implement-bulk-operations
stage: implement
date: 2026-07-25T00:00:00Z
surface: cli
model: deepseek-v4-flash
feature: 004-async-bulk-operations
branch: 005-async-excel-staging
user: Muhammad Anus
command: /sp.implement
labels: [implementation, bulk-operations, background-tasks]
links:
  spec: specs/004-async-bulk-operations/spec.md
  plan: specs/004-async-bulk-operations/plan.md
  tasks: specs/004-async-bulk-operations/tasks.md
  ticket:
  adr:
  pr:
files:
  - backend/src/models/bulk_operation.py (NEW)
  - backend/src/models/__init__.py (EDIT)
  - backend/src/schemas/bulk_operation.py (NEW)
  - backend/alembic/versions/20260725_merge_heads_and_add_bulk_operation_task.py (NEW)
  - backend/src/services/bulk_operation_service.py (NEW)
  - backend/src/api/v1/invoices.py (EDIT)
  - backend/src/services/scheduler.py (EDIT)
  - backend/tests/test_bulk_operation_service.py (NEW)
  - backend/tests/test_bulk_operation_endpoints.py (NEW)
  - frontend/src/lib/api.ts (EDIT)
  - frontend/src/contexts/BulkOperationContext.tsx (NEW)
  - frontend/src/components/invoices/BulkOperationProgress.tsx (NEW)
  - frontend/src/app/(protected)/layout.tsx (EDIT)
  - frontend/src/app/(protected)/invoices/history/page.tsx (EDIT)
tests:
  - backend/tests/test_bulk_operation_service.py (7 tests, all PASS)
  - backend/tests/test_bulk_operation_endpoints.py (13 tests, all PASS)
  - frontend/__tests__/BulkOperationContext.test.tsx (pending)
  - frontend/__tests__/BulkOperationProgress.test.tsx (pending)
---

## Prompt

/sp.implement — execute implementation tasks for 004-async-bulk-operations feature

## Response snapshot

Completed implementation across all 45 tasks in 7 phases:

**Phase 1 — Foundational**: Created BulkOperationTask model, Pydantic schemas, Alembic merge migration (adds bulk_operation_task table, merges 3 heads). ✅

**Phase 2 — Service (TDD)**: Wrote 7 service tests covering bulk validate/post with all-succeed, partial-failure, single-invoice-failure-does-not-stop-batch, and empty-batch scenarios. Implemented `BulkOperationService` with configurable DB session factory for testability. ✅

**Phase 3 — Endpoints (TDD)**: Wrote 13 endpoint tests covering all 4 endpoints (bulk-validate, bulk-post, bulk-task status, active tasks) with auth guards, user isolation, and edge cases. Implemented all 4 endpoints in invoices.py. ✅

**Phase 4 — Frontend MVP**: Added 4 API functions to api.ts, created `BulkOperationContext` (polling, localStorage, backend recovery, auto-remove), created `BulkOperationProgress` component (progress bar, error details, dismiss), wired `BulkOperationProvider` in layout, replaced both bulk handlers with fire-and-forget pattern. ✅

**Phase 5-7 — Recovery, Concurrency, Polish**:
- Recovery: `GET /invoices/bulk-tasks/active` endpoint + `recoverFromBackend` in context ✅
- Concurrency: `has_active_operation` check in endpoints + `hasActiveOperation` button guards ✅
- Cleanup: `cleanup_completed_bulk_tasks` job in scheduler (10-min interval, deletes tasks >5min old) ✅

**All 20 backend tests PASS.**

## Outcome

- ✅ Impact: Complete non-blocking bulk operations feature implemented — fire-and-forget + polling pattern replaces blocking sequential processing
- 🧪 Tests: 20 backend tests (7 service, 13 endpoint), all passing; frontend tests still to be written
- 📁 Files: 8 new files created, 6 files edited across backend and frontend
- 🔁 Next prompts: Frontend tests (context + progress component), migration apply, manual QA via Quickstart guide
- 🧠 Reflection: Using `flag_modified` for JSON column mutations was necessary for SQLite compatibility. Test DB session injection via factory pattern enables clean testing. The dependency override trick with `src.`-prefixed imports is essential for FastAPI tests.

## Evaluation notes (flywheel)

- Failure modes observed: Module aliasing conflicts between `src.` and short imports in tests (resolved by using `src.` prefix), JSON list mutation not tracked by SQLAlchemy (resolved by `flag_modified`)
- Graders run and results (PASS/FAIL): All 20 backend tests PASS
- Prompt variant (if applicable): TDD-first — tests written before implementation
- Next experiment (smallest change to try): Add frontend Vitest tests
