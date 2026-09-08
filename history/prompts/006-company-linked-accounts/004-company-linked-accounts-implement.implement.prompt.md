---
id: PHR-006-implement-001
title: company-linked-accounts-implement
stage: implement
date: 2026-09-07
surface: claude-code
model: deepseek-v4-flash
feature: 006-company-linked-accounts
branch: 006-company-linked-accounts
user: Muhammad Anus
command: /sp.implement
labels: [implement, company-accounts, owner-employee, automation-gate, us1-us6]
links:
  spec: specs/006-company-linked-accounts/spec.md
  ticket: specs/006-company-linked-accounts/tasks.md
  adr: history/adr/001-company-linked-accounts-company-scope.adr.md
  pr: ''
files:
  - backend/src/models/user.py
  - backend/alembic/versions/20260905_add_company_id_to_users.py
  - ai-agent/src/models/user.py
  - backend/src/services/company_service.py
  - backend/src/api/v1/company.py
  - backend/src/api/v1/auth.py
  - backend/src/api/v1/user_profile.py
  - backend/src/utils/helpers.py
  - backend/src/api/v1/invoices.py
  - backend/src/services/invoice_service.py
  - backend/src/services/bulk_operation_service.py
  - backend/src/services/posting_service.py
  - backend/src/utils/manual_excel_helper.py
  - backend/src/api/v1/saved_products.py
  - backend/src/api/v1/dashboard.py
  - backend/src/api/v1/reports.py
  - ai-agent/src/middleware/rbac.py
  - ai-agent/src/api/v1/automation/retry.py
  - ai-agent/src/api/v1/automation/invoice_numbers.py
  - frontend/src/services/companyApi.ts
  - frontend/src/components/profile/TeamMembersSection.tsx
  - frontend/src/app/(protected)/settings/page.tsx
  - backend/tests/test_company.py
tests:
  - backend/tests/test_company.py (52 tests: US1 provisioning/deactivate/admin-guard, US2 scope/isolation/delete matrix, US3 agent-gate adjacent, US4 token resolution/profile/numbering/env, US5 owner-only 403s, US6 standalone regression)
  - backend full suite pytest -q → 283 passed
  - backend/tests/test_company.py tests/test_auth.py -q → 123 passed
  - frontend npx tsc --noEmit → clean
---

## Prompt

/sp.implement "feature=006-company-linked-accounts. Tasks at specs/006-company-linked-accounts/tasks.md (T001–T045, 9 phases). Execute phases in order; per-story tests last; flip task boxes [X] as completed; run the full backend test suite at checkpoints; create this implement PHR at the end. Standing directive from the user: NO git commits at any point — work proceeds uncommitted on branch 006-company-linked-accounts."

## Response snapshot

Executed T001–T045 on branch 006-company-linked-accounts (no commits — user directive):

