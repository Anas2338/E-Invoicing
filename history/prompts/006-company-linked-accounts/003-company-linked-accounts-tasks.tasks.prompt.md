---
id: PHR-006-tasks-001
title: company-linked-accounts-tasks
stage: tasks
date: 2026-09-05
surface: claude-code
model: deepseek-v4-flash
feature: 006-company-linked-accounts
branch: 006-company-linked-accounts
user: Muhammad Anus
command: /sp.tasks
labels: [tasks, company-accounts, task-breakdown, migration, rbac]
links:
  spec: specs/006-company-linked-accounts/spec.md
  ticket: ''
  adr: ''
  pr: ''
files:
  - specs/006-company-linked-accounts/tasks.md
tests:
  - backend/tests/test_company.py (planned, per-story suites US1/US2/US4/US5/US6)
  - backend/tests/test_auth.py (login deactivation regression, US1)
---

## Prompt

/sp.tasks "feature=006-company-linked-accounts. Plan at specs/006-company-linked-accounts/plan.md, research at specs/006-company-linked-accounts/research.md, contracts at specs/006-company-linked-accounts/contracts/company-api.md, data-model at specs/006-company-linked-accounts/data-model.md. Generate implementation task breakdown. Key scope: users.company_id migration + both model copies; company service helpers; company employees router (owner-only, auto-approved, temp password, deactivate w/ token bump + login is_active check); company-scoped queries (invoices/saved products/dashboard/reports/buyers); effective-user resolution at 5 FBR token sites + env filter callers + profile payload; company numbering; owner-only settings writes (403); AI-agent real automation gate + retry swap + company-aware invoice-numbers feed; frontend User type + settings gating + companyApi + TeamMembersSection; ADR for isolation amendment; backend tests test_company.py."

## Response snapshot

Produced the complete tasks phase on branch 006-company-linked-accounts:

- **`tasks.md` with 45 tasks** (T001–T045) in 9 phases, every task in strict checklist format (`- [ ] ID [P?] [Story?] desc + path`).
- **Phase 1 Setup** (T001 context check — no scaffolding, repo pre-initialized) · **Phase 2 Foundational** (T002–T008: migration `20260905_add_company_id_to_users`, both User model copies, conftest `_make_user` company_id default, register-path `company_id=id`, `company_service.py` helpers, schema+payload identity fields) · **Phase 3–8 user stories** US1 (11 tasks) → US2 (6) → US3 (3) → US4 (9) → US5 (3) → US6 (2) in spec priority order P1→P3 · **Phase 9 Polish** (T043 ADR, T044 full suite, T045 quickstart matrix + deploy order).
- Story structure per phase: Goal + Independent Test (from spec) + implementation tasks + per-story test task, checkpoints between phases; dependency graph, parallel opportunities/examples (back/front split on US1; file-isolated scoping pairs on US2), MVP-first + incremental + parallel-team strategies.
- **Two alignment corrections recorded at the top of tasks.md (must resolve first)**: (1) standalone accounts are single-member company owners — `company_id == id` backfill makes every account owner-of-self, so the TeamMembersSection is visible to all owners listing themselves; this is REQUIRED for the pilot flow (pilot owner is a fresh normal account) and SC-007 self-service; spec US6 AC2 / quickstart step 9 wording amended via T041. (2) Main-backend bulk endpoints = manual worker workflow (stay open to employees); the automation gate becomes real on the AI-agent only; backend `require_automation_access` remains unwired (per plan.md correction).
- Task text carries the implementation-point precision from plan research: 5 FBR-token sites (invoices.py validate/post, bulk_operation_service.py two sites, posting_service.py, manual_excel_helper.py snapshot), env-filter caller pass, delete matrix w/ `automation_invoice_id` owner-only guard incl. bulk delete, agent `invoice_numbers.py` company-aware but auth-only (NOT gated), numbering via owner settings + company scope + company-resolved agent feed, FR-013 admin delete guard, FR-015 denial logging, no hard-delete of employees.

## Outcome

- ✅ Impact: Converts plan/contracts/data-model into an immediately executable, story-atomic task list with exact file paths; surfaced the standalone-is-owner semantic conflict between artifacts (spec/quickstart "no team section" vs data-model backfill identity) BEFORE implementation and resolved it self-consistently with a documented alignment note + amendment task instead of leaving it to mid-implementation discovery
- 🧪 Tests: N/A (tasks phase) — per-story test tasks planned into test_company.py + test_auth.py per conftest conventions
- 📁 Files: specs/006-company-linked-accounts/tasks.md
- 🔁 Next prompts: /sp.implement (approval of tasks.md + alignment notes, then T001→T045)
- 🧠 Reflection: The story-vs-plan ordering tension (plan executes step 5 resolution before step 6 gating, while spec priority puts US3 before US4) was resolved by mapping tasks to spec stories but sequencing phases by plan dependency order — tasks stay traceable to stories AND executable in plan order. One unresolved-at-spec ambiguity (does a standalone account see team UI?) was provable only at task time because it follows from the backfill semantics — worth a "semantic consequence audit" pass in future plan phases.

## Evaluation notes (flywheel)

- Failure modes observed: spec/quickstart wording contradicted the data-model backfill consequence (team UI visibility for standalone owners); no create-phr.sh bash helper exists in this repo — fell back to agent-native PHR per skill instructions
- Graders run and results (PASS/FAIL): Format validation PASS — all 45 tasks use `- [ ] T### [P?] [US#?]` with file paths; story counts sum to phases (11+6+3+9+3+2 + 1 setup + 7 foundational + 3 polish = 45); no [P] marks on same-file pairs
- Prompt variant (if applicable): standard /sp.tasks with key-scope parameter
- Next experiment (smallest change to try): none
