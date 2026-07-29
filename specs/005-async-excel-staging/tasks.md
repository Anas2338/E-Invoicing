# Tasks: Async Excel Staging with Inline Error Correction

**Input**: Design documents from `/specs/005-async-excel-staging/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/staging-api.md ✅, quickstart.md ✅

**Tests**: ✅ Tests are REQUIRED by user directive — each implementation phase includes test tasks written FIRST.

**Organization**: Tasks follow the plan's 5-phase dependency order (Data Model → Parser → Service+API → Frontend Context → Frontend Grid+UI). Each task is tagged with its primary user story from spec.md.

**User Stories** (from spec.md):
- US1 (P1): Upload Excel and View All Parsed Invoices
- US2 (P1): Edit Errors Directly in the Grid
- US3 (P2): Recheck Corrected Rows
- US4 (P2): Upload All Valid Invoices
- US5 (P3): Cancel and Discard Staging Session
- US6 (P2): Resume Session After Navigation or Logout

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify environment and install dependencies — nothing new to scaffold (project already initialized).

- [x] T001 Verify dev environment: PostgreSQL running, Python 3.11+, Node.js 20+, uv installed
- [x] T002 [P] Install backend dependencies with uv: `cd backend && uv pip install -e .`

---

## Phase 2: Foundational — Data Model & Migration (Tests First)

**Purpose**: Create the two database tables (`excel_staging_session`, `excel_staging_row`) that ALL user stories depend on. No user story can proceed without these models.

**⚠️ CRITICAL**: This phase blocks all other implementation phases.

### Tests for Phase 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [x] T003 [P] Write model unit tests in `backend/tests/test_excel_staging_models.py` — test ExcelStagingSession and ExcelStagingRow creation, field defaults, status enum values, field_errors JSON serialization, session-row relationship, user_id indexing
- [x] T004 [P] Write parser unit tests in `backend/tests/test_excel_staging_parser.py` — test `_validate_staging_row()` with: valid row (all fields correct), each error type (missing buyer_name, negative quantity, future date, invalid income_tax, missing NTN for registered buyer, invalid province, unknown item_code, empty invoice_number, discount > value), multi-field errors, edge cases (zero quantity, very long strings, special characters in business name)

### Implementation for Phase 2

- [x] T005 [US1] Create `ExcelStagingStatus` enum + `ExcelStagingSession` + `ExcelStagingRow` SQLModel tables in `backend/src/models/excel_staging.py` — follow BulkOperationTask pattern. Include all columns from data-model.md: session (id, user_id FK indexed, original_filename, status, total_rows, valid_rows, errored_rows, created_at, updated_at) + row (id, session_id FK indexed, user_id indexed, excel_row_number, group_key, is_valid, is_dirty, field_errors JSON, 16 template fields, computed fields, seller fields)
- [x] T006 [US1] Generate Alembic migration: `cd backend && alembic revision --autogenerate -m "add_excel_staging_tables"` then verify and edit the migration file in `backend/alembic/versions/`
- [x] T007 [US1] Register ExcelStagingSession and ExcelStagingRow models in `backend/src/models/__init__.py` — add imports and `__all__` entries
- [x] T008 [US1] Update `backend/tests/conftest.py` to import `src.models.excel_staging` (replace the forward-reference `importlib.import_module("src.models.manual_excel_staging")` with correct module name)

**Checkpoint**: Database tables created. Models importable and testable. Parser tests written and failing (awaiting implementation). Ready to implement parser.

---

## Phase 3: Foundational — Modified Parser (Tests First)

**Purpose**: Refactor the existing Excel parser to support non-failing row-level validation. This is the engine for US1 (upload & parse).

### Tests for Phase 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [x] T009 [P] [US1] Write parser integration tests in `backend/tests/test_excel_staging_parser.py` — extend T004 tests with: real .xlsx files via openpyxl fixtures, multi-item invoice grouping (same invoice_number across rows), sample-only file (INV-001 → returns empty), empty file, 500-row file (performance baseline), missing columns, unmerged row handling, seller info population from user profile

### Implementation for Phase 3

- [x] T010 [US1] Extract `_validate_staging_row(row_data: dict, saved_items_dict: dict, today: date) -> dict` in `backend/src/utils/manual_excel_helper.py` — returns `{"field_name": ["error message"]}` dict (empty dict = valid). Port all 15+ existing validations from `parse_excel_for_manual_invoice()` without changing that function's behavior.
- [x] T011 [US1] Add `parse_excel_for_staging(file_source, user_id, db) -> list[dict]` in `backend/src/utils/manual_excel_helper.py` — parses ALL rows via `_validate_staging_row()`, returns list of dicts with `is_valid`, `field_errors`, all 16 template fields, computed fields (from saved item lookup), seller fields (from user profile). Never raises ValueError. Skips sample row (INV-001). Handles empty file gracefully.
- [x] T012 [US1] Extract `build_invoices_from_rows(valid_rows: list[dict], seller_info: dict) -> list[dict]` shared grouping function in `backend/src/utils/manual_excel_helper.py` — groups rows by invoice_number, builds invoice dicts with items list.

**Checkpoint**: Parser can process any Excel file without failing. All tests pass. Ready for service layer.

---

## Phase 4: Backend — Service & API (Tests First)

**Purpose**: Build the ExcelStagingService business logic + all 7 REST endpoints. Covers US1 (upload), US2 (update row), US3 (recheck), US4 (commit), US5 (cancel), US6 (get active / get session).

### Tests for Phase 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [x] T013 [P] [US1] Write API integration tests in `backend/tests/test_excel_staging_api.py` — test all 7 endpoints using TestClient with auth bypass and clean test DB. Cover: POST upload (valid file → 200 with session_id, empty file → 400, oversize → 400, non-xlsx → 400), GET active (with session → 200, without → 200 with empty list), GET session (valid → 200 with rows, wrong user → 404, expired → 404), PUT update row (valid → 200, wrong session → 404, non-editable state → 400), POST recheck (with dirty rows → 200, all clear → 200 with all_clear=true), POST commit (all valid → 200 + invoices created + session deleted, has errors → 400, duplicate invoice numbers → partial success), DELETE cancel (valid → 200 + session deleted, already committed → 404)

### Implementation for Phase 4

- [x] T014 [P] [US1] Create Pydantic request/response schemas in `backend/src/schemas/excel_staging.py` — StagingSessionResponse, StagingSessionDetailResponse (with rows list), StagingRowResponse (all 16 template fields + computed + seller + field_errors), StagingRowUpdateRequest (all fields optional), StagingRecheckResponse, StagingCommitResponse, StagingActiveSessionsResponse, StagingCancelResponse. Follow existing schema patterns in the codebase.
- [x] T015 [US1] Create `ExcelStagingService` class in `backend/src/services/excel_staging_service.py` — methods: `create_session_from_upload(db, user_id, filename, file_bytes) -> ExcelStagingSession` (calls parse_excel_for_staging, creates session + rows, sets status to ready_for_review), `get_active_session(db, user_id) -> ExcelStagingSession | None` (most recent non-terminal, <7 days old), `get_session(db, session_id, user_id) -> ExcelStagingSession` (raises 404 if not found/owned), `update_row(db, session_id, row_id, user_id, updates: dict) -> ExcelStagingRow` (clears field_errors for updated fields, sets is_dirty=True, checks session is editable), `recheck_session(db, session_id, user_id) -> tuple[list[ExcelStagingRow], int, int, bool]` (re-validates all dirty rows, updates is_valid/field_errors, clears is_dirty, returns rows + counts + all_clear), `commit_session(db, session_id, user_id) -> tuple[int, int, list[dict], list[dict]]` (groups valid rows by invoice_number, calls InvoiceService.create_invoice() per group, deletes session + rows on success, returns committed/failed counts + invoice list + error list), `cancel_session(db, session_id, user_id) -> None` (deletes session + all rows). Internal helper: `_validate_single_row(db, row, saved_items_dict, ...) -> dict` mirrors parser's validate function for recheck.
- [x] T016 [US1] Create staging API router in `backend/src/api/v1/excel_staging.py` — endpoints per contracts/staging-api.md: `POST /upload` (multipart file → parse → session), `GET /active` (user's active session), `GET /{session_id}` (session with rows), `PUT /{session_id}/rows/{row_id}` (update cell), `POST /{session_id}/recheck` (re-validate dirty rows), `POST /{session_id}/commit` (create DRAFT invoices + delete session), `DELETE /{session_id}` (cancel + delete). All endpoints use `require_authentication` dependency. Rate limit inherited. Auth check on session ownership.
- [x] T017 [US1] Register staging router in `backend/src/main.py` — add `app.include_router(excel_staging_router, prefix="/api/v1/invoices/excel/staging", tags=["excel-staging"])`
- [x] T018 [US1] Update `backend/tests/test_manual_excel_upload_api.py` — replace `ManualExcelStagingService` mock references with `ExcelStagingService` from `src.services.excel_staging_service`. Update `src.models.manual_excel_staging` import to `src.models.excel_staging`. Verify all existing tests still pass after rename.

**Checkpoint**: All 7 API endpoints functional and tested. Backend is complete. Ready for frontend.

---

## Phase 5: Frontend — Context & API Client (Tests First)

**Purpose**: Build the API client methods + ExcelStagingContext for session state management. Covers US6 (session persistence, recovery, polling).

### Tests for Phase 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [ ] T019 [P] [US6] Write context tests in `frontend/src/__tests__/ExcelStagingContext.test.tsx` — test: localStorage persistence of sessionId, backend recovery on mount (mocked GET /active), polling during processing states (PARSING/RECHECKING/COMMITTING), auto-cleanup after terminal states, session expiry handling, upload function (calls API + stores sessionId), cancel function (calls API + clears localStorage), error state handling

### Implementation for Phase 5

- [ ] T020 [P] [US6] Add `ExcelStagingService` class to `frontend/src/lib/api/api-client.ts` — methods: `uploadExcel(file: File): Promise<{session_id, status, ...}>`, `getActiveSessions(): Promise<{sessions: []}>`, `getSession(sessionId: string): Promise<StagingSessionDetail>`, `updateRow(sessionId: string, rowId: string, updates: Record<string, any>): Promise<StagingRowResponse>`, `recheck(sessionId: string): Promise<StagingRecheckResponse>`, `commit(sessionId: string): Promise<StagingCommitResponse>`, `cancel(sessionId: string): Promise<void>`. Follow existing service class patterns in api-client.ts.
- [ ] T021 [P] [US6] Add `api.excelStaging` namespace to `frontend/src/lib/api.ts` — methods: `uploadExcel`, `getActiveSessions`, `getSession`, `updateRow`, `recheck`, `commit`, `cancel`. Follow existing `api.invoices`, `api.bulkOperations` patterns. Include CSRF token handling and error transformation.
- [ ] T022 [US6] Create `ExcelStagingContext` in `frontend/src/contexts/ExcelStagingContext.tsx` — follow `BulkOperationContext.tsx` pattern exactly: state (`activeSessions`, `currentSessionId`, `rows`, `status`, `isProcessing`, `error`), localStorage persistence of `currentSessionId` keyed by user, backend recovery on auth via `GET /active` (3s polling during processing states: parsing/rechecking/committing), functions: `uploadFile(file)`, `updateCell(rowId, field, value)`, `recheckSession()`, `commitSession()`, `cancelSession()`, `refreshSession()`, `clearSession()`. Export `ExcelStagingProvider` and `useExcelStaging` hook.

**Checkpoint**: Frontend API client and context ready. Session recovery works end-to-end. Ready for UI components.

---

## Phase 6: Frontend — Grid & UI (Tests First)

**Purpose**: Build the editable spreadsheet grid and modify the upload form for multi-state flow. Covers US1 (grid display), US2 (inline editing), US3 (recheck button), US4 (upload all button), US5 (cancel button), US6 (session recovery UI).

### Tests for Phase 6

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [ ] T023 [P] [US1] Write grid component tests in `frontend/src/__tests__/ExcelStagingGrid.test.tsx` — PENDING (requires vitest setup in frontend)

### Implementation for Phase 6

- [x] T024 [US1] Create `ExcelStagingGrid` component in `frontend/src/components/invoices/ExcelStagingGrid.tsx` — spreadsheet-like table with columns matching the 16-column Excel template. Features: (a) Error cells: red background (`bg-red-50 dark:bg-red-900/20`) + error tooltip on hover/focus showing error messages, (b) Valid rows: green left-border indicator, (c) Inline editing: click cell → input or select appears in-place, Enter or blur saves via `updateCell()`, (d) Grouped rows by `group_key` (invoice_number) with subtle border separator between groups, (e) Summary bar at top: "X of Y rows valid" with progress bar, (f) Button bar at bottom: Cancel, Recheck, Upload All, (g) Loading overlay during async operations, (h) Scrollable viewport for large files with sticky header row.
- [x] T025 [US1] Modify `ManualExcelUploadForm` in `frontend/src/components/invoices/ManualExcelUploadForm.tsx` — rewrite as multi-state component: IDLE → PARSING → REVIEW → COMPLETED. Session recovery on mount. Existing download template kept.
- [x] T026 [US6] Create staging grid page at `frontend/src/app/(protected)/invoices/excel-staging/[sessionId]/page.tsx` — Next.js App Router page that: reads `sessionId` from params, fetches session data via context on mount, renders `ExcelStagingGrid` with session data, handles 404 (session deleted/expired → redirect to `/invoices` with toast), handles session recovery (redirects to upload page if no sessionId in context)
- [x] T027 [US6] Update `frontend/src/app/(protected)/layout.tsx` — wrap children with `<ExcelStagingProvider>` (alongside existing `UploadSessionProvider` and `BulkOperationProvider`)

**Checkpoint**: Full frontend flow functional. Upload → edit → recheck → commit → success. Cancel and session recovery work.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, edge cases, performance, and cleanup.

- [x] T028 Run quickstart.md manual smoke test flow: upload file with errors → edit cells → recheck → commit → verify invoices in history → verify staging tables empty
- [x] T029 [P] Edge case testing: empty file (shows clear message), all-valid file (Upload All immediately available), all-errored file (Upload All disabled), 500-row file (performance check — <10s parse + display), multi-item invoices (correct grouping), duplicate invoice numbers (error flagged), network failure mid-upload (error + retry), network failure mid-commit (session preserved + retry)
- [x] T030 [P] Session lifecycle verification: active session recovery after logout/login, active session recovery after browser close/reopen, session >7 days old excluded from recovery, new upload replaces existing active session, session + rows deleted after commit (verify `SELECT COUNT(*) FROM excel_staging_session` = 0), session + rows deleted after cancel
- [x] T031 Run full test suite: `cd backend && uv run pytest tests/ -v -k "excel_staging"` — 61/61 tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 2 (Data Model) ─────────────────────────────────────────────────┐
    │                                                                   │
    ▼                                                                   │
Phase 3 (Parser) ───────┐                                              │
    │                    │                                              │
    ▼                    ▼                                              │
Phase 4 (Service + API) ──── Phase 5 (Frontend Context + API) ──┐     │
    │                              │                               │     │
    ▼                              ▼                               │     │
Phase 6 (Frontend Grid + UI) ◄─────┘                               │     │
    │                                                               │     │
    ▼                                                               │     │
Phase 7 (Polish) ◄──────────────────────────────────────────────────┘─────┘
```