- **Phase 1–2 (Setup, Foundational)**: migration `20260905_add_company_id_to_users` (company_id + index + backfill), `company_id = id` default on register, both User model copies, conftest `_make_user` default, `company_service.py` (`is_company_owner`, `get_company_root_id`, `resolve_effective_user`, `get_company_member_ids` — members include deactivated), UserProfile schema + auth payload gains `company_id`/`is_company_owner` + owner seller/numbering fields.
- **Phase 3 US1 (T009–T019)**: `company.py` employees router (owner-only, auto-approved, temp password, list, deactivate with token bump + login is_active 403, FR-012 409 no-partial-row, FR-013 admin delete-owner guard), frontend `companyApi.ts` + `TeamMembersSection` (owner-only, shows temp password once), deactivation login-block.
- **Phase 4 US2 (T020–T025)**: company-scoped visibility across invoice list/single/history/count, dashboard stats, reports rows/years, saved-products CRUD, buyers-from-history; delete matrix (manual = any member, automation-posted = owner only incl. bulk); staging/bulk/posting-log remain actor-scoped.
- **Phase 5 US3 (T026–T028)**: AI-agent `require_automation_access` real gate (main-DB user load, admin bypass, `automation_enabled` else FR-015 403); `retry.py` swapped to the gated dependency; `invoice_numbers.py` stays auth-only (numbering is not automation) but made company-aware later (T036).
- **Phase 6 US4 (T029–T037)**: employee manual worker under company identity — owner-token resolution at validate/post (invoices.py), bulk service, posting service, excel-helper seller snapshot + auto numbering; env filter company-consistent; profile/login payload serves OWNER seller + numbering fields, never tokens; company-wide numbering (owner settings + company invoice set + agent feed); `invoice_numbers.py` resolves employee → owner's used numbers; 8 US4 tests (token capture on mock FBR, next-number sequence + agent-feed skip, employee-created invoice attribution, env consistency).
- **Phase 7 US5 (T038–T040)**: owner-only write guards with exact detail `"Only the company owner can update company settings"` (FR-015 denial logs) on `PUT /auth/profile/fbr-credentials` (auth.py), `PUT /profile/invoice-settings` + `PUT /profile/auto-posting` (user_profile.py shared `_require_company_settings_owner` helper mirroring company.py's `_require_owner`); settings page gating — numbering/auto-posting sections hidden for non-owners, FBR card renders the company's read-only seller identity (owner values via profile payload) with no edit controls; 7 US5 tests incl. deactivated-employee defense-in-depth 403s.
- **Phase 8 US6 (T041–T042)**: spec.md US6 AC1/AC2 + quickstart step 9 reworded (standalone = single-member company owner; Team lists only themselves); 2 dedicated standalone-regression tests (full-surface isolation vs unrelated standalone) + frontend typecheck; `navigation.tsx` confirmed untouched by git.
- **Phase 9 (T043–T045)**: ADR-001 (constitution isolation amendment + owner-of-self model, flagged for ratification); full suite 283 passed; test_company+test_auth 123 passed.

## Outcome

- ✅ Impact: Company-linked accounts implemented end-to-end — employees are full manual workers under the owner's single FBR identity/numbering/credential set, Automation is server-gated on the AI-agent, company settings are owner-only writes, standalone customers unchanged.
- 🧪 Tests: backend full suite 283 passed (test_company.py: 52), frontend `npx tsc --noEmit` clean.
- 📁 Files: ~24 implementation files across backend / ai-agent / frontend + ADR + spec/quickstart amendments (see frontmatter).
- 🔁 Next prompts: quickstart.md 9-step manual browser matrix on a live stack (backend 8001 + frontend 3000 + ai-agent 8002); commit the branch when the user lifts the no-commit directive; constitution ratification of ADR-001.
- 🧠 Reflection: the SQLite BLOB/UUID override convention (`_client_as` UUID object for `db.get` routers vs `_us2_client_as` str for `UUID(str)` routers) was the highest-leverage test seam — mixing them was the only recurring failure class. Token-free payloads and token *capture* on mocked FBR calls (rather than decrypted-value assertions) kept credential tests behavioral. Company-wide numbering required explicit `created_at` seeding to defeat `order_by(created_at.desc())` ties.

## Evaluation notes (flywheel)

- Failure modes observed: (1) UUID-vs-str override mismatch → `'UUID' object has no attribute 'replace'` / `'str' object has no attribute 'hex'`; fixed by per-router conventions above. (2) User model `invoice_prefix` column default `'INV-'` (not None) invalidated a "never diverged" assertion — test corrected to compare against the actual default. (3) Bash heredoc quoting failed on this shell for multi-line appends — switched to the Edit tool (the file round-trip rule: never PowerShell Get/Set-Content on UTF-8).
- Graders run and results (PASS/FAIL): backend full suite PASS (283); targeted company+auth PASS (123); frontend typecheck PASS; navigation.tsx untouched PASS (git).
- Prompt variant (if applicable): sequential single-implementer per plan (no parallel agents).
- Next experiment (smallest change to try): quickstart matrix step 4/5 as Playwright smoke when the local stack runs.
