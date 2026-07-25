# Implementation Plan: Non-blocking Bulk Invoice Operations

**Branch**: `004-async-bulk-operations` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-async-bulk-operations/spec.md`

## Summary

Convert bulk validation and bulk posting on the invoice history page from synchronous blocking operations to a fire-and-forget + polling pattern. The backend processes invoices in background tasks and exposes status endpoints; the frontend fires the operation, immediately frees the UI, and polls for progress. This is the same pattern already used by the AI agent's Excel upload flow (`BackgroundValidationService` + `UploadSessionContext`), adapted for the main backend.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5 (frontend)
**Package Manager**: uv (backend), npm (frontend)
**Primary Dependencies**: FastAPI, SQLModel, Alembic (backend); Next.js 16 App Router, React 19, TanStack React Query 5, React Hook Form 7 + Zod 4 (frontend)
**Storage**: Neon PostgreSQL (backend), Neon PostgreSQL (AI agent DB — not touched)
**Testing**: pytest + pytest-asyncio + httpx (backend), Vitest + @testing-library/react (frontend)
**Target Platform**: Linux server (Docker Compose)
**Project Type**: web (backend/ + frontend/ — no changes to ai-agent/)
**Performance Goals**: UI freed within 2s of clicking bulk action; progress polling every 3s
**Constraints**: Must not modify existing endpoints, tables, or single-invoice operations (additive only)
**Scale/Scope**: Typical bulk batches of 5–50 invoices per operation; one operation per user at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| Compliance-First | ✅ PASS | FBR validation/posting logic reused unchanged from existing services (`PostingService.post_single_invoice`, existing validate endpoint) |
| Security by Design | ✅ PASS | All new endpoints use `require_authentication` dependency; `user_id` isolation enforced on bulk task queries; no new auth bypass |
| Spec-Driven Implementation | ✅ PASS | All new models/endpoints derived from spec FR-001 through FR-013 |
| Data Integrity and Auditability | ✅ PASS | FBR responses still stored by existing services; bulk task errors logged per-invoice; no change to invoice audit trail |
| Environment Isolation | ✅ PASS | Background posting reuses existing `PostingService` which already enforces per-invoice environment |
| No business logic in frontend | ✅ PASS | Background processing is server-side; frontend only starts tasks + polls status |
| All FBR communication via backend | ✅ PASS | FBR calls remain in backend services; frontend never calls FBR directly |
| RESTful /api/v1/ pattern | ✅ PASS | New endpoints follow `/api/v1/invoices/bulk-*` convention |
| Additive only | ✅ PASS | New model, new endpoints, new context; zero changes to existing tables/endpoints |
| Non-functional: <3s responses | ✅ PASS | Fire-and-forget endpoints return immediately (<500ms); polling endpoints are lightweight DB reads |

**Gate result: ALL PASS — proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/004-async-bulk-operations/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/sp.tasks — NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   └── bulk_operation.py          # NEW — BulkOperationTask SQLModel
│   ├── services/
│   │   ├── bulk_operation_service.py  # NEW — background processing logic
│   │   └── scheduler.py               # EDIT — add cleanup_bulk_tasks job
│   ├── api/
│   │   └── v1/
│   │       └── invoices.py            # EDIT — add 4 new endpoints
│   └── schemas/
│       └── invoice.py                 # EDIT — add request/response schemas
├── tests/
│   ├── unit/
│   │   └── test_bulk_operation_service.py  # NEW
│   └── api/
│       └── test_bulk_operation_endpoints.py # NEW

frontend/
├── src/
│   ├── contexts/
│   │   └── BulkOperationContext.tsx    # NEW — context + provider
│   ├── components/
│   │   └── invoices/
│   │       └── BulkOperationProgress.tsx # NEW — progress card component
│   ├── app/
│   │   └── (protected)/
│   │       ├── layout.tsx             # EDIT — add BulkOperationProvider
│   │       └── invoices/
│   │           └── history/
│   │               └── page.tsx        # EDIT — replace bulk handlers
│   └── lib/
│       └── api.ts                      # EDIT — add 4 new API functions
└── __tests__/
    ├── BulkOperationContext.test.tsx    # NEW
    └── BulkOperationProgress.test.tsx   # NEW
```

**Structure Decision**: Web application (Option 2). Both backend/ and frontend/ exist. The ai-agent/ project is not touched — the new functionality lives entirely in the main backend. No new project is created.

## Complexity Tracking

No constitution violations — this section is empty.
