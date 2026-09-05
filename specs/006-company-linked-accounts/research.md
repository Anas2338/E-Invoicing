# Research: Company Linked Accounts

**Date**: 2026-09-05 | **Feature**: 006-company-linked-accounts

Research inputs: three pre-plan codebase research passes + two precision inventories (backend creation/posting/numbering points; frontend settings/component patterns). Every decision below cites the code it is based on.

## R1 — Company representation: `users.company_id` with owner self-reference

- **Decision**: Add `company_id` (UUID, nullable) to `users`. Owner rows get `company_id = id` (backfill for every existing user); employee rows get `company_id = <owner id>`. Expose `is_company_owner` (`company_id == id`) in profiles. Index the column.
- **Rationale**: No company table exists anywhere (verified across both services). The owner row already carries everything company-level: seller identity, FBR tokens, numbering, auto-posting config (`backend/src/models/user.py:48-96`). Self-reference avoids a new `companies` table, keeps owner = single source of truth, and makes "owner" unambiguous. Scope predicate = `user_id IN (users where company_id == root)`, where root = actor's `company_id` (owner id) — this includes **deactivated** employees' rows so historical company data stays visible while their logins are blocked.
- **Alternatives rejected**: (a) New `companies` table — heavier, adds cross-DB model churn for no functional gain at this scale; (b) NTN-based grouping — `fbr_seller_ntn` is editable/optional per row and sandbox/production NTNs can differ, too fragile for an access boundary.
- **Code refs**: `backend/src/models/user.py:21-96` + `ai-agent/src/models/user.py` (byte-identical except backend-only `reset_pin_*`); both must be updated. Alembic head today: `20260727_add_excel_staging` (`backend/alembic/versions/20260727_add_excel_staging_tables.py`).

## R2 — Employee provisioning: owner-only endpoint, auto-approved, deactivate-not-delete

- **Decision**: New owner-only API creates employees with `account_status='approved'`, `role='user'`, `automation_enabled=False`, `is_active=True`, no tokens/seller/numbering fields (resolved via owner), server-generated temporary password validated by `validate_password_strength`. Deactivation sets `is_active=False` **and** bumps `token_version` (kills live sessions); login additionally blocked for `not is_active`. Never hard-delete (invoices FK to `users.id` with CASCADE-ish semantics — rows are company data).
- **Rationale**: Registration flow (`backend/src/api/v1/auth.py:328-379`) always creates standalone pending accounts — unsuitable for employees (would sit in the portal-admin approval queue). No admin "create user" endpoint exists. Login currently checks `account_status` only (`auth.py:132-147`); `is_active` is used for password reset only, so the login guard needs the small addition.
- **Alternatives rejected**: reuse public register + admin approve (friction + wrong account shape); DB provisioning only (customer chose self-serve UI).
- **Code refs**: `backend/src/utils/password_validator.py:29+` (password policy), `backend/src/models/user.py` (account_status/token_version), `backend/src/api/v1/admin_users.py:106-223` (approve/reject patterns).

## R3 — Data-sharing scope: company-wide read/write, actor-scoped workspaces

- **Decision**: Visibility predicates change from `Model.user_id == actor` to `Model.user_id IN (company members)` for: invoices (all service methods in `backend/src/services/invoice_service.py`), unified history / buyers-from-history / PDF ownership checks (`invoices.py:266-561`), dashboard (`dashboard.py:43,71`), reports (`reports.py`), saved products (`saved_products.py`), profile/report counts (`user_profile.py`, `reports.py:90`). Buyers need no code: they are derived from invoice history (`invoices.py:313-367`).
- **Unchanged on purpose (actor-scoped workspaces, NOT company data)**: Excel staging sessions and rows (`excel_staging.py`, `excel_staging_service.py`), bulk-operation tasks (`bulk_operation_service.py`), posting logs, daily posting counters, idempotency keys — these are per-actor working state. All automation-DB tables (`automation_invoice`, `excel_upload_session`, `automation_log`) remain owner-only — employees never write them.
- **Rationale**: "All data same in both accounts" = the company dataset. Transient workspaces shared between members would corrupt mid-flow state (two members editing one staging session); automation rows are owner's module state. Posting logs/counters keyed to the actor preserve the audit trail of who posted.
- **Code refs**: ownership filters at `invoice_service.py:179,234,411,454,494,532,634,664`, `saved_products.py:91,148,318,447,509`, agent side all endpoints (employees never call it after R7 gate).

## R4 — Effective-user (owner) resolution for credentials, seller data, environment, numbering

