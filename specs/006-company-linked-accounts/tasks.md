# Tasks: Company Linked Accounts

**Input**: Design documents from `specs/006-company-linked-accounts/` (plan.md, spec.md, research.md R1–R9, data-model.md, contracts/company-api.md, quickstart.md)
**Prerequisites**: Foundational phase complete before any user story.

**Tests**: Test tasks ARE included — the plan (step 9, quickstart.md) explicitly requires `backend/tests/test_company.py` (+ `tests/test_auth.py` regression). Tests run against each completed story's implementation (not red-green).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US6 mapping to spec.md user stories
- All paths repo-root-relative (`backend/…`, `ai-agent/…`, `frontend/…`) per plan.md structure.

## Alignment notes (recorded before task generation — resolve first)

1. **Standalone accounts are single-member company owners.** `users.company_id == id` is true for every standalone account (backfill + registration), so `is_company_owner` is true for them and the TeamMembersSection is visible listing only themselves. This is REQUIRED for the pilot flow (quickstart step 1–2: the pilot owner is a normal registered account that must be able to add its first employee) and for SC-007 self-service. Consequence: spec US6 AC2 and quickstart step 9's "no Team section" wording are amended (task T042); US6 acceptance = data scope, Automation behavior, and permissions unchanged, not section invisibility.
2. **Main-backend bulk endpoints are the MANUAL worker workflow, not Automation** (plan correction, validated by inventory). They stay open to employees; the Automation gate is enforced on the AI-agent only. Backend `require_automation_access` (`backend/src/middleware/rbac.py`) stays unwired.
3. **Deactivated employees keep `company_id`** — their rows remain company data (member scope predicate ignores `is_active`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm working context. No scaffolding needed — three services and spec artifacts already exist.

- [X] T001 Confirm git branch `006-company-linked-accounts` is checked out, working tree clean, and `specs/006-company-linked-accounts/` holds spec.md, plan.md, research.md, data-model.md, contracts/company-api.md, quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The single column + semantics everything else builds on. MUST be complete before ANY user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Create Alembic migration `backend/alembic/versions/20260905_add_company_id_to_users.py`: add nullable UUID column `company_id` to `users` (non-unique index), backfill every existing row `company_id = id`, then run `alembic upgrade head` (current head `20260727_add_excel_staging`). Migration must be idempotent-safe and reversible (downgrade drops column + index).
- [X] T003 [P] Add `company_id: Optional[uuid.UUID] = None` to `UserBase` in `backend/src/models/user.py`
- [X] T004 [P] Mirror `company_id` in the duplicate user model `ai-agent/src/models/user.py` (agent reads main DB through this copy)
- [X] T005 [P] Extend `_make_user(engine, **overrides)` in `backend/tests/conftest.py` to accept a `company_id` override; default it to the created user's own id (mirrors production backfill) so existing tests stay green
- [X] T006 Set `company_id = id` on all user-creation paths: public registration (`backend/src/api/v1/auth.py`, register ~328–379) and any other `User(...)` insert sites found by search (admin/service paths); registration stays standalone (each new company of its own)
- [X] T007 [P] Create `backend/src/services/company_service.py` with the three helpers (per data-model.md §1–2): `is_company_owner(user) -> bool` (`company_id == id`), `get_company_root_id(db, actor) -> UUID` (actor's `company_id`), `resolve_effective_user(db, actor) -> User` (owner's User row when `actor.company_id != actor.id`, else actor row — the row holding FBR tokens, seller fields, numbering settings), `get_company_member_ids(db, actor) -> list[UUID]` (all ids where `company_id == root`, INCLUDING deactivated employees). Cache member ids per-request where practical.
- [X] T008 Add `company_id` and `is_company_owner` to the profile schema `backend/src/schemas/user.py` (~UserProfile 61–80) and to the profile/login payload builder in `backend/src/api/v1/auth.py` (~391–433): identity-only fields at this stage (`is_company_owner = company_id == id`; `company_id` exposed as-is). Owner-resolved seller/numbering fields come in T035.

**Checkpoint**: Foundation ready — `alembic upgrade head` applied, both model copies carry `company_id`, helpers + profile fields live, full backend suite still green.

---

## Phase 3: User Story 1 - Company owner adds an employee account (Priority: P1) 🎯 MVP

**Goal**: Owner-only provisioning API + UI: create auto-approved employee (generated temporary password), list members, deactivate (never delete). Login rejects deactivated accounts.

**Independent Test** (spec): Log in as a company owner, add an employee with a fresh email, log in as that employee — the employee gains access to the portal right away; deactivating them kills their session and next login.

**Implementation for User Story 1**

- [X] T009 [US1] Implement `POST /api/v1/company/employees` in new router `backend/src/api/v1/company.py` (contracts §1): caller must be owner (`company_id == id`) else 403 `"Only the company owner can manage employees"`; validate + lowercase email, unique check → 409 `"Email already registered"` (no partial row); `role="user"`, `account_status="approved"` (no pending queue), `automation_enabled=False`, `company_id=owner.id`; when `password` omitted generate a compliant temporary password (reuse existing strength policy/generator in `backend/src/utils/` if present; else implement per contract §1 rules) and return it ONCE in the 201 response (`temporary_password` field); apply slowapi rate limit 10/hour per owner (match existing rate-limit usage)
- [X] T010 [US1] Implement `GET /api/v1/company/employees` in `backend/src/api/v1/company.py` (contracts §1): owner-only; returns owner + active + deactivated members (`id, email, name, role, is_company_owner, automation_enabled, is_active, account_status, created_at`) + `total`
- [X] T011 [US1] Implement `POST /api/v1/company/employees/{employee_id}/deactivate` in `backend/src/api/v1/company.py` (contracts §1): owner-only; target must be member of caller's company and not the owner (400 deactivating owner; 404 not found / not in your company); effect `is_active=False` + `token_version += 1` (existing sessions die); never hard-delete
- [X] T012 [US1] Extend login in `backend/src/api/v1/auth.py` (~132–147) to reject `is_active == False` with 403 `"Account deactivated. Please contact your administrator."` (check after `account_status`, before password verify per contracts §6)
- [X] T013 [US1] Mount the company router at `/api/v1/company` in `backend/src/main.py` (route registration + middleware order unchanged)
- [X] T014 [US1] Enforce FR-013 in `backend/src/api/v1/admin_users.py`: locate portal-admin delete/disable routes; refuse deleting or disabling an account that is a company owner (`company_id == id`) while it has ≥1 active employee (`company_id = owner.id AND is_active`), with a clear 400/409 detail
- [X] T015 [P] [US1] Extend the `User` type in `frontend/src/providers/auth-provider.tsx` (~12–27) with `company_id: string | null` and `is_company_owner: boolean`
- [X] T016 [P] [US1] Create `frontend/src/services/companyApi.ts` (pattern: `frontend/src/services/adminApi.ts` — class + `getHeaders` CSRF convention): `createEmployee({email, name, password?})` returning the temp password from the 201 payload, `listEmployees()`, `deactivateEmployee(id)`
- [X] T017 [US1] Create `frontend/src/components/profile/TeamMembersSection.tsx` (pattern: `SavedItemsSection.tsx` — hand-rolled modal, react-toastify, `window.confirm`): list members (owner badge, active/deactivated status, automation badge), "Add employee" modal (email/name, optional password), show generated temporary password ONCE with copy affordance + warning, deactivate action with confirmation; no team-management UI for non-owners (API already 403s)
- [X] T018 [US1] Mount `TeamMembersSection` on the settings page `frontend/src/app/(protected)/settings/page.tsx`, rendered only when `is_company_owner` (owner and standalone single-member companies both see it per alignment note 1)
- [X] T019 [US1] Tests in `backend/tests/test_company.py` (+ append to `backend/tests/test_auth.py`): employee created → 201, auto-approved, temp password logins immediately; duplicate email → 409 with no partial row; deactivate → 200, `is_active=False`, existing session JWT rejected (token bump), subsequent login → 403; employee API calls from non-owner member → 403; non-member target of deactivate → 404; FR-013 admin-delete guard; rate limit on provisioning

**Checkpoint**: US1 fully functional and testable independently — owner can provision, list, deactivate; employee logs in immediately; suite green.

---

## Phase 4: User Story 2 - Both accounts see the same company data (Priority: P1)

**Goal**: Company-wide visibility for manual + automation-posted invoices, saved products, derived buyers, dashboard stats, reports — with per-invoice creator attribution and the delete matrix.

**Independent Test** (spec): Log in as the owner, note full invoice list and counts; log in as the employee and confirm the same invoices, saved products, buyers, dashboard numbers, reports are visible, and each invoice still shows who created it.

**Implementation for User Story 2**

- [ ] T020 [US2] Swap visibility predicates to company-member scope in `backend/src/services/invoice_service.py` (list/get/count/adjacent/unified history — use `get_company_member_ids`); keep every row's `user_id = creator` untouched (attribution, FR-005)
- [ ] T021 [US2] Same member-scope swap in `backend/src/api/v1/invoices.py`: history/list endpoints, PDF ownership checks, buyers-from-history derivation (~313–367, now company-wide automatically) and the DELETE matrix (data-model.md §5): any member may delete manual invoices company-wide; rows with `automation_invoice_id` set are owner-only (403 `"Only the company owner can delete automation-posted invoices"` for non-owner members) — apply to both single and bulk/manual-bulk delete paths
- [ ] T022 [P] [US2] Company scope for all CRUD in `backend/src/api/v1/saved_products.py` (list/get/update/delete by all members)
- [ ] T023 [P] [US2] Company scope for stats in `backend/src/api/v1/dashboard.py` and `backend/src/api/v1/reports.py` (member ids instead of actor id)
- [ ] T024 [US2] Company scope for saved-product/invoice counts in `backend/src/api/v1/user_profile.py`; AUDIT (no code change) that staging sessions, bulk-operation tasks, posting logs and counters stay actor-scoped per data-model.md §4
- [ ] T025 [US2] Tests in `backend/tests/test_company.py`: two-way visibility of manual invoices, automation-posted invoices (insert with `automation_invoice_id` set), saved products, buyers list, dashboard counts, reports; creator `user_id` attribution preserved on employee-created rows; records of a deactivated employee remain visible to the owner; employee deletes manual invoice OK / automation-posted → 403; owner deletes both; staging/bulk/log isolation between members of the same company

**Checkpoint**: US2 independently testable — shared dataset identical from both member accounts, attribution and delete matrix enforced.

---

## Phase 5: User Story 3 - Automation is owner-only, with no way around it (Priority: P1)

**Goal**: Real server-side automation gate on the AI-agent (currently a no-op) so employee/standalone-without-flag JWTs get 403 from the service itself. Frontend nav/page hiding already exists via `automation_enabled` — zero frontend changes (verify only). Backend `require_automation_access` stays unwired (alignment note 2).

**Independent Test** (spec): Log in as the employee and confirm the module is absent; opening Automation page addresses redirects (existing behavior — verify); calling any AI-agent automation endpoint directly with the employee's JWT returns 403.

**Implementation for User Story 3**

- [ ] T026 [US3] Replace the no-op `require_automation_access` in `ai-agent/src/middleware/rbac.py` with a real gate: after JWT verification, load the user row from the main DB (existing read-only session pattern, e.g. `ai-agent/src/api/v1/automation/excel.py:159`); reject 403 `{"detail": "Automation access not enabled. Please contact your administrator."}` when `role != "admin"` AND `automation_enabled != true` (admin bypass preserved; model now has `company_id` — do NOT let an employee's company link grant access)
- [ ] T027 [US3] Swap `ai-agent/src/api/v1/automation/retry.py` from its current auth-only dependency to the real `require_automation_access`
- [ ] T028 [US3] Audit every remaining automation router (`excel.py`, `dashboard.py`, `agent_status.py`, `pdf.py`, `file_management.py`) to confirm they use the gated dependency (attach where missing); record FR-015 denials in the agent's existing logging (`automation_log` where reachable, else structured logs) so portal operators can inspect; confirm `invoice_numbers.py` intentionally stays auth-only (numbering is NOT automation — see T037)

**Checkpoint**: US3 verifiable by direct 403 call (quickstart step 3); owner automation experience unchanged.

---

## Phase 6: User Story 4 - Employee is a full manual invoicing worker under the company identity (Priority: P2)

**Goal**: Employees create/validate/post manual invoices using the company's single credential set + seller identity; one company-wide invoice-number sequence; environment consistency across members.

**Independent Test** (spec): As an employee, create, validate, and submit an invoice to FBR; it submits with the company's identity, receives the next number in the company sequence, then appears for the owner too.

**Implementation for User Story 4**

- [ ] T029 [US4] Resolve FBR tokens through the effective user (owner) at the two token sites in `backend/src/api/v1/invoices.py`: validate (~843–865) and post (~1002–1024) — keep the invoice's actor `user_id`, use owner's sandbox/production credential set + environment
- [ ] T030 [US4] Same resolution in `backend/src/services/bulk_operation_service.py` token sites (~119–146 and `_get_fbr_token` ~461–474). These bulk endpoints are the MANUAL worker workflow and stay open to employees (alignment note 2)
- [ ] T031 [US4] Same resolution in `backend/src/services/posting_service.py` (`PostingService.post_single_invoice` ~51–80); posting logs stay keyed to the acting user (actor-scoped audit)
- [ ] T032 [US4] `backend/src/utils/manual_excel_helper.py`: seller snapshot at ~1054–1064 and `_generate_auto_invoice_numbers` ~93–139 must use the effective owner's seller fields/company scope (Excel manual-upload numbering continues the company sequence)
- [ ] T033 [US4] Resolve the environment filter against the owner: `get_user_environment_filter` in `backend/src/services/invoice_service.py` (~67–86) plus every caller (validate/post/bulk/dashboard/reports) passes the effective user so sandbox/production rules are company-consistent (FR-008, contracts §4)
- [ ] T034 [US4] Extend the profile/login payload builder (`backend/src/api/v1/auth.py` ~391–433; built once for both login + profile) so member accounts receive the OWNER's `fbr_seller_ntn`, `fbr_business_name`, `fbr_seller_province`, `fbr_seller_address`, `invoice_prefix`, `invoice_start_number`, `invoice_padding`, `invoice_include_year` (contracts §2) — never token fields; owners/standalone unchanged
- [ ] T035 [US4] Company-wide numbering (research R5, data-model §6): `get_next_invoice_number` in `backend/src/utils/helpers.py` (~52–86) and the `/profile/next-invoice-number` endpoint (`backend/src/api/v1/user_profile.py`) compute from the OWNER's settings and the company invoice set; invoice create/commit paths gain a company-scoped duplicate check + re-roll (`backend/src/services/invoice_service.py`), including consultation of the company-resolved agent used-numbers feed (T037) so employees skip the owner's pending automation numbers
- [ ] T036 [US4] Make `GET /api/v1/automation/invoice-numbers/used` in `ai-agent/src/api/v1/automation/invoice_numbers.py` company-aware: stays auth-only (NOT gated, T028); for an employee caller, resolve their company owner (main-DB `company_id`) and return that owner's used numbers; owners/standalone behavior unchanged
- [ ] T037 [US4] Tests in `backend/tests/test_company.py`: employee post/validate call path uses owner's FBR credentials (mock token decrypt/encryption per `mock_encryption` convention); seller snapshot on employee-created invoices = owner's values; next-number for employee continues owner's sequence (mocked agent feed) and never restarts at `INV-0001`; environment filter returns the company-consistent set; employee-created invoice attributed to employee but number-sequential with company set

**Checkpoint**: US4 independently testable — employee posts under company identity, numbering shared, no credential leakage.

---

## Phase 7: User Story 5 - Owner keeps single control of company settings and membership (Priority: P2)

**Goal**: Company credentials, seller identity, numbering, automation/auto-posting settings are owner-only writes (backend 403 + settings UI read-only/hidden for employees); owner UI retains full control incl. Team section (US1).

**Independent Test** (spec): Log in as the employee — company credential/numbering/Automation settings are not editable and direct PUTs are rejected; as the owner everything remains editable.

**Implementation for User Story 5**

- [ ] T038 [US5] Backend owner-only write enforcement (contracts §3, 403 detail `"Only the company owner can update company settings"` for non-owner members): `PUT /api/v1/auth/profile/fbr-credentials` (`backend/src/api/v1/auth.py`), invoice-settings update in `backend/src/api/v1/user_profile.py`, and the auto-posting config update endpoint (locate the route `frontend/src/services/autoPostingApi.ts` calls; guard it in its backend file); record FR-015 denials in existing backend logs for operator review
- [ ] T039 [US5] Settings page gating in `frontend/src/app/(protected)/settings/page.tsx`: Business Info / FBR credentials (~306–410), numbering (`InvoiceSettingsSection` ~259) and AutoPosting (~262) sections are editable ONLY for `is_company_owner`; employees see the read-only company identity (fields now populated via T034) with no edit controls; TeamMembersSection already owner-only (T018)
- [ ] T040 [US5] Tests in `backend/tests/test_company.py`: employee PUTs to fbr-credentials, invoice-settings, auto-posting config → 403; owner PUTs → 200; employee profile payload contains no token fields; deactivated-employee JWT also 403 on writes

**Checkpoint**: US5 independently testable — single source of truth stays with the owner, employees cannot mutate company configuration through any interface.

---

## Phase 8: User Story 6 - Existing single-account customers are unaffected (Priority: P3)

**Goal**: Regression safety — standalone accounts (owner-of-self) see exactly their own data and prior Automation behavior; nothing about company mechanics changes their flow (see alignment note 1 for the Team-section semantics).

**Independent Test** (spec): Log in with a normal standalone account — dashboard, invoices, saved products, and Automation behavior identical to before; member-scope predicate degrades to their own id because `company_id == id`.

**Implementation for User Story 6**

- [ ] T041 [US6] Amend the alignment drift in the artifacts: update spec.md US6 AC2 wording and quickstart.md step 9 so standalone accounts = single-member company owners (Team section lists only themselves; no behavioral change otherwise); keep FR-014 as "team mechanics only via owner-type accounts; employees never see them"
- [ ] T042 [US6] Regression audit + tests in `backend/tests/test_company.py`: standalone account (no employees) sees ONLY its own invoices/products/counts — rows of an unrelated company never appear; its Automation toggle behaves as before (nav/redirect flow already flag-driven — verify by frontend build/typecheck `cd frontend && npx tsc --noEmit` and a manual smoke that `navigation.tsx` was untouched); team API returns its single-member self with `is_company_owner: true`

**Checkpoint**: US6 verifiable — full suite green proves no regression for owner-of-self rows.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: ADR, full verification, deploy-order sign-off.

- [ ] T043 Create ADR under `history/adr/` recording the two amendments: (1) row-level data isolation relaxed to company scope (owner-provisioning = authorization grant; cross-company isolation preserved; standalone backfill = no-op) per plan.md constitution check; (2) every existing account is a single-member company owner (Team section visible to all owners) — flagging the constitution wording change for team ratification
- [ ] T044 Run `pytest -q` on the full backend suite (`backend/tests/`); fix any regression; confirm `pytest tests/test_company.py tests/test_auth.py -q` green
- [ ] T045 Run the quickstart.md manual matrix (backend + frontend + ai-agent locally): all 9 steps pass; record results (SC-001…SC-007 trace); verify deploy order documented (migrate main DB → ship backend + AI-agent together → pilot provisioning) and commit the branch

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (migration must be applied before either service reads `company_id`)
- **User Stories (Phase 3+)**: All depend on Foundational
  - US1 → US2 → US3 → US4 → US5 → US6 (single-implementer sequential order, matching plan.md steps 3–8; safest because US1’s UI tasks, US4's payload/numbering and US5's gating all touch `auth.py`/`settings/page.tsx` at different phases)
  - Backend + frontend can be implemented per story independently if staffed
- **Polish (Phase 9)**: Depends on all stories

### Within Each User Story

- Models/service helpers (Foundational) before endpoints
- Backend endpoint per story before its frontend surface (T034 profile payload precedes T039 read-only identity display)
- Per-story test task last; story complete before moving to next priority

### Parallel Opportunities

- Foundational: T003/T004/T005/T007 can run in parallel once T002's migration is applied
- US1: T015/T016 (frontend type + service) parallel with backend tasks T009–T014
- US2: T022/T023 parallel (saved_products.py vs dashboard.py+reports.py)
- US3: T026–T028 same service, sequential; independent of all other stories once Foundational is done
- US4: T029–T033 touch different files but share the same helper seam (T007) — sequential edits, no [P]
- US5: T038 backend before T039 frontend (frontend gating assumes backend 403 as the real bound)

---

## Parallel Example: User Story 1 (back/front split)

```bash
# Backend provisioning (once Foundational done):
Task: "T009–T014 company router + login rejection + admin guard + mount"

# Frontend (parallel — different files):
Task: "T015 extend User type in frontend/src/providers/auth-provider.tsx"
Task: "T016 companyApi.ts in frontend/src/services/companyApi.ts"
```

## Parallel Example: User Story 2 (file-isolated scoping)

```bash
Task: "T020–T021 invoice_service.py + invoices.py member scope"
Task: "T022 saved_products.py company scope"
Task: "T023 dashboard.py + reports.py company scope"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup
2. Phase 2: Foundational (CRITICAL — migration + both models + helpers)
3. Phase 3: US1 (owner adds employee, employee logs in, deactivation works)
4. **STOP and VALIDATE**: `pytest tests/test_company.py tests/test_auth.py -q` + quickstart step 2–3
5. Deploy/demo if ready — employee onboarding is the whole customer ask's entry point

### Incremental Delivery

1. Foundation ready → US1 (provisioning) → deploy/demo
2. US2 (shared data) → US3 (agent gate) → the three P1 stories form the customer's complete ask; validate against quickstart steps 3–4
3. US4 (company worker) + US5 (owner control) → P2 completeness; quickstart steps 5–6
4. US6 (standalone regression) → full suite + quickstart step 9
5. Polish: ADR, full suite, manual matrix, rollout order sign-off

### Parallel Team Strategy

With multiple developers: one on backend scoping (US2/US4), one on AI-agent gating (US3), one on frontend (US1 UI + US5 gating); integrate per checkpoint after Foundational.

---

## Notes

- [P] tasks = different files, no dependencies — sequential execution is fine for a single implementer
- [Story] label maps task to spec.md user story for traceability
- Do NOT wire `backend/src/middleware/rbac.py` `require_automation_access` anywhere (alignment note 2)
- Do NOT add an agent-side gate to `invoice_numbers.py` (T037 keeps it auth-only)
- Never hard-delete employee rows from the company API; deactivation only (FR-011)
- Follow existing patterns: service-layer scope changes in backend services, frontend components modeled on `SavedItemsSection.tsx`/`adminApi.ts`, conftest fixtures for tests
- Commit after each task or logical group; stop at any checkpoint to validate