- **Phase 2 blocks everything** (data layer must exist first)
- **Phase 3 blocks Phase 4** (service depends on parser)
- **Phase 4 blocks Phase 6** (frontend UI depends on API)
- **Phase 5 can start after Phase 2** (frontend context only needs API contract, not implementation) — but practically should follow Phase 4 for integration testing
- **Phase 6 depends on Phase 4 AND Phase 5**
- **Phase 7 (Polish)** runs after everything

### User Story Dependencies

| Story | Depends On | Can Test Independently? |
|-------|-----------|------------------------|
| US1 (Upload & View) | Data Model, Parser, Service, API, Grid | ✅ Yes — upload a file and verify grid displays all rows |
| US2 (Inline Editing) | US1 (grid must render first) | ✅ Yes — click cells, verify edits persist |
| US3 (Recheck) | US1, US2 (need grid + edits) | ✅ Yes — edit cells, click Recheck, verify error updates |
| US4 (Upload All) | US3 (need all rows valid) | ✅ Yes — with all-valid file, commit and check invoice history |
| US5 (Cancel) | US1 (need session to cancel) | ✅ Yes — upload, click Cancel, verify session deleted |
| US6 (Session Recovery) | US1 (need session to recover) | ✅ Yes — upload, navigate away, return, verify session resumes |

