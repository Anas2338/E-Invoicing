# Research: Async Excel Staging with Inline Error Correction

**Feature**: 005-async-excel-staging  
**Date**: 2026-07-27

## 1. Existing Code Reuse Analysis

### Decision: Reuse `parse_excel_for_manual_invoice()` logic with a non-failing variant

**Rationale**: The existing parser in `backend/src/utils/manual_excel_helper.py` already implements all 15+ validation checks needed. Rather than rewriting, we extract the row-level validation into a reusable `_validate_staging_row()` function that returns per-field errors instead of raising `ValueError`. A new `parse_excel_for_staging()` function wraps this to parse ALL rows without failing.

**Alternatives considered**:
- Rewrite validation from scratch → wastes existing tested logic, risks regressions
- Add try/catch per row in existing parser → the existing function groups rows by invoice_number before validating; we need per-row validation for the grid

**Existing code reference**: `backend/src/utils/manual_excel_helper.py` lines 151–432

### Decision: Follow `BulkOperationTask` pattern for staging session model

**Rationale**: The existing `BulkOperationTask` model (`backend/src/models/bulk_operation.py`) demonstrates the project's established pattern for async, user-scoped, progress-trackable operations. We follow the same pattern: UUID primary key, `user_id` indexed FK, status enum, counters, JSON errors field, timestamps.

**Alternatives considered**:
- Store everything in a single JSON column → loses queryability, can't update individual rows
- Use a separate staging database (like automation DB) → adds deployment complexity; staging is temporary

**Existing code reference**: `backend/src/models/bulk_operation.py`

### Decision: Use `ExcelStagingContext` pattern from `BulkOperationContext`

**Rationale**: The existing `BulkOperationContext.tsx` (`frontend/src/contexts/BulkOperationContext.tsx`) already implements localStorage persistence, backend recovery on auth, polling at 3s intervals, and auto-cleanup of completed tasks. The staging context follows the exact same pattern.

**Alternatives considered**:
- Server-Sent Events (SSE) for real-time updates → overengineered for this use case; polling at 3s is sufficient
- WebSocket → adds infrastructure complexity; not needed

**Existing code reference**: `frontend/src/contexts/BulkOperationContext.tsx`

### Decision: Extract invoice grouping logic into shared helper

**Rationale**: The existing `parse_excel_for_manual_invoice()` groups rows by `invoice_number` and builds invoice dicts (lines 394–432). Both the old upload endpoint and the new commit flow need this grouping logic. We extract a `build_invoices_from_rows()` function that both can call.

**Existing code reference**: `backend/src/utils/manual_excel_helper.py` lines 394–432

### Decision: Use existing `InvoiceService.create_invoice()` for commit

**Rationale**: The `InvoiceService.create_invoice()` method handles deduplication, NTN/CNIC cleaning, item normalization, and status setting. No need to duplicate this logic.

**Existing code reference**: `backend/src/services/invoice_service.py` line 93

## 2. Technology Decisions

### Decision: Inline cell editing via controlled inputs (no library)

**Rationale**: The project already uses shadcn/ui components extensively. Inline editing can be built with standard `<Input>` and `<Select>` components triggered on cell click. No need for a heavy spreadsheet library (e.g., Handsontable, AG Grid) for this use case — the grid is read-mostly with occasional cell edits, not a full spreadsheet.

**Alternatives considered**:
- Handsontable → adds ~500KB bundle, overkill for simple inline editing
- AG Grid Community → adds ~300KB, complex API for simple needs
- Custom contentEditable divs → fragile, cross-browser issues

### Decision: Backend uses BackgroundTasks for async operations

**Rationale**: The existing `BulkOperationService` already uses FastAPI `BackgroundTasks` for async processing. Parse, recheck, and commit all follow this same pattern — they run in the background while the frontend polls for status.

**Alternatives considered**:
- Celery task queue → adds Redis dependency, overkill for single-user staging sessions
- APScheduler → used by AI agent for scheduled tasks, not request-triggered work

### Decision: Backend uses uv for package management

**Rationale**: Per user instruction. `uv` is significantly faster than pip and provides deterministic lock files. Commands: `uv pip install`, `uv pip compile`.

### Decision: Tests written before implementation

**Rationale**: Per user instruction. Each phase produces tests first, then implementation. Tests are organized:
- `backend/tests/unit/test_excel_staging_parser.py` — parser unit tests
- `backend/tests/unit/test_excel_staging_service.py` — service unit tests
- `backend/tests/integration/test_excel_staging_api.py` — API integration tests
- `frontend/src/__tests__/ExcelStagingGrid.test.tsx` — component tests

## 3. Architecture Decisions

### Decision: Two-table design (session + rows) rather than single JSON column

**Rationale**: A separate `excel_staging_row` table allows per-row updates, per-row querying, and efficient recheck (only fetch modified rows). A single JSON column would require full read-modify-write cycles and lose database-level integrity.

**Alternatives considered**:
- Single table with JSON column → simpler schema but cannot update individual rows atomically
- Redis for staging → adds infrastructure dependency, staging data should be durable

### Decision: Delete on commit/cancel, not soft-delete

**Rationale**: Staging data is temporary by definition. Once committed to the main `invoices` table, the staging copy has zero value. Soft-delete would bloat the database unnecessarily. The spec (FR-025, FR-028) explicitly requires deletion.

### Decision: Only one active session per user

**Rationale**: Simpler UI, avoids confusion about which session to resume. If a user uploads a new file while one is in progress, the old one is automatically deleted and replaced. Per spec assumption #1 and FR-032.

### Decision: 7-day expiry for abandoned sessions

**Rationale**: Sessions older than 7 days are stale and unlikely to be resumed. A simple `WHERE created_at > NOW() - INTERVAL '7 days'` filter handles this without a scheduled cleanup job (though one can be added later).

## 4. Testing Strategy

### Backend tests (pytest)
1. **Parser unit tests**: Test `_validate_staging_row()` with valid rows, each error type, edge cases
2. **Service unit tests**: Test `ExcelStagingService` methods with mocked DB
3. **API integration tests**: Test each staging endpoint end-to-end with test DB

### Frontend tests (Vitest + Testing Library)
1. **Grid component tests**: Render grid with mock rows, test cell editing, error display
2. **Context tests**: Test session recovery, localStorage persistence
3. **API client tests**: Mock fetch, test staging API methods

### Testing order per phase:
- Phase 1 (Data model): Test model creation, validation, state transitions
- Phase 2 (Parser): Test `parse_excel_for_staging()` with sample Excel files
- Phase 3 (Service + API): Test endpoints with HTTP client
- Phase 4 (Frontend): Test components with mock data
