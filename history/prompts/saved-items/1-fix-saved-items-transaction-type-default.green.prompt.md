---
id: 1
title: fix saved items transaction type default
stage: green
date: 2026-05-21
surface: agent
model: deepseek-v4-pro[1m]
feature: saved-items
branch: master
user: Muhammad Anus
command: "in profile page, when user add Saved Items manually, i want when user click add item, value of Transaction Type * set to default_sale_type, currently it saved code of value to transaction type, i check it manually in database dashboard."
labels: [bug-fix, frontend, backend, saved-items]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - frontend/src/components/profile/SavedItemsSection.tsx
  - backend/src/api/v1/saved_products.py
tests:
---
## Prompt

in profile page, when user add Saved Items manually, i want when user click add item, value of Transaction Type * set to default_sale_type, currently it saved code of value to transaction type, i check it manually in database dashboard.

## Response snapshot

Fixed two issues:
1. Transaction Type dropdown now pre-fills with the first available transaction type when opening the Add Item form, instead of being empty.
2. `default_sale_type` is now sent from the frontend with the transaction type name, preventing the backend from falling back to the hardcoded default "01" (a code, not a name).
3. Backend `default_sale_type` Pydantic default changed from "01" (code) to None for consistency.

## Outcome

- Impact: Transaction Type dropdown now auto-selects default; default_sale_type saves proper name instead of code "01"
- Tests: Manual verification required
- Files: 2 files modified (frontend + backend)
- Next prompts: null
- Reflection: The root cause was that the dropdown had no default selection and the frontend never sent default_sale_type, so the backend hardcoded "01" (a code value). Fix pre-fills dropdown and sends default_sale_type explicitly.

## Evaluation notes (flywheel)

- Failure modes observed: Empty dropdown default caused user confusion; backend fallback to code "01" polluted database with inconsistent values
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
