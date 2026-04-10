---
id: 2
title: Create Implementation Plan for Invoice Automation
stage: plan
date: 2026-04-04
surface: agent
model: claude-sonnet-4-6
feature: 001-invoice-automation
branch: 001-invoice-automation
user: Anas2338
command: /sp.plan
labels: ["planning", "architecture", "automation", "excel-processing", "background-worker"]
links:
  spec: specs/001-invoice-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-invoice-automation/plan.md
  - specs/001-invoice-automation/research.md
  - specs/001-invoice-automation/data-model.md
  - specs/001-invoice-automation/contracts/excel-upload.yaml
  - specs/001-invoice-automation/contracts/automation-dashboard.yaml
  - specs/001-invoice-automation/contracts/invoice-retry.yaml
  - specs/001-invoice-automation/quickstart.md
tests:
  - null
---

## Prompt

/sp.plan first read existing project than make plan accordingly

User requested to create implementation plan for Digital FTE Invoice Automation feature, with emphasis on understanding existing project structure before planning.

## Response snapshot

Explored existing project structure including:
- Backend: FastAPI with SQLModel, existing models (Invoice, User, FBRResponse), services (FBRClient, ValidationService, AuditService)
- Frontend: Next.js 16 App Router with Better Auth
- Database: Neon PostgreSQL with Alembic migrations
- Authentication: JWT-based with existing middleware

Created comprehensive implementation plan with:

**Phase 0 - Research (research.md)**:
- Excel processing: pandas + openpyxl for reading/writing .xlsx files
- Background scheduler: APScheduler for hourly FTE worker
- File storage: Local filesystem under uploads/{user_id}/
- FBR integration: Reuse existing FBRClient and ValidationService
- Concurrency control: Database flag in ExcelUploadSession.processing_status
- Template generation: Dynamic with pandas + openpyxl

**Phase 1 - Design (data-model.md, contracts/, quickstart.md)**:
- Data models: AutomationInvoice, AutomationLog, ExcelUploadSession (SQLModel schemas)
- API contracts: OpenAPI specs for excel upload, dashboard, and retry endpoints
- Database migration: Alembic migration for 3 new tables with indexes
- Quickstart guide: Setup, testing, deployment, and troubleshooting instructions

**Key Design Decisions**:
1. Hourly processing window (FTE worker checks at minute 0 each hour)
2. Local filesystem storage for Excel files
3. Database flag for concurrent upload prevention
4. Reuse existing FBR services (DRY principle)
5. JSON storage for invoice data (flexible schema)
6. Systemd service for FTE worker deployment

**Integration Points**:
- Reuse existing authentication (require_authentication dependency)
- Reuse existing FBRClient for FBR API calls
- Reuse existing ValidationService for invoice validation
- Reuse existing AuditService for logging
- Follow existing patterns (SQLModel, service layer, Pydantic schemas)

All artifacts follow existing project patterns and constitution requirements.

## Outcome

- ✅ Impact: Complete implementation plan created with research, data models, API contracts, and setup guide. Ready for task breakdown with /sp.tasks.
- 🧪 Tests: No tests run (planning phase)
- 📁 Files: Created plan.md, research.md, data-model.md, 3 API contract files, quickstart.md
- 🔁 Next prompts: /sp.tasks to generate detailed task breakdown for implementation
- 🧠 Reflection: Successfully explored existing codebase before planning, ensuring all design decisions align with current architecture. Identified reusable services (FBRClient, ValidationService) to avoid duplication. All new code follows established patterns (SQLModel for models, service layer for business logic, FastAPI for endpoints).

## Evaluation notes (flywheel)

- Failure modes observed: None - planning completed successfully
- Graders run and results (PASS/FAIL): N/A (planning phase)
- Prompt variant (if applicable): Standard /sp.plan workflow with explicit instruction to read existing project first
- Next experiment (smallest change to try): Proceed to /sp.tasks for task breakdown
