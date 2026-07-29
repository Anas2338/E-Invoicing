---
id: PHR-005-plan-001
title: async-excel-staging-plan
stage: plan
date: 2026-07-27
surface: claude-code
model: deepseek-v4-pro
feature: 005-async-excel-staging
branch: 005-async-excel-staging
user: Muhammad Anus
command: /sp.plan
labels: [plan, excel, staging, implementation, architecture]
links:
  spec: specs/005-async-excel-staging/spec.md
  plan: specs/005-async-excel-staging/plan.md
  research: specs/005-async-excel-staging/research.md
  data-model: specs/005-async-excel-staging/data-model.md
  contracts: specs/005-async-excel-staging/contracts/staging-api.md
  adr: ''
  pr: ''
files:
  - specs/005-async-excel-staging/plan.md
  - specs/005-async-excel-staging/research.md
  - specs/005-async-excel-staging/data-model.md
  - specs/005-async-excel-staging/contracts/staging-api.md
  - specs/005-async-excel-staging/quickstart.md
tests: []
---

## Prompt

/sp.plan "make plan according to existing project structure dont make double file or folder if those file or folder already exist, use uv package manager for backend. write test before any phase implementation."

## Response snapshot

Generated comprehensive implementation plan across 5 phases following the SDD workflow:

**Phase 0 — Research**: Documented 8 technical decisions with rationale and alternatives, including: reuse of existing parser logic, BulkOperationTask pattern for staging model, BulkOperationContext pattern for frontend state, inline editing via controlled inputs (no library), BackgroundTasks for async ops, uv for package management, two-table design over JSON column, delete-on-commit cleanup strategy.

**Phase 1 — Design**: Produced 4 artifacts:
- `data-model.md`: Two-table design (excel_staging_session + excel_staging_row) with complete column definitions, state machine diagrams, field_errors JSON structure, and lifecycle documentation
- `contracts/staging-api.md`: 7 REST endpoints with full request/response schemas, error codes, and example payloads
- `quickstart.md`: Setup instructions, test commands, manual test flow, DB verification queries
- `plan.md`: Technical context, constitution check (all gates pass), project structure, 5-phase implementation sequence with dependency graph

**Key architecture decisions**:
- Follow existing project patterns: models in `backend/src/models/`, services in `backend/src/services/`, API in `backend/src/api/v1/`, components in `frontend/src/components/invoices/`, contexts in `frontend/src/contexts/`
- No new top-level directories; all files added to existing locations
- Tests written before each phase implementation per user instruction
- Implementation order: Data Model → Parser → Service+API → Context+API Client → Grid+UI

**Total new files**: 13 (6 backend, 5 frontend, 2 test files)
**Total modified files**: 5 (2 backend, 3 frontend)

## Outcome

- ✅ Impact: Complete implementation blueprint with 5 phases, dependency graph, test-first strategy, and full API contracts
- 🧪 Tests: Test files specified for each phase (parser unit, service unit, API integration, grid component, context)
- 📁 Files: 8 spec/plan artifacts created + 18 source files planned
- 🔁 Next prompts: /sp.tasks for task breakdown
- 🧠 Reflection: All research decisions grounded in existing codebase analysis. Constitution check passes all gates. Plan respects existing project structure exactly. User's three directives (use existing structure, uv for backend, tests first) incorporated throughout.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Constitution gate — ALL PASS
- Prompt variant (if applicable): standard /sp.plan
- Next experiment (smallest change to try): N/A
