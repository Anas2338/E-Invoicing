# Quickstart: Company Linked Accounts

**Date**: 2026-09-05 | **Feature**: 006-company-linked-accounts

## Local run (unchanged project commands)

```bash
# Backend (port 8001): migration first
cd backend
alembic upgrade head            # applies 20260905_add_company_id_to_users
uvicorn src.main:app --reload

# Frontend (port 3000)
cd frontend && npm run dev

# AI-agent (port 8002) — only needed for automation paths
cd ai-agent && uvicorn src.main:app --port 8002
```

> Startup `create_all` does NOT add columns to an existing `users` table — `alembic upgrade head` is mandatory wherever `users` already exists (dev and prod).

## Manual end-to-end verification

1. **Setup**: register a normal account via the UI, approve it via the portal admin panel (`/admin/users`), set FBR sandbox credentials in settings, and have portal admin enable Automation on it (existing toggle). This is the future **company owner**.
2. **Provision**: as that owner, open Settings → new **Team members** section → Add employee (fresh email). Copy the shown temporary password. Confirm the employee row is not in the portal-admin pending queue.
3. **Employee login**: log in as the employee. Assert:
   - Nav has Dashboard / Invoices only — **no Automation**.
   - Typing `/automation`, `/automation/upload`, `/automation/uploads`, `/automation/dashboard` redirects to `/dashboard` with the toast.
   - Direct call to the AI-agent with the employee's JWT (`curl -H "Authorization: Bearer $TOKEN" https://localhost:8002/api/v1/automation/dashboard/summary`) → **403**.
4. **Shared data (both directions)**: as the owner, create an invoice and a saved product; as the employee, confirm both appear (history, dashboard counts, saved products). Create an invoice as the employee → appears for the owner with the creator's name/id. Automation-posted invoices (transfer a few via the owner's automation upload) appear for the employee too.
5. **Company worker behavior**: as the employee create + validate + post an invoice to the FBR sandbox → succeeds **with the company's credentials** (check the posting log); next invoice number continues the owner's sequence (`INV-XXXX` from company max, not a fresh `INV-0001`); buyers list shows company buyers.
6. **Owner-only surfaces**: as the employee, Settings shows read-only company identity but no editable Business Information / numbering / auto-posting forms; direct PUTs to `/auth/profile/fbr-credentials` and `/profile/invoice-settings` → 403. Owner still edits all of it.
7. **Delete matrix**: employee deleting the owner's manual invoice → allowed; deleting an automation-posted invoice → 403; owner deletes both fine.
8. **Delete (removal)**: owner clicks **Delete** on the employee → the member is removed from the team list, their open session dies (token bumped) and next login → 403; owner's dashboard still shows the employee's historical invoices. Add-employee with the removed email → 409 (account row retained — delete is a soft deactivation, never a hard row deletion).
9. **Regression**: a second standalone account (a single-member company owner) sees only its own data; its Settings Team section lists only itself; Automation behaves per its own flag; direct automation API with its JWT → 403 unless enabled.

## Automated tests

```bash
cd backend
pytest tests/test_company.py tests/test_auth.py -q    # new company tests + login/deactivate regression
pytest -q                                             # full backend suite
```

Key test seams (per conftest conventions): `clean_test_engine` (SQLite in-memory), `_make_user(engine, **overrides)` (add `company_id` override), `require_authentication` dependency override returning the user UUID, `mock_encryption` autouse fixture for token decrypt.

## Rollout order (production)

1. Backend migration `alembic upgrade head` on the main DB (backfills `company_id = id` — no-op data-wise for existing customers).
2. Deploy backend + AI-agent **together** (agent's User model copy reads `company_id`; shipping it before the migration breaks agent DB reads).
3. Portal admin enables/confirms Automation on the pilot customer's account; customer owner provisions the employee account in the UI.
4. Smoke: employee login, no Automation, shared data spot-checks, sandbox post, deactivation.

## SC mapping (spec Success Criteria → check)

SC-001 provisioning/login < 2 min → step 2–3 · SC-002 data match → step 4 · SC-003 employee automation 100% blocked → step 3 + step 9 · SC-004 no duplicate numbers → step 5 (repeat 20 concurrent creates) · SC-005 standalone regression → step 9 · SC-006/SC-007 → post-release support/survey.
