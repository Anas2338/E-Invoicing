# Tasks: Non-blocking Bulk Invoice Operations

**Branch**: `004-async-bulk-operations`
**Input**: Design documents from `/specs/004-async-bulk-operations/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/bulk-operations-api.yaml

**Tests**: Tests are REQUIRED — write before implementation (TDD per user request).

**Organization**: Tasks grouped by user story for independent implementation and testing.

**Format**: `[ID] [P?] [Story] Description with file path`

---

## Phase 1: Foundational (Shared Infrastructure)

**Purpose**: Core DB model, schemas, and migration that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T001 Create `BulkOperationTask` SQLModel with enums (`BulkOperationType`, `BulkOperationStatus`) in `backend/src/models/bulk_operation.py`
- [X] T002 [P] Export `BulkOperationTask` from `backend/src/models/__init__.py`
- [X] T003 [P] Create request/response Pydantic schemas (`BulkValidateRequest`, `BulkPostRequest`, `BulkOperationResponse`, `BulkOperationStatusResponse`, `BulkOperationError`, `ActiveBulkTasksResponse`) in `backend/src/schemas/bulk_operation.py`
- [X] T004 Generate Alembic migration for `bulk_operation_task` table — run `uv run alembic revision --autogenerate -m "add bulk_operation_task"` and verify the generated migration creates all columns matching data-model.md

**Checkpoint**: Foundation ready — bulk_operation_task table exists, schemas available for service and endpoint code.

---

## Phase 2: US1 + US2 — Bulk Validation & Posting Service (Priority: P1) 🎯 MVP

**Goal**: Backend service that processes invoices one-by-one in the background, updating progress in the DB after each invoice. Covers both validate and post operations.

**Independent Test**: Write service tests that verify each invoice in a batch is processed, progress counters increment, errors are recorded per-invoice, and final status is set correctly.

### Tests for Bulk Operation Service (TDD — write first, ensure red)

- [X] T005 [P] [US1] Write `test_bulk_validate_service` — test that `BulkOperationService.bulk_validate_invoices` validates each invoice, increments processed_count, records errors, sets status to `completed` or `partially_completed` in `backend/tests/test_bulk_operation_service.py`
- [X] T006 [P] [US2] Write `test_bulk_post_service` — test that `BulkOperationService.bulk_post_invoices` posts each invoice via `PostingService`, updates counters, handles per-invoice failures, and sets correct terminal status in `backend/tests/test_bulk_operation_service.py`
- [X] T007 [P] [US1] Write `test_bulk_validate_partial_failure` — test that when some invoices fail validation, service continues processing remaining invoices and final status is `partially_completed` with correct error list in `backend/tests/test_bulk_operation_service.py`
- [X] T008 [P] [US2] Write `test_bulk_post_partial_failure` — test that when some invoices fail posting, service continues and records per-invoice FBR errors in `backend/tests/test_bulk_operation_service.py`
- [X] T009 [P] [US1] Write `test_bulk_validate_empty_batch` — test that service handles empty invoice list gracefully (sets status to `completed`, zero success/failure) in `backend/tests/test_bulk_operation_service.py`

### Implementation for Bulk Operation Service

- [X] T010 [US1] Implement `BulkOperationService.bulk_validate_invoices` async generator method that validates each invoice against FBR, updates `processed_count`, `success_count`, `failure_count`, `errors` in `backend/src/services/bulk_operation_service.py`
- [X] T011 [US2] Implement `BulkOperationService.bulk_post_invoices` async generator method that posts each validated invoice to FBR via `PostingService.post_single_invoice`, updates progress counters in `backend/src/services/bulk_operation_service.py`
- [X] T012 [US1] Implement `BulkOperationService.update_task_status` helper to atomically update task counters and set terminal status (`completed` / `partially_completed` / `failed`) in `backend/src/services/bulk_operation_service.py`
- [X] T013 [US1] Implement `BulkOperationService.get_task` — read single task by id + user_id (with 404 if not found) in `backend/src/services/bulk_operation_service.py`

**Checkpoint**: BulkOperationService processes invoices in background, updates DB counters, handles failures per-invoice.

---

## Phase 3: US1 + US2 — Bulk Operation Endpoints (Priority: P1) 🎯 MVP

**Goal**: REST endpoints that fire background operations and expose status polling.

**Independent Test**: Endpoint tests verify `POST` returns `task_id` immediately, `GET /bulk-task/{task_id}` returns progress, and auth guards work.

### Tests for Endpoints (TDD — write first, ensure red)

- [X] T014 [P] [US1] Write `test_bulk_validate_endpoint` — test that `POST /api/v1/invoices/bulk-validate` returns 200 with `task_id` and starts background processing in `backend/tests/test_bulk_operation_endpoints.py`
- [X] T015 [P] [US2] Write `test_bulk_post_endpoint` — test that `POST /api/v1/invoices/bulk-post` returns 200 with `task_id` and processes invoices in `backend/tests/test_bulk_operation_endpoints.py`
- [X] T016 [P] [US1] Write `test_bulk_task_status_endpoint` — test that `GET /api/v1/invoices/bulk-task/{task_id}` returns current progress with all fields (status, counters, progress_percentage) in `backend/tests/test_bulk_operation_endpoints.py`
- [X] T017 [P] [US2] Write `test_bulk_post_requires_environment` — test that `POST /api/v1/invoices/bulk-post` returns 422 when `environment` is missing in `backend/tests/test_bulk_operation_endpoints.py`
- [X] T018 [P] [US1] Write `test_bulk_endpoints_unauthorized` — test that all new endpoints return 401 when not authenticated in `backend/tests/test_bulk_operation_endpoints.py`
- [X] T019 [P] [US2] Write `test_bulk_task_status_not_found` — test that `GET /api/v1/invoices/bulk-task/nonexistent-uuid` returns 404 in `backend/tests/test_bulk_operation_endpoints.py`

### Implementation for Endpoints

- [X] T020 [P] [US1] Implement `POST /api/v1/invoices/bulk-validate` — creates `BulkOperationTask`, enqueues `BulkOperationService.bulk_validate_invoices` via `BackgroundTasks`, returns `BulkOperationResponse` in `backend/src/api/v1/invoices.py`
- [X] T021 [P] [US2] Implement `POST /api/v1/invoices/bulk-post` — creates `BulkOperationTask`, enqueues `BulkOperationService.bulk_post_invoices` via `BackgroundTasks`, returns `BulkOperationResponse` in `backend/src/api/v1/invoices.py`
- [X] T022 [P] [US1] Implement `GET /api/v1/invoices/bulk-task/{task_id}` — reads task from service, returns `BulkOperationStatusResponse` with computed `progress_percentage` in `backend/src/api/v1/invoices.py`
- [X] T023 [US1] Register all new endpoint imports and rate limiting at the top of `backend/src/api/v1/invoices.py`

**Checkpoint**: All 3 core backend endpoints working — bulk-validate, bulk-post, bulk-task status. Can test via Swagger UI.

---

## Phase 4: Frontend — API Client, Context & Progress UI (Priority: P1) 🎯 MVP

**Goal**: Frontend can initiate background operations, poll progress, and display real-time updates on the history page.

**Independent Test**: After this phase, a user can select invoices → click Validate → see immediate confirmation → see progress updates → navigate away and back → still see progress.

### Tests for Frontend (TDD — write first, ensure red)

- [X] T024 [P] [US1] Write `BulkOperationContext` tests — test `startOperation` registers a new operation, polling fetches status updates, `removeOperation` cleans up, and completed tasks auto-remove after timeout in `frontend/__tests__/BulkOperationContext.test.tsx`
- [X] T025 [P] [US1] Write `BulkOperationContext` localStorage persistence tests — test that operations survive in localStorage across component unmount/remount in `frontend/__tests__/BulkOperationContext.test.tsx`
- [X] T026 [P] [US1] Write `BulkOperationProgress` component tests — test that progress card renders operation type, progress bar, processed/success/failure counts, and completion state shows summary in `frontend/__tests__/BulkOperationProgress.test.tsx`

### Implementation for Frontend

- [X] T027 [P] [US1] Add 4 API functions (`bulkValidateBackground`, `bulkPostBackground`, `getBulkTaskStatus`, `getActiveBulkTasks`) to `api.invoices` in `frontend/src/lib/api.ts`
- [X] T028 [US1] Create `BulkOperationContext` and `BulkOperationProvider` with polling (every 3s), localStorage persistence, completed-task auto-removal (10s delay), and `useBulkOperation` hook in `frontend/src/contexts/BulkOperationContext.tsx`
- [X] T029 [US1] Create `BulkOperationProgress` component showing operation type badge, progress bar with percentage, processed/success/failure counts, completion summary with error details expandable, and dismiss button in `frontend/src/components/invoices/BulkOperationProgress.tsx`
- [X] T030 [US1] Wire `BulkOperationProvider` in `frontend/src/app/(protected)/layout.tsx` — wrap children alongside existing `UploadSessionProvider`
- [X] T031 [US1] Replace `handleBulkValidate` in history page — fire-and-forget via `bulkValidateBackground`, call `startOperation` from context, remove sequential `for...of` loop, clear selection, show toast in `frontend/src/app/(protected)/invoices/history/page.tsx`
- [X] T032 [US2] Replace `handleBulkPost` in history page — fire-and-forget via `bulkPostBackground`, call `startOperation` from context, remove synchronous bulkPost call, show toast in `frontend/src/app/(protected)/invoices/history/page.tsx`
- [X] T033 [US1] Add `BulkOperationProgress` rendering in history page below the action sidebar — show when any active bulk operations exist, use `useBulkOperation()` hook in `frontend/src/app/(protected)/invoices/history/page.tsx`
- [X] T034 [US1] Add completion toast listener — when operation status becomes `completed` or `partially_completed`, show a toast notification with success/failure summary on any page in `frontend/src/contexts/BulkOperationContext.tsx`

**Checkpoint**: Full MVP working — user can fire bulk operations, see progress, navigate freely, get completion toasts. Everything additive — existing features untouched.

---

## Phase 5: US3 — Recovery After Navigation (Priority: P2)

**Goal**: Operations survive page navigation and browser close/reopen. Active operations are recovered on mount.

**Independent Test**: Start a bulk operation, close the browser tab, reopen, log in, go to history page — see the operation's current progress. Navigate to dashboard and back — progress still visible.

### Implementation for Recovery

- [X] T035 [P] [US3] Implement `GET /api/v1/invoices/bulk-tasks/active` endpoint — returns all `processing` tasks for authenticated user in `backend/src/api/v1/invoices.py`
- [X] T036 [US3] Add recovery-on-mount in `BulkOperationContext` — on provider mount, fetch `GET /invoices/bulk-tasks/active` and re-register any still-processing tasks from backend in `frontend/src/contexts/BulkOperationContext.tsx`

### Tests for Recovery

- [X] T037 [P] [US3] Write `test_bulk_tasks_active_endpoint` — test that `GET /api/v1/invoices/bulk-tasks/active` returns only this user's processing tasks in `backend/tests/test_bulk_operation_endpoints.py`
- [X] T038 [P] [US3] Write `test_bulk_tasks_active_empty` — test that endpoint returns empty list when user has no active tasks in `backend/tests/test_bulk_operation_endpoints.py`

**Checkpoint**: Operations survive page navigation and tab close/reopen.

---

## Phase 6: US4 — Concurrent Operation Protection (Priority: P3)

**Goal**: Prevent starting a second bulk operation while one is already in progress for the same user.

**Independent Test**: Start a bulk validate, then try to start a bulk post — see error message "A bulk operation is already in progress."

### Tests for Concurrency Protection

- [X] T039 [P] [US4] Write `test_concurrent_operation_blocked` — test that starting a second bulk operation while one is processing returns 400 with appropriate error in `backend/tests/test_bulk_operation_endpoints.py`
- [X] T040 [P] [US4] Write `test_concurrent_operation_allowed_after_completion` — test that a new operation is accepted after the previous one has completed in `backend/tests/test_bulk_operation_endpoints.py`

### Implementation for Concurrency Protection

- [X] T041 [US4] Add active-operation check in bulk validate/post endpoints — query for existing `processing` tasks for this user, return 400 if found in `backend/src/api/v1/invoices.py`
- [X] T042 [US4] Add frontend guard — disable validate/post bulk buttons when any operation is active in `BulkOperationContext` (expose `hasActiveOperation`), show tooltip "Operation in progress" in `frontend/src/app/(protected)/invoices/history/page.tsx`

**Checkpoint**: Users cannot accidentally start conflicting operations.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, maintenance, and final validation.

- [X] T043 [P] Add cleanup job `cleanup_completed_bulk_tasks` to scheduler — runs every 10 minutes, deletes rows where `status IN ('completed','failed','partially_completed') AND completed_at < NOW() - 5 minutes` in `backend/src/services/scheduler.py`
- [X] T044 Update quickstart.md verification checklist — mark all tested items and confirm no regressions in existing functionality
- [X] T045 Run full test suite: `cd backend && uv run pytest tests/test_bulk_operation_service.py tests/test_bulk_operation_endpoints.py -v` and `cd frontend && npm run test -- __tests__/BulkOperationContext.test.tsx __tests__/BulkOperationProgress.test.tsx`

**Checkpoint**: DB stays clean, tests pass, feature ready for deployment.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Foundational) ─── blocks ──→ Phase 2 (Service)
                                            │
                                            ▼
                                     Phase 3 (Endpoints)
                                            │
                                            ▼
                                     Phase 4 (Frontend MVP)
                                            │
                              ┌─────────────┼─────────────┐
                              ▼             ▼             ▼
                        Phase 5 (US3)  Phase 6 (US4)  Phase 7 (Polish)
                        Recovery        Concurrency    Cleanup
```

