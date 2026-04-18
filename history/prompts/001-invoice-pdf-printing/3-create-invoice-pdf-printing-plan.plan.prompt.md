---
id: 3
title: Create Invoice PDF Printing Implementation Plan
stage: plan
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 001-invoice-pdf-printing
branch: 001-invoice-pdf-printing
user: Anas2338
command: /sp.plan
labels: ["planning", "architecture", "pdf-printing", "implementation-design"]
links:
  spec: specs/001-invoice-pdf-printing/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-invoice-pdf-printing/plan.md
  - specs/001-invoice-pdf-printing/research.md
  - specs/001-invoice-pdf-printing/data-model.md
  - specs/001-invoice-pdf-printing/contracts/pdf-api.yaml
  - specs/001-invoice-pdf-printing/quickstart.md
  - CLAUDE.md
tests:
  - Constitution check validation (all gates passed)
  - Research decisions documented for 6 technical areas
  - API contracts validated against OpenAPI 3.0.3 spec
---

## Prompt

/sp.plan read existing structure and make accrodingly dont make double file or folder if it already exists.

## Response snapshot

Created comprehensive implementation plan for invoice PDF printing feature with FBR compliance:

**Phase 0 - Research (Completed)**:
- Evaluated PDF libraries → Selected ReportLab for precise layout control and Unicode support
- Defined QR code specifications → Version 2.0, 25x25 modules, 1.0x1.0 inch using qrcode library
- Identified font requirements → Noto Sans Arabic for Urdu/Arabic character support
- Determined PDF response pattern → FastAPI StreamingResponse with attachment headers
- Designed batch memory management → Single canvas sequential generation approach
- Documented FBR logo acquisition plan → User must provide official logo

**Phase 1 - Design (Completed)**:
- Created data model documentation showing read-only access to existing AutomationInvoice model
- Designed 2 API endpoints: GET /invoices/{id}/pdf and POST /invoices/batch-pdf
- Generated OpenAPI 3.0.3 contract with complete request/response schemas
- Documented data flow from frontend → API → PDF service → response
- Created quickstart guide with setup steps, implementation checklist, and troubleshooting

**Technical Decisions**:
- Dependencies: reportlab>=4.0.0, qrcode>=7.4.2, Pillow>=10.0.0
- Architecture: Backend PDF generation (FastAPI), frontend triggers (Next.js)
- Integration: Extends existing automation system under /api/v1/automation/
- Performance: <3s single invoice, <150s batch (50 invoices)
- Security: JWT auth, row-level authorization, no PDF storage

**Constitution Check**: All 11 gates PASSED - no violations, no complexity tracking needed.

## Outcome

- ✅ Impact: Complete implementation plan ready for task generation. All technical unknowns resolved through research. Clear integration path with existing automation system.
- 🧪 Tests: Constitution validation passed, research decisions documented, API contracts validated, existing project structure analyzed to avoid duplication
- 📁 Files: Created 5 planning artifacts (plan.md, research.md, data-model.md, pdf-api.yaml, quickstart.md), updated CLAUDE.md with new technologies
- 🔁 Next prompts: `/sp.tasks` (generate implementation tasks from this plan)
- 🧠 Reflection: Successfully integrated with existing backend/frontend structure. Avoided creating duplicate files by analyzing existing automation API structure. Research phase resolved all technical uncertainties (PDF library, QR specs, Unicode fonts, memory management). Plan respects constitution constraints and reuses existing patterns (auth, authorization, logging).

## Evaluation notes (flywheel)

- Failure modes observed: None. Successfully analyzed existing structure and integrated new feature without duplication.
- Graders run and results (PASS/FAIL): Constitution check - PASS (11/11 gates), Structure analysis - PASS (identified existing automation API pattern), Research completeness - PASS (6/6 technical areas resolved)
- Prompt variant (if applicable): Standard /sp.plan workflow with Phase 0 research and Phase 1 design
- Next experiment (smallest change to try): Proceed to /sp.tasks to generate granular implementation tasks with acceptance criteria
