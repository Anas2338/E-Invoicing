# Implementation Plan: Async Excel Staging with Inline Error Correction

**Branch**: `005-async-excel-staging` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-async-excel-staging/spec.md`

## Summary

Replace the current all-or-nothing manual Excel upload flow with an async, database-backed staging workflow. Users upload an Excel file → ALL rows are parsed and displayed in an editable spreadsheet-like grid with per-field error highlighting → users fix errors inline → click "Recheck" to re-validate edited rows → when all errors are cleared, click "Upload All" to create DRAFT invoices → staging data is deleted. The session persists across navigation and logout/login. Cancel also deletes the staging session.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5 (frontend)
**Primary Dependencies**: FastAPI, SQLModel, Pandas/OpenPyXL (backend); Next.js 16, React 19, Tailwind CSS 4, shadcn/ui (frontend)
**Storage**: Neon PostgreSQL (existing `invoices` table + new `excel_staging_session` and `excel_staging_row` tables)
**Testing**: pytest + httpx (backend), Vitest + React Testing Library (frontend)
**Target Platform**: Web (Linux server + modern browsers)
**Project Type**: Web (separate `backend/` and `frontend/` directories)
**Performance Goals**: Parse + display 500 rows in <10s (SC-001), recheck 100 rows in <5s (SC-003)
**Constraints**: Rate limit 5 uploads/hour, max 10MB file, max ~1000 rows per file
**Scale/Scope**: Single user per session, one active session per user, 7-day session expiry

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Compliance-First Development | ✅ PASS | Staging doesn't change FBR field structure; invoices created via existing `InvoiceService.create_invoice()` which already enforces FBR spec |
| Security by Design | ✅ PASS | JWT auth via `require_authentication`, row-level isolation by `user_id`, CSRF protection on all mutating endpoints, rate limiting inherited |
| Spec-Driven Implementation | ✅ PASS | All fields match FBR spec; no new FBR fields introduced |
| Data Integrity and Auditability | ✅ PASS | Staging rows deleted after commit (temporary data); final invoices stored with full audit trail in existing `invoices` table; FBR interactions unchanged |
| Environment Isolation | ✅ PASS | Staging uses same environment separation as invoices; no cross-contamination |
| No business logic in frontend | ✅ PASS | All validation logic in backend parser/service; frontend only renders and sends edits |
| All FBR communication via backend | ✅ PASS | No new FBR communication; commit uses existing `InvoiceService` |
| No hardcoded secrets | ✅ PASS | No new secrets introduced |

**Gate Result**: ✅ ALL PASS — proceed to implementation

## Project Structure

### Documentation (this feature)

```text
specs/005-async-excel-staging/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research decisions
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 quickstart guide
├── contracts/           # Phase 1 API contracts
│   └── staging-api.md
└── tasks.md             # Phase 2 output (/sp.tasks - NOT created yet)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── invoice.py                    # Existing - unchanged
│   │   └── excel_staging.py             # NEW - ExcelStagingSession + ExcelStagingRow
│   ├── schemas/
│   │   └── excel_staging.py             # NEW - Pydantic request/response schemas
│   ├── services/
│   │   ├── invoice_service.py            # Existing - unchanged
│   │   └── excel_staging_service.py     # NEW - staging business logic
│   ├── api/v1/
│   │   ├── invoices.py                   # Existing - MODIFY: add staging router or endpoints
│   │   └── excel_staging.py             # NEW (alternative): separate staging router
│   └── utils/
│       └── manual_excel_helper.py        # Existing - MODIFY: add parse_excel_for_staging()
├── alembic/versions/
│   └── XXXX_add_excel_staging_tables.py # NEW - migration
└── tests/
    ├── unit/
    │   ├── test_excel_staging_parser.py  # NEW - parser unit tests
    │   └── test_excel_staging_service.py # NEW - service unit tests
    └── integration/
        └── test_excel_staging_api.py     # NEW - API integration tests

frontend/
├── src/
│   ├── components/invoices/
│   │   ├── ManualExcelUploadForm.tsx     # Existing - MODIFY: multi-state staging flow
│   │   └── ExcelStagingGrid.tsx         # NEW - editable spreadsheet grid
│   ├── contexts/
│   │   └── ExcelStagingContext.tsx       # NEW - staging session state management
│   ├── lib/
│   │   ├── api.ts                        # Existing - MODIFY: add staging endpoints
│   │   └── api/
│   │       └── api-client.ts             # Existing - MODIFY: add staging methods
│   └── app/(protected)/invoices/
│       └── excel-staging/
│           └── [sessionId]/
│               └── page.tsx              # NEW - staging grid page
└── src/__tests__/
    ├── ExcelStagingGrid.test.tsx         # NEW - grid component tests
    └── ExcelStagingContext.test.tsx      # NEW - context tests