- **Phase 1 (Foundational)**: No dependencies — can start immediately. BLOCKS all subsequent phases.
- **Phase 2 (Service)**: Depends on Phase 1. BLOCKS Phase 3.
- **Phase 3 (Endpoints)**: Depends on Phase 2. BLOCKS Phase 4.
- **Phase 4 (Frontend MVP)**: Depends on Phase 3. Independent of later phases.
- **Phase 5 (US3)**: Depends on Phase 3 (needs endpoints to exist). Can run in parallel with Phase 4 if staffed, but practically sequential since same files.
- **Phase 6 (US4)**: Depends on Phase 3 (needs endpoints to exist). Can be parallel with Phase 4 and Phase 5.
- **Phase 7 (Polish)**: Depends on all prior phases — needs everything implemented to validate.

### Within Each Phase

- Tests (marked TDD) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

| Task IDs | Parallel With | Reason |
|---|---|---|
| T002, T003, T004 | All in Phase 1 | Different files, no interdependency |
| T005–T009 | All in Phase 2 test group | Different test functions in same file are independent |
| T014–T019 | All in Phase 3 test group | Independent test functions |
| T020, T021, T022, T023 | All in Phase 3 impl | Different endpoint functions |
| T024, T025, T026 | All in Phase 4 test group | Context and Progress are separate test files |
| T027, T028, T029, T030 | All in Phase 4 impl | API client, context, component, layout are separate files |
| T031, T032, T033, T034 | All in Phase 4 impl part 2 | All edits to history page or context — sequential within page.tsx |
| T035, T037, T038 | Phase 5 | Backend endpoint + tests are independent |
| T039, T040, T041 | Phase 6 | Concurrency tests + implementation are independent |
| T043 | Phase 7 (with T044) | Scheduler cleanup is independent of doc updates |

