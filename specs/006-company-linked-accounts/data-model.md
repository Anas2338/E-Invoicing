# Data Model: Company Linked Accounts

**Date**: 2026-09-05 | **Feature**: 006-company-linked-accounts

## 1. New column

### `users.company_id`

| Attribute | Value |
|---|---|
| Type | UUID, nullable |
| Added by | Alembic migration `20260905_add_company_id_to_users` (main DB) |
| Index | yes (non-unique) |
| Backfill | every existing row: `company_id = id` |

**Semantics** (the whole feature):

- `company_id == id` ⇒ **company owner** (or standalone account — 100% of today's customers). `is_company_owner = (company_id == id)`.
- `company_id == <other user's id>` ⇒ **employee account** linked to that owner. `company_id` never chains (employees always point at the root owner).
- `company_id IS NULL` ⇒ only transiently during creation; login/profile and all queries assume non-null after provisioning/registration.
- A deactivated employee keeps `company_id` — their historical rows remain company data.

**Member scope predicate** for any shared table T: `T.user_id IN (SELECT id FROM users WHERE company_id = :root)` with `root = actor.company_id` (for the owner, `company_id == id` ⇒ their own company incl. all employees). Applies to invoices, saved products, and derived views (buyers, dashboard, reports).

## 2. Derived per-request values (not stored)

- **Effective company row** `effective_user(actor)`: the owner's User row if `actor.company_id != actor.id`, else the actor row. Used for: FBR sandbox/production tokens, `fbr_seller_*` snapshot, invoice numbering settings, environment filter. Employees' rows keep all such fields at defaults and never diverge.
- **Profile exposure**: employees receive owner's `fbr_seller_ntn`, `fbr_business_name`, `fbr_seller_province`, `fbr_seller_address`, `invoice_prefix/start_number/padding/include_year` in `/auth/profile` (they are needed to render invoice forms and numbering); **no token fields ever**.

## 3. Field rules for employee rows (set at provisioning, immutable via user-facing API)

| Field | Value | Enforcement |
|---|---|---|
| `role` | `"user"` | never `admin` (portal admin is DB-promoted only) |
| `account_status` | `"approved"` | auto-approved at creation — no pending queue |
| `automation_enabled` | `False` | only portal-admin `/admin/users/{id}/toggle-automation` can change (existing) |
| `auto_posting_enabled` | `False` (default) | settings write endpoints 403 for employees (R6) |
| `is_active` | `True` → `False` on deactivation | login blocked; `token_version` bumped on deactivate |
| FBR tokens, `fbr_seller_*`, numbering fields | defaults/empty | resolved through owner; owner-only write endpoints 403 for employees |
| `email` | unique (existing constraint) | duplicate → 409 at provisioning |

## 4. Owner-only vs company-shared vs actor-scoped (per table/area)

| Table / area | Scope rule |
|---|---|
| `invoices` (manual + automation-posted) | company (read/edit per status rules; delete matrix below) |
| `user_saved_product` | company (CRUD by all members) |
| Buyers (derived from invoice history) | company (automatic) |
| Dashboard stats, reports | company |
| `excel_staging_session` / `excel_staging_row` | actor (workspace) |
| `bulk_operation_task` | actor |
| `posting_logs`, `daily_posting_counters`, `idempotency_keys` | actor (audit) |
| `fbr_user_hs_code_uom` (cache) | actor (cache only) |
| Automation DB: `automation_invoice`, `excel_upload_session`, `automation_log` | owner only (employees never reach them — gate R6) |
| FBR master data | global (unchanged) |

## 5. Delete matrix

| Row | Owner | Employee | Portal admin |
|---|---|---|---|
| Manual invoice (any member's) | yes | yes | yes |
| Automation-posted invoice (`automation_invoice_id` set — identifier confirmed on main-DB Invoice) | yes | **no (403)** | yes |
| Saved product | yes | yes | — |
| Employee account | deactivate (no hard delete) | no | deactivate/delete via existing admin routes (guarded: see spec FR-013 — owner may not be deletable while active employees exist; employee rows are never hard-deleted by the company API) |

## 6. Numbering state

- Numbering settings live on the owner row only.
- Sequence = max suffix over **company invoices** (`external_id`) + settings, plus company-resolved automation used-numbers (R5) for the owner's pre-transfer automation rows.
- `external_id` has no DB unique constraint (existing product semantics); race mitigation = company-scoped duplicate re-check + re-roll at create/commit (best effort, matching current behavior per-user).

## 7. No new tables

No schema additions beyond the one column. Entity concepts ("company", "company dataset") are query-level semantics over existing tables, documented here and in the ADR.
