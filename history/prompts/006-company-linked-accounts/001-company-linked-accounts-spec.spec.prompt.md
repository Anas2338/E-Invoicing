---
id: PHR-006-spec-001
title: company-linked-accounts-spec
stage: spec
date: 2026-09-05
surface: claude-code
model: deepseek-v4-flash
feature: 006-company-linked-accounts
branch: 006-company-linked-accounts
user: Muhammad Anus
command: /sp.specify
labels: [spec, company-accounts, employees, automation-access, shared-data]
links:
  spec: specs/006-company-linked-accounts/spec.md
  ticket: ''
  adr: ''
  pr: ''
files:
  - specs/006-company-linked-accounts/spec.md
  - specs/006-company-linked-accounts/checklists/requirements.md
tests: []
---

## Prompt

/sp.specify "feature=company-linked-accounts. Company owner account can add employee accounts via UI; employees: full workers minus Automation (hidden UI + server-blocked), shared company data (invoices/saved products/buyers/dashboard/reports), one shared FBR credential set on owner, auto-approved provisioning, deactivate-not-delete. Approved plan at C:\Users\HP\.claude\plans\inherited-swimming-lamport.md"

## Response snapshot

Created the feature specification for company-linked accounts on branch 006-company-linked-accounts. Key outputs:

- **6 user stories** prioritized P1-P3 covering: owner adds employee (P1), identical shared company data (P1), owner-only Automation with no bypass (P1), employee full manual invoicing under company identity (P2), owner single control of company settings + membership (P2), standalone customers unaffected (P3)
- **15 functional requirements** (FR-001..FR-015): provisioning with auto-approval and temp password, Automation blocked at navigation/page/service layers, identical company dataset for all members, per-invoice attribution, company-wide invoice numbering with no duplicates, consistent sandbox/production rules, read-only company settings for employees, owner-only deletion of automation-created invoices, deactivate-not-delete, duplicate-email guard, owner deletion guard while employees active, standalone regression guarantee, audit of employee access attempts
- **6 key entities**: Company, Company owner account, Employee account, Company dataset, FBR credentials (single owner-held set), Automation entitlement
- **8 documented assumptions**: owner-only provisioning, no automation via team UI, one owner per company for now, auto-approved employees, reversible deactivation (portal operators), credentials never copied to employees, public registration still creates standalone accounts
- **8 edge cases**: duplicate email vs public signup, add-employee during in-flight batches, concurrent numbering, missing/expired company credentials, deactivated employee with in-flight work, deactivated owner with active employees, environment access differences, employee deleting automation-created invoices
- **7 measurable success criteria**: sub-2-minute provisioning with Automation absent, 100% data match between pilot accounts, 100% block rate on employee Automation attempts, 0 duplicate invoice numbers, zero standalone regression, elimination of shared-login workaround, self-service resolution of staff-access requests

Design decisions carried from the approved plan: no new role (Automation entitlement stays per-account and owner-only), company ownership distinguished from portal admin, one FBR credential set never exposed to employees.

## Outcome

- ✅ Impact: Established a stakeholder-readable specification for allowing one company to have owner + employee accounts with a fully shared dataset while keeping Automation strictly owner-only and enforceable at every layer
- 🧪 Tests: N/A (spec phase)
- 📁 Files: specs/006-company-linked-accounts/spec.md, specs/006-company-linked-accounts/checklists/requirements.md
- 🔁 Next prompts: /sp.plan (spec is clarification-free; /sp.clarify not needed — all product decisions were confirmed with the customer before spec writing)
- 🧠 Reflection: Three-agent codebase research completed before spec writing grounded every requirement in existing architecture (per-user data silos, existing per-account Automation flag, missing server-side enforcement). The spec deliberately stays implementation-neutral while preserving the security requirement that Automation restriction must be enforced at the service layer, not just the interface.

## Evaluation notes (flywheel)

- Failure modes observed: None in spec writing; tooling issue only — create-new-feature.ps1 crashed on Join-Path multi-arg under PowerShell 5.1 after creating the branch and spec copy (prompts dir + env var had to be created manually)
- Graders run and results (PASS/FAIL): Specification quality checklist validation PASS — all 16 items verified on first run
- Prompt variant (if applicable): standard /sp.specify
- Next experiment (smallest change to try): N/A
