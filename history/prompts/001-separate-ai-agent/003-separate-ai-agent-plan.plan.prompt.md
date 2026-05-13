---
id: 003
title: "AI-Agent Separation Implementation Plan"
stage: plan
date: 2026-05-13
surface: agent
model: deepseek-v4-pro
feature: 001-separate-ai-agent
branch: 001-separate-ai-agent
user: HP
command: /sp.plan
labels: ["plan","automation","ai-agent","separation","architecture","fbr-compliance"]
links:
  spec: specs/001-separate-ai-agent/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-separate-ai-agent/plan.md
  - specs/001-separate-ai-agent/research.md
  - specs/001-separate-ai-agent/data-model.md
  - specs/001-separate-ai-agent/quickstart.md
  - specs/001-separate-ai-agent/contracts/automation-api.md
tests:
  - (none yet — tasks phase)
---

## Prompt

```
/sp.plan built plan according to current project structure, if relevant file or folder already exist dont built again and use same same technology stack and approaches
```

## Response snapshot

Generated implementation plan for separating automation code into standalone ai-agent/ directory. Plan defines:
- **Technical Context**: Python 3.11+, FastAPI, SQLModel, two Neon PostgreSQL DBs, multi-service architecture
- **Constitution Check**: All gates pass; one flag (duplicated shared services) with documented mitigation
- **Project Structure**: Three top-level directories (backend/, ai-agent/, frontend/) with detailed file mapping
- **Phase 0 (research.md)**: 10 research decisions covering shared code strategy, manual Excel decoupling, auth sharing, CSRF, PDF generation, transfer flow deferral, frontend routing, scheduler split, env config, deployment strategy
- **Phase 1 (data-model.md)**: Full entity mapping for both databases, AutomationInvoice state transitions, cross-DB reference handling
- **Phase 1 (contracts/automation-api.md)**: All 24 automation API endpoint contracts with request/response schemas
- **Phase 1 (quickstart.md)**: Step-by-step setup for all three services with verification checklist and env var reference

Key architectural decisions: duplicate shared services (not shared library), independent CSRF per backend, AI-agent has no login endpoint, TransferService deferred, frontend merges unified history.

## Outcome

- ✅ Impact: Complete implementation blueprint covering code organization, data models, API contracts, and deployment configuration for two-service architecture
- 🧪 Tests: None yet — tasks phase will generate test scenarios
- 📁 Files: 5 artifacts created (plan.md, research.md, data-model.md, quickstart.md, contracts/automation-api.md)
- 🔁 Next prompts: `/sp.tasks` to generate implementation task breakdown
- 🧠 Reflection: Plan leverages existing code patterns and tech stack. No new technology introduced. The 10 research decisions document all tradeoffs. Constitution check passes. Ready for task generation.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
