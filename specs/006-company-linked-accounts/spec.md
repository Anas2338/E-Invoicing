# Feature Specification: Company Linked Accounts (Owner + Employee, Shared Data)

**Feature Branch**: `006-company-linked-accounts`  
**Created**: 2026-09-05  
**Status**: Draft  
**Input**: User description: "feature=company-linked-accounts. Company owner account can add employee accounts via UI; employees: full workers minus Automation (hidden UI + server-blocked), shared company data (invoices/saved products/buyers/dashboard/reports), one shared FBR credential set on owner, auto-approved provisioning, deactivate-not-delete. Approved plan at C:\Users\HP\.claude\plans\inherited-swimming-lamport.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Company owner adds an employee account (Priority: P1)

A customer company using the portal (including the Automation feature) wants to give its staff their own login instead of sharing the company login. From the portal, the company's owner account can add an employee account (name, email, and a generated temporary password). The employee can log in immediately — no waiting for a separate approval step. If the employee later needs to be removed, the owner can deactivate the account; the employee's login stops working but the company's data is never lost.

**Why this priority**: This is the entry point for the entire feature — without account provisioning nothing else is possible, and it immediately removes the unsafe practice of staff sharing one login.

**Independent Test**: Can be fully tested by logging in as a company owner, adding an employee with a fresh email, and logging in as that employee — the employee gains access to the portal right away.

**Acceptance Scenarios**:

1. **Given** a company owner account is logged in, **When** the owner adds an employee with a valid email, name, and generated temporary password, **Then** the account is created, shown once to the owner, and the employee can log in immediately with it.
2. **Given** an employee account was added, **When** the employee's account is deactivated by the owner, **Then** the employee can no longer log in, but all invoices and data created by them remain visible to the company.
3. **Given** an email that is already registered, **When** the owner tries to add an employee with it, **Then** a clear error is shown and no account or partial data is created.
4. **Given** an owner with active employees, **When** anything (portal admin or system) attempts to delete the owner account outright, **Then** the system refuses or requires employees to be deactivated first, because their data belongs to the company.

---

### User Story 2 - Both accounts see the same company data (Priority: P1)

Because the owner and employee accounts belong to the same company, both must see one identical dataset: invoice history (including invoices created by the Automation feature), saved products, saved buyers, dashboard statistics, and reports. An invoice created by the employee appears on the owner's dashboard and history, and vice versa. Neither account needs to do anything to "share" — it just works because they are the same company.

**Why this priority**: This is the core behavioral promise of the feature ("all data same in both accounts") and the reason a second account is useful at all.

**Independent Test**: Log in as the owner, note the full invoice list and counts; log in as the employee and confirm the same invoices, saved products, buyers, dashboard numbers, and reports are visible (and that each invoice still shows who created it).

**Acceptance Scenarios**:

1. **Given** an owner and an employee of the same company, **When** either one opens invoice history, dashboard, saved products, buyers, or reports, **Then** both see the same company-wide set of records.
2. **Given** invoices posted through Automation by the owner, **When** the employee opens invoice history, **Then** those invoices are visible to the employee (the Automation module itself is not).
3. **Given** records created by a deactivated employee, **When** the owner opens history/dashboard, **Then** those records remain visible and attributable to that employee.

---

### User Story 3 - Automation is owner-only, with no way around it (Priority: P1)

The company has stated that Automation is not allowed for employees. An employee login must never see the Automation module: it does not appear in navigation, its pages cannot be opened by typing the address, and calls to the Automation service itself are rejected — not just hidden. Only the company owner account can use Automation.

**Why this priority**: This is the company's stated reason for the two-account setup — it is a policy/security requirement, so hiding the menu alone is not enough; access must be denied at every layer.

**Independent Test**: Log in as the employee and confirm the module is absent; then attempt to open the Automation pages directly and to call the Automation service with the employee's login — all attempts fail with a clear "not allowed" outcome.

**Acceptance Scenarios**:

1. **Given** an employee account, **When** they view the portal navigation, **Then** the Automation module is not shown.
2. **Given** an employee account, **When** they type an Automation page address directly, **Then** they are redirected away with a clear message that Automation access is not enabled.
3. **Given** an employee account, **When** they attempt to use any Automation service directly (bypassing the interface), **Then** the request is rejected by the service itself, not merely hidden in the interface.
4. **Given** the owner account, **When** they log in, **Then** the Automation module is present and works exactly as before.

