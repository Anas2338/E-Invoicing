# ADR-001: Company-Scoped Data Isolation & Owner-Of-Self Accounts

> **Scope**: One decision cluster — how the company-linked-accounts feature amends
> the constitution's row-level data isolation and account-ownership model.

- **Status:** Proposed (constitution wording change pending team ratification)
- **Date:** 2026-09-07
- **Feature:** 006-company-linked-accounts
- **Context:** A customer runs one company with two portal accounts: an owner
  (Automation enabled) and employees (Automation hidden), sharing one dataset.
  Before this feature the constitution mandated strict `user_id` isolation
  (`.specify/memory/constitution.md`: "Row-level data isolation must be
  enforced in database queries to ensure users can access only their own data";
  "Authorization rule: users can access ONLY their own data (user_id
  isolation)"), so two accounts meant two isolated silos. The feature relaxes
  that rule — deliberately and only within an explicit authorization grant —
  and backfills every existing account into the new model.

## Decision

Two coordinated amendments:

**Amendment 1 — Row-level isolation is relaxed to company scope.**
Business data (invoices, saved products, buyers derived from invoice history,
dashboard/report aggregates) is scoped to *all members of a company*
(`users.company_id`), not to a single `user_id`. Attribution is preserved:
each row keeps the creating `user_id` for audit, and the actor-scoped
workspaces (staging sessions, bulk tasks, posting logs) stay per-actor.
Cross-company isolation is absolute: member-scope predicates resolve through
the company root, and an unrelated company's rows are never visible.
Owner-provisioning of an employee is the authorization grant that widens the
employee's scope to the owner's company dataset; employees can never widen
their own scope. The owner's row remains the *single configuration source* —
FBR credentials, seller identity, numbering settings, Automation state are
owner-only reads/writes for the company (employees 403 on writes; token
values never returned). This relaxation does NOT extend to credentials or
configuration; it covers business data only.

**Amendment 2 — Every existing account is a single-member company owner.**
Backfill sets `company_id = id` on all existing rows and on new
registrations, so `is_company_owner` is true for every standalone account.
Consequences: member-scope predicates degrade to `[self]` (no behavioral
change for standalone customers), and the Settings → Team section is visible
to every owner — listing only themselves until they add an employee. The
constitution's "users can access ONLY their own data" must be re-read as
"users access their company's data (their own for single-member companies)"
— this wording change is flagged for team ratification.

## Consequences

### Positive

- One FBR credential set per company; no divergent seller profiles.
- Employees operate with full manual capabilities on shared data without
  Automation access (the customer's exact requirement).
- Standalone customers experience zero change — the backfill is a no-op for
  scope resolution.
- Audit trail intact: creator `user_id` attribution on every shared row.

### Negative

- Constitution wording now differs from shipped behavior until ratified.
- The relaxation is an additional security surface: any bug in
  company-scope resolution could widen access — mitigated by
  single-resolution helpers (`company_service.py`) used by every scoped
  query and by the company-wide automated tests.
- Team UI appears on settings for all owners (self-only list) — a visible
  change for existing customers, though inert until they add employees.

## Alternatives Considered

- **Keep strict `user_id` isolation and duplicate data per account.**
  Rejected: violates the single-credential/single-sequence requirement;
  duplicated data diverges and breaks numbering continuity.
- **Introduce a real company/tenant table with explicit membership.**
  Rejected for this iteration: heavier migration and UI; the owner-row
  model (one owner per company today) delivers the pilot without it.
  Revisit when companies need multiple owners or self-service teams.
- **Gate the Team section to "companies with employees".**
  Rejected: the pilot owner is a normal registered account that must add
  its first employee — the section must exist before any employee does.

## References

- Feature Spec: `specs/006-company-linked-accounts/spec.md`
- Implementation Plan: `specs/006-company-linked-accounts/plan.md`
- Data Model & Semantics: `specs/006-company-linked-accounts/data-model.md` §1–2
- API Contract: `specs/006-company-linked-accounts/contracts/company-api.md`
- Task Tracking: `specs/006-company-linked-accounts/tasks.md` (T002–T045)
- Evaluator Evidence: implement-stage PHR
  `history/prompts/006-company-linked-accounts/004-company-linked-accounts-implement.implement.prompt.md`
