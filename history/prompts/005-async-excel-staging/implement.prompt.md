---
id: PHR-005-implement-001
title: async-excel-staging-implement
stage: green
date: 2026-07-27
surface: claude-code
model: deepseek-v4-flash
feature: 005-async-excel-staging
branch: 005-async-excel-staging
user: Muhammad Anus
command: /sp.implement
labels: [implement, excel, staging, backend, frontend]
links:
  spec: specs/005-async-excel-staging/spec.md
  plan: specs/005-async-excel-staging/plan.md
  tasks: specs/005-async-excel-staging/tasks.md
  data-model: specs/005-async-excel-staging/data-model.md
  contracts: specs/005-async-excel-staging/contracts/staging-api.md
  adr: ''
  pr: ''
files:
  - backend/src/models/excel_staging.py — ExcelStagingSession + ExcelStagingRow SQLModel tables
  - backend/src/schemas/excel_staging.py — 10 Pydantic request/response schemas
  - backend/src/services/excel_staging_service.py — ExcelStagingService (7 methods)
  - backend/src/api/v1/excel_staging.py — API router (7 endpoints)
  - backend/src/utils/manual_excel_helper.py — _validate_staging_row, parse_excel_for_staging, build_invoices_from_rows, _compute_staging_fields
  - backend/alembic/versions/20260727_add_excel_staging_tables.py — DB migration
  - backend/alembic/env.py — Updated with SQLModel metadata
  - backend/src/models/__init__.py — Registered staging models
  - backend/src/main.py — Registered staging router
  - backend/tests/conftest.py — Updated import reference
  - backend/tests/test_excel_staging_models.py — 16 model tests
  - backend/tests/test_excel_staging_parser.py — 32 parser tests (unit + integration)
  - backend/tests/test_excel_staging_api.py — 13 API integration tests
  - frontend/src/contexts/ExcelStagingContext.tsx — React context with polling + recovery
  - frontend/src/components/invoices/ExcelStagingGrid.tsx — Editable spreadsheet grid component
  - frontend/src/components/invoices/ManualExcelUploadForm.tsx — Multi-state upload form (rewritten)
  - frontend/src/app/(protected)/invoices/excel-staging/[sessionId]/page.tsx — Staging session page
  - frontend/src/app/(protected)/layout.tsx — Added ExcelStagingProvider
  - frontend/src/lib/api/api-client.ts — ExcelStagingService class
  - frontend/src/lib/api.ts — excelStaging namespace
tests:
  - 16 model tests (test_excel_staging_models.py)
  - 32 parser tests (test_excel_staging_parser.py)
  - 13 API integration tests (test_excel_staging_api.py)
---

## Prompt

/sp.implement

## Response snapshot

Implemented the full async Excel staging feature across all 7 phases:

**Phase 1 (Setup)**: Verified environment, installed backend dependencies with `uv sync`.

**Phase 2 (Data Model)**: Created `ExcelStagingSession` + `ExcelStagingRow` SQLModel tables with all columns from data-model.md (UUID PKs, status enum, 16 template fields, computed fields, seller fields, field_errors JSON). Generated Alembic migration for PostgreSQL. Registered models in `__init__.py` and `alembic/env.py`. Wrote 16 model tests covering defaults, status, serialization, and relationships.

**Phase 3 (Parser)**: Extracted `_validate_staging_row()` returning per-field error dicts. Added `parse_excel_for_staging()` that never raises — captures ALL rows with field-level errors. Added `_compute_staging_fields()` for financial calculations. Added `build_invoices_from_rows()` for grouping. Wrote 32 tests (unit + real .xlsx integration).

**Phase 4 (Service & API)**: Created `ExcelStagingService` with 7 methods (create, get_active, get_session, update_row, recheck, commit, cancel). Created API router with 7 endpoints matching contracts/staging-api.md. Registered in main.py. Wrote 13 API integration tests using TestClient + clean test engine. Removed deprecated test_manual_excel_upload_api.py.

**Phase 5 (Frontend Context)**: Created `ExcelStagingContext` following `BulkOperationContext` pattern — localStorage persistence, backend recovery, 3s polling. Added `ExcelStagingService` class to api-client.ts. Added `excelStaging` namespace to api.ts.

**Phase 6 (Frontend UI)**: Created `ExcelStagingGrid` — editable spreadsheet with 16 columns, red error indicators, inline editing (input/select), group separators, progress bar, cancel/recheck/upload buttons. Rewrote `ManualExcelUploadForm` as 4-state component (IDLE→PARSING→REVIEW→COMPLETED). Created staging session page. Added `ExcelStagingProvider` to layout.

**Phase 7 (Validation)**: All 61 backend tests pass.

## Outcome

- ✅ Impact: Complete async Excel staging flow — upload → view all rows with per-field errors → edit inline → recheck → upload all as DRAFT → clean up. Session persistence across navigation/logout.
- 🧪 Tests: 61 backend tests (16 model + 32 parser + 13 API) — all passing
- 📁 Files: 12 new files + 6 modified files across backend and frontend
- 🔁 Next prompts: Manual smoke test via quickstart.md, frontend TypeScript compilation check
- 🧠 Reflection: Followed user's three directives (existing structure, uv for backend, tests first). Skipped T019/T023 frontend tests due to missing vitest framework — would need `npx vitest init` setup.

## Evaluation notes (flywheel)

- Failure modes observed: SQLModel `primary_key=True` conflicts with `sa_column`; `sa_column` overrides Field `default` for primitive types; INV-001 filtering affects user data (existing behavior, not changed)
- Graders run and results (PASS/FAIL): All 61 backend tests PASS
- Prompt variant (if applicable): standard /sp.implement
- Next experiment (smallest change to try): Manual smoke test with real Excel upload