---

### User Story 4 - Employee is a full manual invoicing worker under the company identity (Priority: P2)

Employees continue doing the normal manual work of the portal: creating invoices, validating them, and submitting them to FBR — using the company's one set of FBR credentials and the company's seller identity and invoice numbering. New invoice numbers continue the company's existing sequence so numbers never collide between the two accounts. The system records which account created each invoice for accountability. Employees cannot submit on behalf of another company and cannot use credentials they were never given.

**Why this priority**: This preserves the employee's day-to-day usefulness; without it the feature would be view-only, which is not the requirement.

**Independent Test**: As an employee, create, validate, and submit an invoice to FBR; confirm it is submitted with the company's registered identity and receives the next number in the company's sequence, and that it then appears for the owner too.

**Acceptance Scenarios**:

1. **Given** an employee account of a company that has valid FBR credentials, **When** the employee creates and submits an invoice, **Then** the submission uses the company's FBR identity and credentials, and succeeds exactly as an owner submission would.
2. **Given** a company where the owner's invoice numbering settings are in place, **When** either member creates an invoice, **Then** numbers continue one shared company sequence with no duplicates, even when both create invoices at the same time.
3. **Given** invoices already in the company's history, **When** the employee creates a new invoice, **Then** the system proposes the next unused number rather than restarting a private sequence for the employee.
4. **Given** an employee and the owner of the same company, **When** either tries to submit an invoice, **Then** sandbox/production visibility and submission rules are consistent for the whole company.

---

### User Story 5 - Owner keeps single control of company settings and membership (Priority: P2)

The company's FBR credentials, seller/business identity, invoice numbering settings, and Automation settings remain a single source of truth controlled by the owner account. Employees see the company identity where needed (for example when creating invoices) but cannot change company credentials, numbering, or Automation settings, and cannot manage the team. Portal operators retain their existing oversight of all accounts.

**Why this priority**: Prevents the very drift the shared-credential decision is designed to avoid (diverging company profiles, duplicate credentials), and keeps the owner as the accountable party.

**Independent Test**: Log in as the employee and confirm that company credential/numbering/Automation settings are not editable; log in as the owner and confirm they can still change them and manage employees.

**Acceptance Scenarios**:

1. **Given** an employee account, **When** they open profile/settings, **Then** company credentials, seller identity fields, invoice numbering, and Automation settings are read-only or hidden, and attempts to change them via any interface are rejected.
2. **Given** the owner account, **When** they open the same settings, **Then** they can edit company credentials, seller identity, numbering, and Automation settings as before.
3. **Given** the owner account, **When** they open the team section, **Then** they can add and deactivate employees; employees see no team-management capability.
4. **Given** an employee with no FBR credentials of their own, **When** the system needs company credentials, **Then** it always uses the company's single registered set, and the employee never sees or receives those credentials.

---

### User Story 6 - Existing single-account customers are unaffected (Priority: P3)

Every existing customer today has one account that represents their whole company. After this feature ships, their experience must be unchanged: they see exactly their own data, their Automation access is whatever it was, and nothing new is required of them.

**Why this priority**: Regression safety for the whole existing customer base; the feature must not impose company mechanics on customers that never asked for them.

**Independent Test**: Log in with a normal standalone account and confirm dashboard, invoices, saved products, and Automation behavior are identical to before; no team features appear.

**Acceptance Scenarios**:

1. **Given** a standalone customer account — the owner of its own single-member company (`company_id == id`) — **When** they use the portal as before, **Then** all existing screens and behavior are unchanged.
2. **Given** a standalone customer account (a single-member company owner), **When** they open Settings, **Then** the Team section is visible and lists only themselves as the single member — team mechanics run only via owner-type accounts (FR-014), and employees never see them.
3. **Given** an Automation-enabled standalone customer, **When** they log in, **Then** Automation still works exactly as before.

---

### Edge Cases