- **Decision**: New helper resolves the **effective company row**: members get the owner's row; standalone users get themselves. Everything derived from the user row resolves through it:
  - **Seller snapshot** at manual-Excel parse time (`backend/src/utils/manual_excel_helper.py:1054-1064`) — snapshot owner's seller fields.
  - **FBR tokens** at the five posting/validate sites: single validate (`invoices.py:843-865`), single post (`invoices.py:1002-1024`), bulk validate (`backend/src/services/bulk_operation_service.py:119-146`, `_get_fbr_token` at 461-474), `PostingService.post_single_invoice` (`backend/src/services/posting_service.py:51-80`, used by bulk post + auto-posting scheduler `scheduler.py:86-91`). The orphaned `manual_post_to_fbr` (`invoices.py:1128`) has no route — leave untouched.
  - **Environment filter** `get_user_environment_filter` (`invoice_service.py:67-86`; callers `invoices.py:267,313,540,561`, `reports.py:61,86,113`, `dashboard.py:43`) — callers first resolve the effective row so members see the same sandbox/production set the owner's tokens allow.
  - **Profile payload** (`auth.py:391-433` + `backend/src/schemas/user.py:61-80`): for members, return owner's `fbr_seller_*` and numbering fields (forms prefill from `/auth/profile` — `sale-invoice-form.tsx:311-352`) plus new `company_id` / `is_company_owner`. Tokens are never returned (already true).
  - **Invoice numbering** `get_next_invoice_number` (`backend/src/utils/helpers.py:52-86`) + duplicated logic `_generate_auto_invoice_numbers` (`manual_excel_helper.py:93-139`): resolve owner's settings (prefix/padding/start/year) and count across the **company's** invoices, not the actor's.
- **Rationale**: Single source of truth (user chose one shared credential set). Invoice creation payloads already carry seller fields for single manual create (`schemas/invoice.py` — environment required in payload), so only the excel-path snapshots and all token reads need the resolution.
- **Alternatives rejected**: copying seller fields/tokens onto employee rows at provisioning — creates divergence when the owner edits them; violates "credentials never copied" assumption.
- **Code refs**: as listed; `db.get(User, uuid)` pattern in each caller is swapped to `resolve_effective_user(db, actor)`.

## R5 — Company-wide numbering + automation-number awareness

- **Decision**: Numbering is computed from owner settings + company invoices. To avoid colliding with the owner's **pending automation numbers** (assigned in the automation DB, not yet transferred), the used-numbers feed from the agent must be resolved for the company, not the caller:
  - Agent endpoint `GET /automation/invoice-numbers/used` (`ai-agent/src/api/v1/automation/invoice_numbers.py:25` uses plain `require_authentication`) stays **auth-only** (it returns only external-number strings) but resolves the owning user: if the JWT user is a company member, return numbers for their company owner. This is read-safe: employees only ever see their own company's number strings.
  - The main backend's `fetch_automation_invoice_numbers` (`backend/src/utils/helpers.py:89-124`) is unchanged — it forwards the actor's JWT; the agent now answers company-aware.
  - Collision race (two members creating concurrently, no DB unique constraint on `external_id`): mitigate with a company-scoped duplicate-`external_id` re-check + re-roll loop at create/commit time. Documented limitation: same best-effort semantics the single-account product has today (no constraint exists per user either).
- **Rationale**: `InvoiceNumberAssigner` (`ai-agent/src/services/transfer_service.py:29-69`) seeds from `Invoice.external_id` per user_id at transfer; once transferred, automation numbers exist as company invoices and are naturally covered. The gap is only pre-transfer rows in the automation DB, which is what the feed covers.
- **Alternatives rejected**: (a) gating the used-numbers endpoint behind automation access — would 403 employees' legitimate manual Excel flow; (b) skipping the feed for employees — reintroduces transient collisions.

## R6 — Automation gate = AI-agent (real enforcement) + owner-only settings writes

- **Decision**:
  - **AI-agent**: replace the no-op `require_automation_access` (`ai-agent/src/middleware/rbac.py:8-16`) with a real check: load the User from the main DB via the request-scoped `get_db` dependency (`ai-agent/src/database/session.py:118-133`; pattern in `excel.py:158-181`), allow `role == 'admin'` or `automation_enabled`, else 403 `"Automation access not enabled..."` (mirroring `backend/src/middleware/rbac.py:180-217`). Swap `retry.py:28` from `require_authentication` to the real dependency. **Do NOT gate `invoice_numbers.py`** (see R5).
  - **Main backend**: do **not** gate the manual bulk endpoints (`invoices.py:1452,1518,1586`) — inventory shows they are the manual full-worker bulk workflow (bulk-operation tasks), not the Automation module; employees keep them per the spec (full workers minus Automation). The automation surface lives entirely on the AI-agent.
  - **Owner-only settings writes** (403 for employees): FBR-credentials/seller update (`PUT /auth/profile/fbr-credentials`, `auth.py` ~670+), invoice-numbering settings update (`PUT /profile/invoice-settings`), auto-posting config update (route used by `frontend/src/services/autoPostingApi.ts`) — employees' own rows must not diverge from company config.