```

**Structure Decision**: Follow the existing project layout exactly. Put new backend models in `backend/src/models/`, new services in `backend/src/services/`, new API routes in `backend/src/api/v1/`, new frontend components in `frontend/src/components/invoices/`, new context in `frontend/src/contexts/`. No new top-level directories. Tests mirror the source structure under `backend/tests/` and `frontend/src/__tests__/`.

## Complexity Tracking

> No constitution violations. No complexity justifications needed.

## Implementation Phases

### Phase 1: Data Model & Migration (Tests First)

**Tests to write first:**
- `backend/tests/unit/test_excel_staging_parser.py` — Test `_validate_staging_row()` with valid rows, each error type (missing buyer name, negative quantity, future date, invalid income_tax, etc.)
- `backend/tests/unit/test_excel_staging_service.py` — Test session creation, row updates, status transitions

**Implementation:**

1. **NEW** `backend/src/models/excel_staging.py`
   - `ExcelStagingStatus` enum (parsing, ready_for_review, rechecking, committing, cancelled)
   - `ExcelStagingSession` SQLModel table with: id, user_id, original_filename, status, total_rows, valid_rows, errored_rows, created_at, updated_at
   - `ExcelStagingRow` SQLModel table with all 16 template fields + computed fields + seller fields + is_valid, is_dirty, field_errors JSON

2. **NEW** `backend/alembic/versions/XXXX_add_excel_staging_tables.py`
   - Create `excel_staging_session` table
   - Create `excel_staging_row` table with FK to session, indexes on user_id and session_id

3. **Register** model in `backend/src/models/__init__.py` (if exists) and `backend/alembic/env.py` for autogenerate

### Phase 2: Modified Parser (Tests First)

**Tests to write first:**
- Additional parser tests with real Excel files (use `openpyxl` to generate test .xlsx in pytest fixtures)
- Test multi-item invoice grouping, edge cases (empty file, sample-only file, large file)

**Implementation:**

4. **MODIFY** `backend/src/utils/manual_excel_helper.py`
   - Extract `_validate_staging_row(row_data, saved_items_dict, existing_invoice_numbers, seen_invoice_numbers, seller_info, today) -> dict` — returns `{"field_name": ["error"]}` or `{}`
   - Add `parse_excel_for_staging(file_source, user_id, db) -> list[dict]` — parses ALL rows, calls `_validate_staging_row()` per row, returns row dicts with `is_valid`, `field_errors`, computed fields populated
   - Extract `build_invoices_from_rows(valid_rows) -> list[dict]` — shared grouping logic reused by both old and new flows
   - Keep existing `parse_excel_for_manual_invoice()` unchanged for backward compatibility

### Phase 3: Service & API (Tests First)

**Tests to write first:**
- `backend/tests/integration/test_excel_staging_api.py` — HTTP tests for all 6 endpoints using `TestClient`

**Implementation:**

5. **NEW** `backend/src/schemas/excel_staging.py`
   - `StagingSessionResponse` — session without rows
   - `StagingSessionDetailResponse` — session with rows array
   - `StagingRowResponse` — single row with all fields + field_errors
   - `StagingRowUpdateRequest` — partial update (all fields optional)
   - `StagingRecheckResponse` — recheck result
   - `StagingCommitResponse` — commit result
   - `StagingActiveSessionsResponse` — active sessions list
   - `StagingCancelResponse` — cancel result

6. **NEW** `backend/src/services/excel_staging_service.py`
   - `create_session_from_rows(db, user_id, filename, rows) -> ExcelStagingSession`
   - `get_active_session(db, user_id) -> ExcelStagingSession | None`
   - `get_session(db, session_id, user_id) -> ExcelStagingSession`
   - `update_row(db, session_id, row_id, user_id, updates) -> ExcelStagingRow`
   - `recheck_session(db, session_id, user_id) -> (list[ExcelStagingRow], int, int, bool)`
   - `commit_session(db, session_id, user_id) -> (int, int, list, list)`
   - `cancel_session(db, session_id, user_id) -> None`
   - `_validate_single_row(db, row, saved_items_dict, ...) -> dict` — same logic as parser's validate function

7. **NEW** `backend/src/api/v1/excel_staging.py` (separate router) OR **MODIFY** `backend/src/api/v1/invoices.py` (add endpoints)
   - `POST /upload` — file upload, parse, create session, return summary
   - `GET /active` — get active sessions
   - `GET /{session_id}` — get session with rows
   - `PUT /{session_id}/rows/{row_id}` — update row cell
   - `POST /{session_id}/recheck` — re-validate dirty rows
   - `POST /{session_id}/commit` — create invoices, delete session
   - `DELETE /{session_id}` — cancel, delete session

8. **Register** new router in `backend/src/main.py` (or wherever routers are included)

### Phase 4: Frontend — Context & API (Tests First)

**Tests to write first:**
- `frontend/src/__tests__/ExcelStagingContext.test.tsx` — Test session recovery, localStorage persistence, polling

**Implementation:**

9. **MODIFY** `frontend/src/lib/api/api-client.ts`
   - Add `ExcelStagingService` class with methods: `uploadExcel()`, `getActiveSessions()`, `getSession()`, `updateRow()`, `recheck()`, `commit()`, `cancel()`

10. **MODIFY** `frontend/src/lib/api.ts`
    - Add `api.excelStaging` namespace with all staging endpoints

11. **NEW** `frontend/src/contexts/ExcelStagingContext.tsx`
    - Follow `BulkOperationContext.tsx` pattern
    - State: `activeSessions`, `currentSessionId`, `rows`, `status`, `isProcessing`
    - localStorage persistence of `currentSessionId`
    - Backend recovery on auth via `GET /active`
    - Polling every 3s during processing states
    - Functions: `uploadFile()`, `updateCell()`, `recheckSession()`, `commitSession()`, `cancelSession()`, `refreshSession()`

### Phase 5: Frontend — Grid & UI (Tests First)

**Tests to write first:**
- `frontend/src/__tests__/ExcelStagingGrid.test.tsx` — Test grid rendering with mock rows, cell editing, error display, button states

**Implementation:**

12. **NEW** `frontend/src/components/invoices/ExcelStagingGrid.tsx`
    - Spreadsheet-like table with columns matching Excel template
    - Error cells: red background + error tooltip on hover
    - Valid rows: green left-border indicator
    - Inline editing: click cell → `<Input>` or `<Select>` appears
    - Grouped rows by `group_key` (invoice_number) with visual separator
    - Summary bar: "X of Y rows valid" with progress indicator
    - Button bar: Cancel (always), Recheck (when errors exist), Upload All (when all valid)
    - Loading overlay during recheck/commit

13. **MODIFY** `frontend/src/components/invoices/ManualExcelUploadForm.tsx`
    - State machine: IDLE → PARSING → REVIEW → COMMITTING → COMPLETED
    - IDLE: File picker + Upload button (current UI, kept)
    - PARSING: Loading spinner
    - REVIEW: Renders `ExcelStagingGrid`
    - COMMITTING: Progress indicator
    - COMPLETED: Success summary + "View History" link + "Upload Another" button
    - Session recovery: on mount, check context for active session → jump to REVIEW

14. **NEW** `frontend/src/app/(protected)/invoices/excel-staging/[sessionId]/page.tsx`
    - Page component wrapping `ExcelStagingGrid` with context
    - Fetches session data on mount
    - Handles 404 (session deleted/expired) → redirect to upload
    - Handles session state recovery

15. **MODIFY** `frontend/src/app/(protected)/layout.tsx` (if needed)
    - Wrap with `ExcelStagingProvider` if not already wrapped at a higher level

## Implementation Order (Dependency Graph)

```
Phase 1 (Data Model) ─────────────────────────────────────────────┐
    │                                                              │
    ▼                                                              │