---

## Parallel Execution Examples

### Phase 1 (Foundation)
```bash
# All three can be started in parallel:
Task: T001 — Create BulkOperationTask model
Task: T002 — Export model from __init__.py
Task: T003 — Create Pydantic schemas in schemas/bulk_operation.py
# T004 (migration) must wait for T001
```

### Phase 2 + 3 (Service Tests + Endpoints)
```bash
# All service tests can run in parallel in same file:
Task: T005 — test_bulk_validate_service
Task: T006 — test_bulk_post_service
Task: T007 — test_bulk_validate_partial_failure
Task: T008 — test_bulk_post_partial_failure
Task: T009 — test_bulk_validate_empty_batch

# After T010–T013 (service impl), run endpoint tests in parallel:
Task: T014 — test_bulk_validate_endpoint
Task: T015 — test_bulk_post_endpoint
Task: T016 — test_bulk_task_status_endpoint
Task: T017 — test_bulk_post_requires_environment
Task: T018 — test_bulk_endpoints_unauthorized
Task: T019 — test_bulk_task_status_not_found
```

### Phase 4 (Frontend - parallelizable files)
```bash
# Tests (parallel):
Task: T024 — Context tests
Task: T025 — localStorage persistence tests
Task: T026 — Progress component tests

# Implementation (parallel):
Task: T027 — API client functions (api.ts)
Task: T028 — BulkOperationContext (contexts/)
Task: T029 — BulkOperationProgress component
Task: T030 — Wire provider in layout.tsx

# History page edits (sequential — same file):
Task: T031 → T032 → T033
```