- **Rationale**: "Not allowed for employees" requires enforcement where the feature actually executes (the agent service), not UI hiding. Manual bulk ops are regular invoicing features; gating them would wrongly strip employees of the "full worker" capability the customer approved.
- **This refines approved-plan step 5** (which proposed gating backend bulk endpoints): the pre-plan research treated those endpoints as automation; the implementation-point inventory proved they belong to the manual workflow. Spec unchanged (US3/FR-003 talk about the Automation module), so this is a plan correction, not a scope change.
- **Code refs**: agent rbac file is 16 lines (verbatim in inventory); `excel.py:158-181` shows the DB-read pattern; dependency used across agent endpoints (`excel.py`, `dashboard.py`, `agent_status.py`, `pdf.py`, `file_management.py`).

## R7 — Migration, deploy ordering, model copies

- **Decision**: One Alembic migration on the main DB (`revision` style `20260905_add_company_id_to_users`, `down_revision = 20260727_add_excel_staging` — verify actual head with `alembic heads` before generating): add nullable `company_id`, backfill `company_id = id`, add index. Mirror the field in **both** User model copies (`backend/src/models/user.py` and `ai-agent/src/models/user.py`).
- **Deploy order matters**: the AI-agent reads the main-DB User row via its model copy; if the agent ships before the migration, `select(User)` fails on the missing column (SQLModel selects all mapped columns). Order: (1) run main-DB Alembic migration, (2) deploy agent + backend together.
- **Code refs**: `backend/alembic/versions/20260727_add_excel_staging_tables.py` (conventions), `backend/src/database/session.py:99-108` + `ai-agent/src/database/session.py:78-97` (startup `create_all` does not alter existing `users`, so migration is mandatory even in dev once `users` exists).

## R8 — Testing approach

- **Decision**: Extend the backend pytest suite following `backend/tests/conftest.py` conventions: SQLite in-memory engine via `clean_test_engine`, users via the `_make_user(engine, **overrides)` pattern, auth simulated by overriding `require_authentication` to return the user UUID (`tests/test_auth.py`). New `tests/test_company.py` covers: provisioning (owner ok / non-owner 403 / duplicate email), scoping (owner sees employee invoices & vice versa; standalone regression), effective-user resolution (employee posting uses owner token — via `mock_encryption` autouse fixture), numbering (company sequence), deactivation (login blocked, data retained), automation 403 contract on agent-side is verified by code review + manual smoke (ai-agent has no pytest suite in-repo).
- **Code refs**: `backend/tests/conftest.py` (fixtures verbatim in inventory), `test_auth.py` (`_make_user`, `auth_client`, `mock_encryption`).

## R9 — Frontend approach (no new patterns needed)

- **Decision**: Extend the `User` type (`frontend/src/providers/auth-provider.tsx:12-27`) with `company_id`, `is_company_owner` (backend returns company-resolved seller/numbering in `/auth/profile`, so invoice forms need no changes). Gate the three company-level settings surfaces to owners only: Business Information form (`settings/page.tsx:306-410`, saves `PUT /auth/profile/fbr-credentials`), `InvoiceSettingsSection` (:259), `AutoPostingSettings` (:262). Portal-admin gates (`role === 'admin'`, the only three: `settings/page.tsx:68,413`, `register/page.tsx:27`) stay portal-admin-only — `is_company_owner` is a separate concept and must not grant them.
- **New Team members section**: `TeamMembersSection` in the settings page modeled on `SavedItemsSection.tsx` (forwardRef card, `useState/useEffect` fetch, `window.confirm` for deactivate, inline `fixed inset-0` modal for the add form, react-toastify for feedback — no Dialog/Table/sonner primitives exist in `src`). New `companyApi` service mirroring `adminApi.ts` class pattern (`getHeaders()` CSRF helper, singleton export). No change to `navigation.tsx` or the automation pages (existing `automation_enabled` flag hides the module for employees).
- **Code refs**: inventory of settings page, `SavedItemsSection.tsx` imports (lines 1-13), `adminApi.ts` (34-56, 140-175), `api.ts` conventions (23-59 fetchWithAuth), toast stack (`react-toastify` in root layout).
