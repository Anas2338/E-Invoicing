---
id: 001
title: "Separate AI-Agent Specification"
stage: spec
date: 2026-05-13
surface: agent
model: deepseek-v4-pro
feature: 001-separate-ai-agent
branch: 001-separate-ai-agent
user: HP
command: /sp.specify
labels: ["automation","ai-agent","separation","fbr-compliance","backend"]
links:
  spec: specs/001-separate-ai-agent/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-separate-ai-agent/spec.md
  - specs/001-separate-ai-agent/checklists/requirements.md
tests:
  - (none yet — spec phase)
---

## Prompt

```
Separate automation (AI-agent) code from main backend into a standalone ai-agent/ directory for FBR compliance. The main backend handles current/past-date manual invoices. The ai-agent handles future-date Excel-uploaded automation invoices. Both databases already exist separately. All functionality must remain the same after separation. Frontend will call two separate backends.
```

## Response snapshot

Created specification for separating automation (AI-agent) from the main backend. The spec defines 4 user stories: (P1) Portal operator uses manual invoices normally, (P1) Automation user uploads future-date invoices via AI-agent, (P2) Administrator manages AI-agent health, (P1) Frontend communicates with both backends. 14 functional requirements mandate zero automation code in the main backend, a standalone AI-agent service, and identical API behavior. 7 success criteria cover file auditability, service independence, API parity, and frontend routing correctness. Edge cases cover AI-agent unavailability, unified invoice history, shared dependency sync, and manual Excel upload decoupling.

## Outcome

- ✅ Impact: Spec defines the complete separation boundary between main backend (manual invoices) and AI-agent (future-date automation). 14 functional requirements, 7 success criteria, 4 independently testable user stories.
- 🧪 Tests: None yet — planning phase will generate testable tasks.
- 📁 Files: spec.md with 4 user stories + 14 FRs + 7 SCs; requirements.md checklist (all items passing).
- 🔁 Next prompts: `/sp.clarify` (if ambiguities found) or `/sp.plan` to generate the implementation plan.
- 🧠 Reflection: The spec captures the key constraint: FBR compliance via physical code separation. Both databases already separate; the work is purely a code reorganization + frontend routing update. No [NEEDS CLARIFICATION] markers needed — the existing codebase exploration provided sufficient context.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
