# API Contracts: Company Linked Accounts

All endpoints under `/api/v1/` unless noted. Existing conventions apply: httpOnly session cookie + `X-CSRF-Token` on state-changing verbs, JWT `sub` = user id, JSON errors as `{"detail": "..."}`. New router mounted at `/api/v1/company`. All times ISO-8601.

## 1. New: employee provisioning (owner-only)

### POST `/api/v1/company/employees`

Creates an employee account linked to the caller's company. Caller must be an approved user with `company_id == id` (company owner). Rate limit: `10/hour` per owner.

**Request**
```json
{
  "email": "staff@acme.pk",
  "name": "Staff Member",
  "password": null
}
```
`email` required (sanitized, lowercased, unique), `name` required, `password` optional — if omitted the server generates a compliant temporary password (returned once, in the response).

**Response 201**
```json
{
  "id": "3f0b...",
  "email": "staff@acme.pk",
  "name": "Staff Member",
  "temporary_password": "Xk9#mQ2$vLp5",   // only present when generated server-side
  "automation_enabled": false,
  "is_company_owner": false,
  "created_at": "2026-09-05T10:00:00Z"
}
```
The employee can log in immediately (`account_status = "approved"`).

**Errors**: 400 invalid email / password policy violation (when provided); 409 `"Email already registered"` (no partial row); 401 unauthenticated; 403 caller is not a company owner (`"Only the company owner can manage employees"`).

**Validation rules**: email unique across `users`; if `password` provided it must pass the existing strength policy (8+ chars, upper/lower/digit/special, etc.); generated passwords comply by construction.

### GET `/api/v1/company/employees`

Lists the caller's company members — the owner + currently active employees. Removed (deactivated) employees drop from the team list (the Settings → Team "Delete" action); their account rows and every row they created remain company data. Caller must be the company owner.

**Response 200**
```json
{
  "members": [
    {
      "id": "…",
      "email": "admin@acme.pk",
      "name": "Company Admin",
      "role": "user",
      "is_company_owner": true,
      "automation_enabled": true,
      "is_active": true,
      "account_status": "approved",
      "created_at": "…"
    }
  ],
  "total": 2
}
```

### POST `/api/v1/company/employees/{employee_id}/deactivate`

Deactivates an employee. Caller must be the company owner; target must be a member of the caller's company and not the owner themselves. Effect: `is_active = false`, `token_version += 1` (all existing sessions die). Company data is retained and remains visible.

**Response 200** `{ "id": "…", "is_active": false }`

**Errors**: 404 employee not found / not in your company; 403 not owner; 400 deactivating the owner.

> Re-activation of an employee is not part of the company API — portal admin handles it (existing admin routes) per spec assumptions.

## 2. Modified: profile payload

### GET `/api/v1/auth/profile` (and login `user` object)

Adds two fields; seller + numbering fields become **company-resolved** for members:

```json
{
  "id": "…",
  "email": "staff@acme.pk",
  "role": "user",
  "automation_enabled": false,
  "company_id": "3f0b…",          // NEW — owner's id for employees, own id for owners
  "is_company_owner": false,        // NEW
  "fbr_seller_ntn": "1234567-8",    // owner's value for employees (was: own, usually empty)
  "fbr_business_name": "ACME (Pvt) Ltd",
  "fbr_seller_province": "Sindh",
  "fbr_seller_address": "Karachi",
  "invoice_prefix": "INV-",         // owner's numbering settings for employees
  "invoice_start_number": 1,
  "invoice_padding": 4,
  "invoice_include_year": false
}
```
Never includes token fields (unchanged behavior). For owners/standalone users, payload is unchanged except the two new fields.

### GET `/api/v1/profile/next-invoice-number`

Behavior change: for employees, computes from the company owner's settings and the company-wide invoice set (plus owner's automation used-numbers via the agent feed). Request/response shape unchanged.

## 3. Owner-only write enforcement (employees get 403)

Existing endpoints gain a 403 for non-owner company members (`{"detail": "Only the company owner can update company settings"}`):

| Endpoint | Purpose |
|---|---|
| `PUT /api/v1/auth/profile/fbr-credentials` | FBR tokens / seller identity |
| `PUT /api/v1/profile/invoice-settings` | numbering settings |
| auto-posting config update (route behind `frontend/src/services/autoPostingApi.ts`) | auto-posting toggle/times/env/limit/pause |

Portal-admin endpoints (`/api/v1/admin/*`) are unchanged.

## 4. Data-scoping behavior changes (no shape changes)

Existing GET/action endpoints keep their contracts; only the row set changes for company members: invoice list/history/detail/PDF, buyers, saved products (list/get/update/delete now company-wide for members), dashboard stats, reports, next-invoice-number. Employees gain 403 only on: deleting automation-posted invoices (`automation_invoice_id` set) and the owner-only writes above.

## 5. AI-agent (direct calls, `/api/v1/automation/…`)

- All automation endpoints (excel, dashboard, agent_status, pdf, file_management, retry) enforce a real gate: after JWT verification, the agent loads the User from the main DB and rejects with **403** `{"detail": "Automation access not enabled. Please contact your administrator."}` when `role != "admin"` and `automation_enabled != true`.
- `GET /api/v1/automation/invoice-numbers/used` stays authenticated-only (unchanged response contract) but resolves the number set for the caller's **company owner** when the caller is an employee (member rows return no numbers themselves). Response: `{ "used_numbers": ["INV-0001", …] }`.
- No shape changes elsewhere.

## 6. Auth changes

- Login rejects `is_active == false`: 403 `{"detail": "Account deactivated. Please contact your administrator."}` (checked after account_status, before password verify to avoid leaking status — implementation detail for tasks).
