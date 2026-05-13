# Implementation Plan: Separate AI-Agent (Automation) from Main Backend

**Branch**: `001-separate-ai-agent` | **Date**: 2026-05-13 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-separate-ai-agent/spec.md`

## Summary

Physically separate automation code (future-date Excel-uploaded invoice processing) from the main backend into a standalone `ai-agent/` directory. Both services remain FastAPI applications sharing the same technology stack. The main backend retains only manual invoice operations (current/past dates). The AI-agent becomes an independently deployable service handling automation Excel uploads, automation invoice management, and automation dashboard. Frontend routes requests to the correct backend via two environment variables. All 24 automation API endpoints maintain identical contracts.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, SQLModel, SQLAlchemy, Pydantic v2, APScheduler, Anthropic SDK, pandas, openpyxl, reportlab, qrcode, Pillow, python-jose, passlib, slowapi, httpx, fastapi-csrf-protect  
**Package Manager**: uv (Python package and project manager)  
**Storage**: Two separate Neon PostgreSQL databases (main DB already deployed, automation DB already deployed)  
**Testing**: pytest (run via `uv run pytest`)  
**Target Platform**: Linux server (Hugging Face Spaces or similar) — two separate services, independently deployable  
**Project Type**: Web application — two backend services + one frontend (multi-service architecture)  
**Performance Goals**: All endpoints respond in <3 seconds under normal load (per constitution); same as current baseline  
**Constraints**: Zero cross-imports between `backend/` and `ai-agent/`; each service independently deployable; main backend must function with AI-agent stopped  
**Scale/Scope**: ~24 automation endpoints moved; ~10 files moved; ~5 shared-service files duplicated; ~4 frontend files modified; 2 new Dockerfiles; 2 new pyproject.toml files (one per service)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **Compliance-First Development** | ✅ PASS | Separation driven by FBR compliance requirement (future-date invoices not permitted in main backend) |
| **Security by Design** | ✅ PASS | Both services retain auth middleware, CSRF protection (FR-015), rate limiting, and input validation |
| **Spec-Driven Implementation** | ✅ PASS | All automation API contracts preserved identically; FBR spec remains single source of truth |
| **Data Integrity and Auditability** | ✅ PASS | Automation logs, FBR responses, and audit trails retained in automation DB; main DB audit trail unchanged |
| **Environment Isolation** | ✅ PASS | Sandbox/Production config separate per service; each service has its own `.env` |
| **Architectural Constraints** | ✅ PASS | FastAPI + SQLModel + Neon PostgreSQL + Next.js 16+; no new technology introduced |
| **API Design Rules** | ✅ PASS | RESTful, versioned `/api/v1/`, schema-based contracts preserved |
| **Non-Functional Standards** | ⚠️ REVIEW | Duplicated shared services (validation_service, fbr_client) create maintenance burden — documented mitigation |
| **Development Guidelines** | ✅ PASS | Smallest viable diff; no unrelated refactoring; existing code patterns followed |

**Gate Result**: PASS. The one flagged item (duplicated services) is an accepted tradeoff documented in the spec's Assumptions section and research.md.

## Project Structure

### Documentation (this feature)

```text
specs/001-separate-ai-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output — OpenAPI specs
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
# After separation:
backend/                          # Main backend (manual invoices only)
├── src/
│   ├── main.py                  # MODIFIED: remove automation router
│   ├── config/
│   │   └── settings.py          # MODIFIED: remove automation settings
│   ├── database/
│   │   └── session.py           # MODIFIED: remove automation engine
│   ├── models/                  # MODIFIED: remove 5 automation models
│   ├── schemas/                 # MODIFIED: remove 5 automation schemas
│   ├── services/                # MODIFIED: remove 4 automation services
│   ├── api/
│   │   └── v1/
│   │       ├── invoices.py      # MODIFIED: remove automation DB deps
│   │       └── ... (no automation/ subdirectory)
│   └── utils/                   # MODIFIED: remove excel_validator
├── alembic/                     # MODIFIED: remove automation migrations
├── pyproject.toml               # Uses uv; backend deps only
├── uv.lock
└── Dockerfile

ai-agent/                         # NEW: standalone AI-agent service
├── src/
│   ├── main.py                  # NEW: FastAPI app with automation router + middleware
│   ├── config/
│   │   └── settings.py          # NEW: automation-specific settings
│   ├── database/
│   │   └── session.py           # NEW: automation DB engine only
│   ├── models/                  # MOVED: 5 automation models
│   │   ├── automation_base.py
│   │   ├── automation_invoice.py
│   │   ├── automation_log.py
│   │   ├── ai_agent_health_check.py
│   │   └── excel_upload_session.py
│   ├── schemas/                 # MOVED: 4 automation schemas
│   │   ├── automation.py
│   │   ├── agent.py
│   │   ├── excel.py
│   │   └── file_management.py
│   ├── services/                # MOVED + COPIED
│   │   ├── automation_service.py      # MOVED
│   │   ├── excel_service.py           # MOVED
│   │   ├── file_management_service.py # MOVED
│   │   ├── background_validation_service.py # MOVED
│   │   ├── validation_service.py      # COPIED (shared)
│   │   ├── fbr_client.py              # COPIED (shared)
│   │   ├── fbr_service.py             # COPIED (shared)
│   │   └── pdf_service.py             # NEW: automation-specific PDF generation
│   ├── api/
│   │   ├── deps.py              # NEW: simplified deps
│   │   ├── middleware/           # COPIED: auth_middleware
│   │   └── v1/
│   │       └── automation/      # MOVED: all 7 route files
│   │           ├── __init__.py
│   │           ├── excel.py
│   │           ├── dashboard.py
│   │           ├── retry.py
│   │           ├── health.py
│   │           ├── agent_status.py
│   │           ├── file_management.py
│   │           └── pdf.py
│   ├── middleware/               # COPIED: rbac
│   │   └── rbac.py
│   └── utils/                   # MOVED + COPIED
│       ├── excel_validator.py   # MOVED
│       ├── secure_file_validator.py # COPIED
│       └── helpers.py           # COPIED (required subset)
├── assets/                      # COPIED: FBR logo + font
├── alembic/                     # MOVED: automation migrations
├── pyproject.toml               # NEW (uv-managed, automation deps only)
├── uv.lock                      # NEW (generated by uv sync)
├── .env.example                 # NEW
└── Dockerfile                   # NEW (multi-stage, uses uv)

frontend/                        # MODIFIED: dual backend routing
├── src/
│   ├── services/
│   │   └── automationApi.ts     # MODIFIED: AI-agent URL
│   ├── lib/
│   │   └── api.ts               # MODIFIED: add AI-agent CSRF handling
│   └── contexts/
│       └── UploadSessionContext.tsx # MODIFIED: AI-agent URL
├── .env.local                   # MODIFIED: add AI_AGENT_API_URL
└── next.config.js               # MODIFIED: proxy rewrites
```

**Structure Decision**: Two separate FastAPI services (`backend/` + `ai-agent/`) sharing identical stack but deployed independently. Existing `backend/` directory retains only manual invoice code. New `ai-agent/` directory created at repo root level. Frontend remains single Next.js app routing to both backends via environment variables.

## Complexity Tracking

No constitution violations requiring justification. The only tradeoff (duplicated shared services) is documented in research.md and accepted per spec assumptions.
