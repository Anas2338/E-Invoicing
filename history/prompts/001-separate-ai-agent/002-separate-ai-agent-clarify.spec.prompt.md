---
id: 002
title: "Clarify AI-Agent Separation Spec"
stage: spec
date: 2026-05-13
surface: agent
model: deepseek-v4-pro
feature: 001-separate-ai-agent
branch: 001-separate-ai-agent
user: HP
command: /sp.clarify
labels: ["clarification","automation","ai-agent","separation","fbr-compliance"]
links:
  spec: specs/001-separate-ai-agent/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-separate-ai-agent/spec.md
tests:
  - (none yet — spec phase)
---

## Prompt

```
/sp.clarify
```

## Response snapshot

Conducted structured ambiguity scan across 10 taxonomy categories. Asked 2 questions:
1. **Unified invoice history**: Resolved with Option A — Frontend merges results from both backends. Main backend returns only manual invoices; frontend fetches from both and merges/sorts.
2. **CSRF protection across services**: Resolved with Option A — Independent CSRF per backend. Each issues/validates its own tokens. Frontend manages separate tokens per backend. Both use identical configuration.

Added FR-015 for CSRF requirement. Updated edge cases and assumptions to reflect decisions. No remaining critical ambiguities.

## Outcome

- ✅ Impact: 2 high-impact ambiguities resolved. Spec now has 15 FRs, 7 SCs, clear data flow for unified history, and explicit CSRF strategy.
- 🧪 Tests: None yet.
- 📁 Files: spec.md updated with Clarifications section, FR-015 added, edge cases and assumptions updated.
- 🔁 Next prompts: `/sp.plan` to generate implementation plan.
- 🧠 Reflection: Most categories were Clear from the initial spec. The two clarifications resolved the only Partial areas (interaction flow and security posture). Remaining gaps are implementation details best handled in planning.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