Phase 2 (Parser) ───────┐                                         │
    │                    │                                         │
    ▼                    ▼                                         │
Phase 3 (Service + API) ──── Phase 4 (Frontend Context + API) ─┐  │
                                  │                              │  │
                                  ▼                              │  │
                            Phase 5 (Frontend Grid + UI) ◄───────┘──┘
```

- Phase 1 blocks everything (data layer)
- Phases 2 and 3 are backend, sequential (parser → service → API)
- Phase 4 can start after Phase 1 (depends only on API contract, not implementation)
- Phase 5 depends on Phase 4 (context) and Phase 3 (API)

## Verification

After all phases complete:

1. **Run backend tests**: `cd backend && uv run pytest tests/ -v -k excel_staging`
2. **Run frontend tests**: `cd frontend && npx vitest run`
3. **Manual smoke test**: Follow quickstart.md flow (upload → edit → recheck → commit → verify in history)
4. **Persistence test**: Upload, navigate to Dashboard, return — verify session resumes
5. **Cleanup test**: After commit, verify `SELECT COUNT(*) FROM excel_staging_session` returns 0
6. **Cancel test**: Upload, click Cancel — verify session deleted
7. **Logout/login test**: Upload, logout, login, navigate to Excel upload — verify session resumes
8. **Edge case test**: Empty file, all-valid file, all-errored file, 500-row file