- What happens when an employee is created with an email that later registers through the public signup form?
- How does the system behave when the owner attempts to add an employee while an invoice batch or submission is in progress?
- What happens when two members create invoices at the exact same moment — can numbers collide?
- What happens when the company's FBR credentials are missing or expired and an employee tries to submit an invoice? (Clear guidance must be shown; no partial submission.)
- What happens if a deactivated employee has in-flight work (staging batches, pending submissions)? Does the work stay with the company?
- What happens if the owner's account is itself deactivated or suspended while employees are active?
- How does the system handle employees whose sandbox/production access differs from the owner's, if company access is granted?
- What happens when an employee tries to delete an invoice that came from the Automation feature?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a company owner account to add an employee account with name, email, and a generated temporary password.
- **FR-002**: Added employee accounts MUST be immediately usable (no separate approval step) and MUST be able to log in with the temporary password.
- **FR-003**: The system MUST NOT show the Automation module to employee accounts — in navigation, by direct page address, or via the Automation service itself (all layers reject it).
- **FR-004**: All members of the same company MUST see one identical company dataset: invoices (manual and automation-created), saved products, saved buyers, dashboard statistics, and reports.
- **FR-005**: Each invoice MUST remain attributable to the member account that created it.
- **FR-006**: Employees MUST be able to create, validate, and submit manual invoices using the company's single registered FBR credentials and seller identity.
- **FR-007**: Invoice numbering MUST follow one company-wide sequence using the owner's numbering settings, with no duplicate numbers under any concurrency scenario.
- **FR-008**: Sandbox/production visibility and submission rules MUST be consistent across all members of a company.
- **FR-009**: Employees MUST NOT be able to modify company FBR credentials, seller identity, invoice numbering, Automation settings, or team membership through any interface.
- **FR-010**: Employees MUST NOT be able to delete invoices that were created through the Automation feature; only the company owner may.
- **FR-011**: The company owner MUST be able to deactivate an employee account; deactivation MUST block login but MUST NOT delete or orphan company data.
- **FR-012**: The system MUST refuse to create an employee account with an email already in use and MUST leave no partial data behind.
- **FR-013**: The owner account MUST NOT be deletable while it still has active employee accounts.
- **FR-014**: Existing standalone customer accounts MUST behave exactly as before this feature; team mechanics MUST only appear for company owners.
- **FR-015**: Attempts by an employee to access Automation or modify protected company settings MUST be recorded for audit by portal operators.

### Key Entities *(include if feature involves data)*

- **Company**: A business entity using the portal, identified by its registered seller identity (e.g., NTN) and business details. Owns one dataset and one set of FBR credentials.
- **Company owner account**: The account that represents and controls a company — can manage employees, holds sole control of company credentials, seller identity, numbering, and Automation settings.
- **Employee account**: An additional login linked to a company. Full manual invoicing rights; no Automation access; no company-settings or team-management rights.
- **Company dataset**: All records owned by the company — invoices (manual and automation-created), saved products, saved buyers, dashboard data, reports — visible identically to every member.
- **FBR credentials**: The single set of sandbox/production credentials registered to the company; used for all submissions by any member.
- **Automation entitlement**: The owner-only capability to use the Automation module (uploads, scheduling, monitoring, background posting).

## Assumptions

- Only the company owner can add/deactivate employees; an employee cannot invite other employees.
- Employee accounts can never be granted Automation through the team interface; portal operators retain the only path to change Automation access.
- For now, one owner per company (the account that exists today); multiple owner-type accounts can be added later.
- Employees are auto-approved at creation (no pending queue), per the company's request.
- Deactivation is reversible only by portal operators.
- Company credentials always come from the single owner-held set; they are never copied onto employee accounts.
- Public self-registration continues to create standalone accounts (each its own company).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A company owner can add an employee and that employee can log in in under 2 minutes, with the Automation module absent.
- **SC-002**: For the pilot company, invoice history, saved products, dashboard figures, and reports match 100% between the owner and employee accounts.
- **SC-003**: 100% of attempts by an employee account to reach Automation (direct pages or direct service calls) are blocked; the owner's Automation experience is unchanged.
- **SC-004**: 0 duplicate invoice numbers across company members over a sustained period of concurrent invoice creation.
- **SC-005**: Zero regression for standalone accounts: existing customers see no change in data scope, features, or permissions.
- **SC-006**: Staff no longer need to share the company login to do manual invoicing — company reports eliminating shared-login use after rollout.
- **SC-007**: Support tickets asking "how do I give my staff access without Automation?" become resolvable via self-service (no manual account work by the portal operator).
