# Implementation Plan: Company Linked Accounts

**Branch**: `006-company-linked-accounts` | **Date**: 2026-09-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-company-linked-accounts/spec.md`

## Summary

A company owner account can add employee accounts (auto-approved, temporary password) and both see one identical company dataset; Automation stays owner-only, now enforced server-side on the AI-agent (today it is a no-op gate), not just hidden in the UI. Employees are full manual workers: they create/validate/post invoices under the company's single FBR credential set, share saved products, follow one company-wide invoice-number sequence. No new role; company = `users.company_id` where owner self-references (`company_id == id`) and employees point at the owner; every existing customer backfills to owner-of-self and is behaviorally unchanged.

## Technical Context

**Language/Version**: Python 3.11+ (backend + ai-agent); TypeScript 5 / React 19 / Next.js 16 (frontend)
**Primary Dependencies**: Backend & ai-agent: FastAPI, SQLModel, Alembic, PostgreSQL (Neon); python-jose. Frontend: Tailwind 4, shadcn/ui primitives (button/card/input/label/select/checkbox/switch/badge/dropdown-menu), react-toastify. No new dependencies.
**Storage**: PostgreSQL (Neon). Main DB owned by backend (Alembic); AI-agent has a duplicate model copy of `users` and reads the main DB via a read-only session. Automation DB separate, untouched by this feature.
**Testing**: pytest backend suite (SQLite in-memory, `conftest.py` fixtures, dependency-override auth pattern). No frontend test framework; no ai-agent pytest suite — agent changes verified by code review + manual smoke (quickstart.md).
**Target Platform**: Linux server (Docker Compose + nginx), AI-agent hosted on HF Space; modern browsers.
**Project Type**: web (backend/frontend/ai-agent three-service monorepo)
**Performance Goals**: existing NFR — endpoints < 3s under normal load; company-scoped queries add a members-id fetch per request (cached in-request).
**Constraints**: no new dependencies; smallest viable diff; FBR fields/validation untouched; sandbox/production separation preserved.
**Scale/Scope**: ~1 company with 2 accounts at launch (pilot); design supports N members per company and N companies over time.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Verdict |
|---|---|
| Compliance-First Development | ✅ FBR payloads/fields/validation untouched; posting still only through existing service paths |
| Security by Design | ✅ Automation gate becomes real on the AI-agent (currently no-op); owner-only writes enforced; deactivation kills live sessions (token bump); provisioning owner-only + rate-limited |
| Spec-Driven Implementation | ✅ Spec-derived; no invented FBR contracts |
| Data Integrity & Auditability | ✅ Per-invoice attribution kept (user_id = creator); posting logs keyed to actor; deactivation retains data |
| Environment Isolation | ✅ Sandbox/production kept distinct; employees see the same environment set the company's tokens allow (single set, never mixed) |
| **Row-level data isolation (user_id)** | ⚠ **DEVIATION — justified below** (company-scoped access is the feature) |
| JWT auth / token middleware | ✅ Unchanged; no claims added (DB-backed checks per request, as today) |
| Rate limiting | ✅ Applied to new provisioning endpoint |
| Smallest viable diff | ✅ One new column + one new router + targeted scope changes; no refactors |
| PHR per prompt / ADRs | ✅ PHRs created per stage; ADR planned (below) |

**Justified deviation — data isolation principle**: "users can access ONLY their own data" is amended for company members to "users can access only their own data **and their company's data**". Justification: the customer (account owner) explicitly provisions and controls employee accounts; membership cannot be self-joined (owner-only API); cross-company isolation is fully preserved; standalone accounts (100% of today's users) are untouched because backfill makes them owner-of-self. Owner consent = authorization grant. An **ADR** will be recorded under `history/adr/` documenting this amendment; a formal constitution amendment should be ratified by the team on approval of this feature.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Row isolation relaxed to company scope | The feature is "one company, multiple accounts, one dataset" | Two siloed accounts with manual mirroring violates data integrity; sharing the login violates the customer's staff policy and auditability |

## Project Structure

### Documentation (this feature)

```text
specs/006-company-linked-accounts/
├── spec.md                # feature spec (/sp.specify)
├── research.md            # decisions R1–R9 with code refs (/sp.plan)
├── data-model.md          # users.company_id + scope semantics (/sp.plan)
├── plan.md                # this file (/sp.plan)
├── contracts/
│   └── company-api.md     # API contracts (/sp.plan)
├── quickstart.md          # run + verification (/sp.plan)
├── checklists/
│   └── requirements.md    # spec quality checklist
└── tasks.md               # /sp.tasks output (not yet created)
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/20260905_add_company_id_to_users.py   # NEW migration
├── src/models/user.py                                     # add company_id
├── src/services/company_service.py                        # NEW: effective-user + scope helpers
├── src/api/v1/company.py                                  # NEW: employees router (owner-only)
├── src/api/v1/auth.py                                     # profile payload, login is_active, owner-only fbr-credentials
├── src/api/v1/user_profile.py                             # next-invoice-number, invoice-settings owner-only
├── src/api/v1/saved_products.py                           # company scope
├── src/api/v1/invoices.py                                 # scope callers, env-filter resolution, delete matrix
├── src/api/v1/dashboard.py, reports.py                    # scope + env resolution
├── src/services/invoice_service.py                        # scope, env filter, delete guard, create collision check
├── src/services/posting_service.py, bulk_operation_service.py  # token via effective user
├── src/utils/helpers.py, manual_excel_helper.py           # numbering via effective user/company
├── src/main.py                                            # mount company router
└── tests/test_company.py                                  # NEW
ai-agent/
├── src/models/user.py                                    # add company_id (mirror)
├── src/middleware/rbac.py                                # real automation gate (main-DB check)
├── src/api/v1/automation/retry.py                        # use real gate
└── src/api/v1/automation/invoice_numbers.py              # company-aware used-numbers (auth-only)
frontend/
├── src/providers/auth-provider.tsx                       # User type: company_id, is_company_owner
├── src/services/companyApi.ts                            # NEW (pattern: adminApi.ts)
├── src/components/profile/TeamMembersSection.tsx         # NEW (pattern: SavedItemsSection.tsx)
└── src/app/(protected)/settings/page.tsx                 # owner gating + TeamMembersSection mount
history/
├── prompts/006-company-linked-accounts/                  # PHRs per stage
└── adr/                                                  # NEW ADR: company-scoped data access
```

**Structure Decision**: existing three-service structure preserved; feature slices per service. Cross-service contract = main-DB `users` row + JWT (no new RPC surface beyond the two existing call directions).

## Implementation approach (see research.md for rationale R1–R9, contracts/ for shapes)

1. **Migration + models**: `20260905_add_company_id_to_users` (nullable UUID + index + backfill `= id`); add `company_id` to `UserBase` in BOTH model copies. Run `alembic upgrade head`.
2. **Company service** (`company_service.py`): `resolve_effective_user(db, actor)` → owner row (self if owner/standalone); `get_company_member_ids(db, actor)` → ids where `company_id == root`; `is_company_owner(user)`.
3. **Company employees router** (`company.py`, owner-only): POST create (email/name/optional password, generate compliant temp password when omitted, auto-approved, automation off, token bump guard), GET list, POST deactivate (`is_active=False` + `token_version += 1`). Mount `/api/v1/company`. Extend login to reject `is_active=False`.
4. **Scoping pass**: swap visibility predicates to member ids in invoice_service/dashboard/reports/saved_products/user_profile-counts; buyers inherit automatically. Keep staging/bulk tasks/logs/counters actor-scoped. Enforce delete matrix (automation-posted rows: owner-only).
5. **Effective-user resolution** at the five token sites (validate/post/bulk-validate/PostingService + manual-excel seller snapshot) and environment-filter callers; profile payload returns owner seller/numbering fields + `company_id`/`is_company_owner`; next-number + excel auto-number use owner settings + company scope + company-resolved agent used-numbers feed.
6. **Owner-only writes**: 403 on fbr-credentials / invoice-settings / auto-posting config updates for non-owner members.
7. **AI-agent enforcement**: real `require_automation_access` (main-DB user lookup; admin bypass; else automation_enabled → 403); swap `retry.py`; `invoice_numbers.py` stays auth-only but resolves the caller's company owner numbers. Deploy with migration order (migrate → ship backend+agent).
8. **Frontend**: extend User type; settings gating via `is_company_owner` (Business Info, numbering, auto-posting sections; keep the three existing `role==='admin'` portal gates untouched); `companyApi.ts` + `TeamMembersSection.tsx` on the settings page. Navigation/automation pages unchanged.
9. **ADR** under `history/adr/` for the isolation amendment; **tests** `backend/tests/test_company.py` (+ auth regression), full suite green; manual matrix per quickstart.md.

**Corrected vs approved plan (validated by implementation-point inventory)**: main-backend bulk endpoints are the manual worker workflow, NOT automation — they stay open to employees; the automation gate is enforced on the AI-agent endpoints only. Backend `require_automation_access` (rbac.py:180) remains unused — its AI-agent twin becomes real instead.

## Verification

Full matrix in `quickstart.md` (manual: provision → employee no-automation incl. direct 403 → two-way data match → company-credentials post → numbering → owner-only surfaces → deactivate → standalone regression) + `pytest backend/tests/`. Rollout order: migrate main DB → deploy backend + agent together → pilot provisioning.
