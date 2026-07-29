---
id: PHR-005-spec-001
title: async-excel-staging-spec
stage: spec
date: 2026-07-27
surface: claude-code
model: deepseek-v4-pro
feature: 005-async-excel-staging
branch: 005-async-excel-staging
user: Muhammad Anus
command: /sp.specify
labels: [spec, excel, staging, inline-editing, async]
links:
  spec: specs/005-async-excel-staging/spec.md
  ticket: ''
  adr: ''
  pr: ''
files:
  - specs/005-async-excel-staging/spec.md
  - specs/005-async-excel-staging/checklists/requirements.md
tests: []
---

## Prompt

/sp.specify "Async Excel Staging with Inline Error Correction — Replace the current all-or-nothing manual Excel upload flow with an async, persistent staging workflow. The current flow fails entirely on ANY validation error, forcing the user to fix the Excel file and re-upload everything. The new flow: (1) User uploads Excel → system parses ALL rows and stores them in a database-backed staging session, (2) ALL invoices (valid + errored) are shown in a spreadsheet-like editable grid where errored cells are highlighted red, (3) User edits cells directly in the UI to fix errors, (4) User clicks "Recheck" to re-validate only the corrected rows, (5) When all errors are cleared, an "Upload All" button appears, (6) Clicking "Upload All" creates all invoices as DRAFT in the main invoices table and DELETES the staging session (cleanup), (7) A "Cancel" button also deletes the staging session. The entire process is async and database-backed so the user can navigate away, logout, and resume where they left off. After commit or cancel, the temporary staging table becomes empty."

## Response snapshot

Created comprehensive feature specification for the async Excel staging workflow. Key outputs:

- **6 user stories** prioritized P1-P3 covering: upload+parse (P1), inline editing (P1), recheck (P2), commit (P2), cancel (P3), session resume (P2)
- **33 functional requirements** across 6 categories: File Upload & Parsing (FR-001 to FR-005), Staging Grid Display (FR-006 to FR-010), Inline Editing (FR-011 to FR-015), Recheck (FR-016 to FR-020), Commit (FR-021 to FR-026), Cancel (FR-027 to FR-029), Session Persistence & Recovery (FR-030 to FR-033)
- **8 measurable success criteria**: grid display in <10s for 500 rows, zero re-upload needed, <5s recheck cycle, 100% edit persistence, 100% session cleanup, 100% session recovery, 80% fewer support tickets, 50% less time correcting data
- **11 edge cases** identified including empty files, large files, concurrent sessions, duplicates, network failures, and stale data
- **3 key entities**: Excel Staging Session (temporary, deleted after commit/cancel), Staging Row (per-row data with field-level errors), Invoice (existing, final DRAFT output)
- **8 documented assumptions** about single session per user, no collaboration, inline editing scope, expiry policy

## Outcome

- ✅ Impact: Established clear specification for replacing the broken all-or-nothing Excel upload with an async, persistent, user-friendly staging workflow
- 🧪 Tests: N/A (spec phase)
- 📁 Files: specs/005-async-excel-staging/spec.md, specs/005-async-excel-staging/checklists/requirements.md
- 🔁 Next prompts: /sp.clarify (if clarifications needed) or /sp.plan (for implementation planning)
- 🧠 Reflection: Thorough codebase research before spec writing ensured all requirements are grounded in the existing architecture. The spec avoids implementation details while being concrete enough about data flow and user interactions. Key user concern about cleanup (empty staging table) explicitly addressed in FR-025 and FR-028.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Checklist validation PASS — all items verified
- Prompt variant (if applicable): standard /sp.specify
- Next experiment (smallest change to try): N/A