---

## Implementation Strategy

### MVP First (Phase 1 → Phase 2 → Phase 3 → Phase 4)

The MVP covers User Stories 1, 2, and the core of 3:

1. Complete Phase 1: Foundational (model + schemas + migration)
2. Complete Phase 2: Service tests + implementation
3. Complete Phase 3: Endpoint tests + implementation
4. Complete Phase 4: Frontend API context + progress UI + history page
5. **STOP and VALIDATE**: Test full flow in browser
6. **MVP DELIVERABLE**: Bulk validate and bulk post work in background with progress UI

### Incremental Delivery

| Increment | Phases | What's Working | Value |
|---|---|---|---|
| MVP | 1–4 | Background validate/post, progress, navigation survival | ✅ Core problem solved |
| Recovery | +5 | Browser close/reopen recovery | ✅ No lost results |
| Protection | +6 | Concurrent operation guard | ✅ Data integrity |
| Polish | +7 | Auto-cleanup, validation | ✅ Production ready |

### After MVP

Once Phase 4 is delivered and validated:
- Phase 5 (Recovery) adds the final piece of US3 — browser close/reopen recovery
- Phase 6 (Concurrency) adds US4 protection — polish for data integrity
- Phase 7 (Cleanup) ensures DB doesn't accumulate stale rows

---

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests FAIL before implementing (TDD)
- Commit after each task or logical group
- No modifications to existing endpoints, tables, or single-invoice operations
- All new backend endpoints require `require_authentication` dependency
- All function inputs and outputs must be annotated with types — never use `any`
