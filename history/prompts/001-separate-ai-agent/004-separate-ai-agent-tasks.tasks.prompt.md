---
id: 004
title: "AI-Agent Separation Task Breakdown"
stage: tasks
date: 2026-05-13
surface: agent
model: deepseek-v4-pro
feature: 001-separate-ai-agent
branch: 001-separate-ai-agent
user: HP
command: /sp.tasks
labels: ["tasks","automation","ai-agent","separation","implementation"]
links:
  spec: specs/001-separate-ai-agent/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-separate-ai-agent/tasks.md
tests:
  - (none — tests not explicitly requested in spec)
---

## Prompt

```
/sp.tasks
```

## Response snapshot

Generated 81 tasks organized across 7 phases mapped to 4 user stories:

- **Phase 1: Setup** (T001-T006): ai-agent/ skeleton, pyproject.toml with uv, .env.example, Dockerfile, alembic config
- **Phase 2: Foundational** (T007-T017): AI-agent core infrastructure — settings, database session, auth middleware, CSRF, main.py
- **Phase 3: US1** (T018-T031): Clean backend — remove 5 models, 4 schemas, 4 services, 7 route files, automation engine from session.py, extract ManualExcelHelper for manual Excel upload
- **Phase 4: US2** (T032-T061): AI-agent automation endpoints — move/copy all automation models, schemas, services, routes; dedicated PDF service; all 24 endpoints
- **Phase 5: US3** (T062-T068): AI-agent health endpoints — health.py, agent_status.py, AIAgentHealthCheck model
- **Phase 6: US4** (T069-T075): Frontend routing — automationApi.ts URL, CSRF per backend, unified history merge, env vars, next.config.js
- **Phase 7: Polish** (T076-T081): Validation checklist, cross-import audit, file audit, test suite, uv.lock generation

Key design: US1 (backend cleanup) runs in parallel with US2 (AI-agent build) — different directories, no conflicts. US2 has 30+ tasks, heavily parallelizable across models/schemas/services/routes groups.

## Outcome

- ✅ Impact: 81 tasks, 4 independently testable user stories, 3 parallel team strategy
- 🧪 Tests: None (not requested in spec; validation via quickstart.md checklist)
- 📁 Files: tasks.md created with strict checklist format (checkbox, ID, [P] marker, [Story] label, file path)
- 🔁 Next prompts: `/sp.implement` to execute tasks
- 🧠 Reflection: Tasks scoped to smallest viable diffs. US1 (14 tasks) is true MVP — achieves FBR compliance by cleaning backend. US2 (30 tasks) adds full AI-agent functionality. US4 bridges frontend to both backends.