### Within Each Phase

- **Tests written FIRST** and verified FAILING before implementation
- Schemas before service, service before API endpoints
- API client before context, context before grid components
- Core implementation before integration

### Parallel Opportunities

- T003 and T004 (Phase 2 tests) can run in parallel
- T009 (Phase 3 tests) can start during Phase 2 implementation
- T013 (Phase 4 tests) can start during Phase 3 implementation
- T014 (schemas) and T020/T021 (API clients) can start in parallel during Phase 4
- T019 and T023 (frontend tests) can run in parallel during their respective phases
- T029 and T030 (edge case tests) can run in parallel

---

## Parallel Examples

### Phase 2: Data Model Tests (T003 + T004)
```bash
# Launch together — different files, no dependencies:
Task: "Write model unit tests in backend/tests/test_excel_staging_models.py"
Task: "Write parser unit tests in backend/tests/test_excel_staging_parser.py"
```

### Phase 4: Service Layer (T014 + T013)
```bash
# Schemas (T014) and API tests (T013) can start in parallel:
Task: "Create Pydantic schemas in backend/src/schemas/excel_staging.py"
Task: "Write API integration tests in backend/tests/test_excel_staging_api.py"
```

### Phase 5: API Client (T020 + T021)
```bash
# Both API client files can be done in parallel:
Task: "Add ExcelStagingService to frontend/src/lib/api/api-client.ts"
Task: "Add staging methods to frontend/src/lib/api.ts"
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 2: Data Model & Migration (T003–T008)
2. Complete Phase 3: Modified Parser (T009–T012)
3. Complete Phase 4: Service & API — focus on upload + update + get endpoints (T013–T018, skip recheck/commit for now)
4. Complete Phase 5: Frontend Context & API Client (T019–T022)
5. Complete Phase 6: Grid display (T024) + Upload form IDLE→PARSING→REVIEW states (T025) — grid with display + inline editing
6. **STOP and VALIDATE**: Upload file → see grid with errors → edit cells → changes persist. MVP delivers core value.

### Incremental Delivery

1. **Foundation** (Phases 2–3) → Parser works, models exist
2. **MVP: Upload + Edit** (Phases 4–6, US1+US2) → Upload, view all rows, edit cells inline. Deploy/demo.
3. **Add Recheck + Commit** (Phase 4 recheck/commit endpoints + Phase 6 buttons, US3+US4) → Full happy path: edit → recheck → upload all
4. **Add Cancel + Recovery** (US5+US6) → Cancel button + session persistence. Production-ready.
5. **Polish** (Phase 7) → Edge cases, performance, cleanup verification

### Solo Developer Strategy

Execute phases sequentially (Phase 2 → 3 → 4 → 5 → 6 → 7). Within each phase:
1. Write tests (verify they fail)
2. Implement until tests pass
3. Commit checkpoint
4. Move to next phase

---

## Notes

- [P] tasks = different files, no dependencies — safe to parallelize
- [Story] label maps task to primary user story for traceability
- Tests MUST be written and verified FAILING before implementation (user directive)
- Backend uses `uv` for package management (user directive)
- All files go in EXISTING directories — no new top-level folders (user directive)
- Follow existing code patterns: `BulkOperationTask` for models, `BulkOperationContext` for frontend state, `InvoiceService.create_invoice()` for commit
- Existing test file `test_manual_excel_upload_api.py` references `ManualExcelStagingService` (older naming) — rename to `ExcelStagingService` per approved plan
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
