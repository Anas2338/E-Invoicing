# Research: Non-blocking Bulk Invoice Operations

**Feature**: 004-async-bulk-operations
**Date**: 2026-07-25

## Decision 1: Background Processing Mechanism

**Decision**: Use FastAPI `BackgroundTasks` for asynchronous processing.

**Rationale**:
- Already used by the AI agent's Excel upload flow (`ai-agent/src/api/v1/automation/excel.py` line 176: `BackgroundValidationService.validate_invoices_background()`)
- No new infrastructure required (no Redis, no Celery)
- In-process — runs in the same FastAPI worker process, which means it survives beyond the request lifecycle but NOT beyond a server restart
- Server restart failure mode is explicitly accepted in the spec (Edge Cases: "In-progress operations are lost")
- The auto-posting scheduler (runs every 5 min) naturally picks up validated-but-unposted invoices as a recovery mechanism

**Alternatives considered**:
- APScheduler one-shot jobs — overkill for single-use operations, complicates cleanup
- Dedicated task queue (Celery, Redis Queue) — would require new infrastructure, violates "additive only" constraint
- Keep synchronous but add frontend-only polling — doesn't solve "reload loses progress" problem

## Decision 2: Database Tracking Table

**Decision**: Create a new `bulk_operation_task` table in the main backend database.

**Rationale**:
- Provides persistence for progress tracking (survives page reloads, enables cross-tab visibility)
- Lightweight — rows are temporary (auto-cleaned after 5-10 min)
- Follows the same pattern as the AI agent's `excel_upload_session` table
- No foreign keys into existing tables (additive only)
- Uses SQLModel following the existing model pattern (`Base, table=True`)

**Alternatives considered**:
- In-memory dict — lost on restart, not shareable across workers
- Redis — new infrastructure, violates additive constraint
- Reuse `excel_upload_session` — wrong domain (AI agent DB), wrong purpose (Excel upload vs bulk operations)

## Decision 3: Progress Communication Pattern

**Decision**: REST polling (not WebSockets, not SSE).

**Rationale**:
- Already the pattern used by `UploadSessionContext.tsx` (polls `/excel/status/{session_id}` every 3 seconds)
- Frontend already has the polling infrastructure in the context pattern
- No new server infrastructure needed (no WebSocket handlers, no SSE middleware)
- Polling interval of 3 seconds meets SC-002 ("progress updates at least every 5 seconds")
- Simpler error handling than persistent connections

**Alternatives considered**:
- WebSockets — real-time but requires new server infrastructure, not in existing stack
- Server-Sent Events — simpler than WebSockets but still new infrastructure, poor browser support for custom headers (auth)

## Decision 4: Frontend State Management

**Decision**: React Context + localStorage (mirror `UploadSessionContext`).

**Rationale**:
- Proven pattern: `UploadSessionContext.tsx` (256 lines) handles polling, localStorage persistence, backend recovery, cross-tab visibility
- New `BulkOperationContext` can be modeled directly on it (same structure, different API endpoints)
- Both contexts will coexist in the protected layout (alongside `UploadSessionProvider`)
- localStorage enables recovery across page navigation and browser close/reopen
- Context auto-detects on mount (reads localStorage, queries backend for processing tasks)

**Alternatives considered**:
- TanStack React Query — already in the stack but requires more boilerplate for real-time polling across components
- Redux/Zustand — overkill for a single-feature state
- URL query params — doesn't survive tab close

## Decision 5: Backend Test Strategy

**Decision**: Write pytest tests following the existing `test_auth.py` pattern.

**Rationale**:
- `backend/tests/conftest.py` provides `clean_test_engine` (in-memory SQLite), `client` (TestClient), test user fixtures, and environment setup
- Existing test files (`test_auth.py`, `test_database_session.py`) are flat in `backend/tests/`, not in subdirectories
- Follows the same structure: module-level `test_app`, fixtures for db session and authenticated client, parametrized tests for success/failure/unauth
- Mock FBR client calls using `unittest.mock.patch` / `pytest-mock`'s `mocker` fixture

## Decision 6: Frontend Test Strategy

**Decision**: Add Vitest + @testing-library/react for frontend tests.

**Rationale**:
- No frontend tests currently exist — this feature creates the first
- Vitest integrates natively with Next.js/TypeScript and is faster than Jest
- @testing-library/react provides component testing with React context providers
- Test files placed in `frontend/__tests__/` alongside the source

## Decision 7: Scheduler Cleanup Job

**Decision**: Add a cleanup job to the existing `backend/src/services/scheduler.py`.

**Rationale**:
- Already has APScheduler infrastructure with `AsyncIOScheduler`
- Existing jobs: `auto_posting_job` (every 5 min)
- New job: `cleanup_bulk_operation_tasks` (every 10 min)
- Pattern: `scheduler.add_job(coro_func, trigger=IntervalTrigger(minutes=10), ...)`
- Job uses its own DB session via `with get_db_session() as db:`
- Deletes rows where `status IN ('completed', 'failed', 'partially_completed') AND completed_at < NOW() - INTERVAL '5 minutes'`

## Decision 8: API Contract Design

**Decision**: Follow existing REST patterns — flat JSON request/response, Pydantic schemas.

**Rationale**:
- All existing endpoints use Pydantic `BaseModel` for request/response schemas
- Routes use `@router.post("/")` with `response_model=` decorator
- Dependencies: `db = Depends(get_database_session)`, `user_id: str = Depends(require_authentication)`
- New endpoints use `BackgroundTasks` parameter (FastAPI built-in) for fire-and-forget
- All validation/posting logic reuses existing services (`PostingService`, existing validate functions)

## No Unresolved Clarifications

All technical decisions have been made. No NEEDS CLARIFICATION markers remain.
