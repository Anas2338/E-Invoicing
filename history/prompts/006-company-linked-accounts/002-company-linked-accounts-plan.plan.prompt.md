---
id: PHR-006-plan-001
title: company-linked-accounts-plan
stage: plan
date: 2026-09-05
surface: claude-code
model: deepseek-v4-flash
feature: 006-company-linked-accounts
branch: 006-company-linked-accounts
user: Muhammad Anus
command: /sp.plan
labels: [plan, company-accounts, data-scoping, rbac, migration]
links:
  spec: specs/006-company-linked-accounts/spec.md
  ticket: ''
  adr: ''
  pr: ''
files:
  - specs/006-company-linked-accounts/plan.md
  - specs/006-company-linked-accounts/research.md
  - specs/006-company-linked-accounts/data-model.md
  - specs/006-company-linked-accounts/contracts/company-api.md
  - specs/006-company-linked-accounts/quickstart.md
tests:
  - backend/tests/test_company.py (planned)
---

## Prompt

/sp.plan "feature=006-company-linked-accounts. Spec at specs/006-company-linked-accounts/spec.md. Approved design plan at C:\Users\HP\.claude\plans\inherited-swimming-lamport.md. Company owner adds employee accounts (auto-approved, temp password, deactivate-not-delete); employees are full manual workers with identical shared company data (invoices/saved products/buyers/dashboard/reports); Automation owner-only enforced at nav/page/API layers (backend require_automation_access unwired, AI-agent gate is a no-op); one shared FBR credential set on the owner account with company-wide resolution; company_id on users (backfill id=own) + company-context service + company-scoped queries + profile additions; provisioning API + Team members UI; both model copies (backend + ai-agent) and both services deployed together."

## Response snapshot

Produced the complete plan phase on branch 006-company-linked-accounts:

- **research.md — 9 decisions (R1–R9)** grounded in two new precision inventories: R1 `users.company_id` self-reference company model (no new table); R2 owner-only provisioning, auto-approved, deactivate = `is_active=False` + `token_version` bump; R3 company scope for invoices/saved products/dashboard/reports/buyers, actor-scoped workspaces (staging/bulk tasks/logs/counters) and owner-only automation DB kept; R4 effective-user (owner) resolution for FBR tokens (5 posting sites inventoried), seller snapshot, environment filter (7 caller sites), profile payload, numbering; R5 company numbering + company-aware agent used-numbers feed (agent endpoint stays auth-only, resolves owner's numbers for members) + collision re-roll mitigation; R6 real automation gate on AI-agent + owner-only settings writes, and a documented correction: main-backend bulk endpoints are the MANUAL worker workflow, not automation — they stay open to employees; R7 one Alembic migration (`20260905_add_company_id_to_users`, head `20260727_add_excel_staging`) + both User model copies + deploy order (migrate → ship backend+agent together); R8 pytest extension plan per conftest conventions; R9 frontend: no new UI patterns, settings gating by `is_company_owner`, TeamMembersSection modeled on SavedItemsSection.
- **data-model.md**: the single column + semantics (owner self-ref, member scope predicate incl. deactivated employees), field rules for employee rows, per-table scope matrix, delete matrix (automation-posted invoices owner-only), numbering state.
- **contracts/company-api.md**: POST/GET employees + deactivate endpoints, profile payload diff, owner-only 403 matrix, scoping behavior notes, AI-agent 403 gate contract + company-aware invoice-numbers, login `is_active` rejection.
- **quickstart.md**: run/migration order, 9-step manual verification matrix mapped to spec SC-001..SC-007, pytest commands, production rollout order.
- **plan.md**: filled template — summary, technical context, constitution check with ONE justified deviation (row-level isolation relaxed to company scope, owner-consent authorization, ADR + constitution amendment flagged), project structure with real paths, 9-step implementation approach, verification.
- **CLAUDE.md** updated via update-agent-context.ps1 (language/framework/database lines).

## Outcome

- ✅ Impact: Converts the approved design into an executable, code-verified plan; caught one material plan error (bulk endpoints are manual workflow, not automation) before implementation; documented the one constitution deviation with justification
- 🧪 Tests: N/A (plan phase) — planned backend/tests/test_company.py per existing conftest conventions
- 📁 Files: plan.md, research.md, data-model.md, contracts/company-api.md, quickstart.md (+ CLAUDE.md agent context updated)
- 🔁 Next prompts: /sp.tasks (generate implementation tasks from plan.md/contracts)
- 🧠 Reflection: Implementation-point inventories (2 Explore agents, 200+ code sites examined) validated the earlier research and corrected a wrong assumption about which endpoints are "automation". The deviation from the user_id-isolation principle was surfaced explicitly rather than buried — the customer owner provisioning employees IS the authorization grant.

## Evaluation notes (flywheel)

- Failure modes observed: pre-plan research misclassified manual bulk endpoints as automation (corrected by line-level inventory before any code was written — caught at plan time, zero cost)
- Graders run and results (PASS/FAIL): Constitution check re-run PASS with one documented justified deviation; no unresolved NEEDS CLARIFICATION
- Prompt variant (if applicable): standard /sp.plan
- Next experiment (smallest change to try): N/A
