---
id: 002
title: Create Frontend Implementation Plan
stage: plan
date: 2026-02-23
surface: agent
model: claude-opus-4-6
feature: 002-fbr-invoice-portal
branch: 002-fbr-invoice-portal
user: user
command: /sp.plan
labels: ["planning", "frontend", "architecture", "nextjs", "react-query", "better-auth"]
links:
  spec: specs/002-fbr-invoice-portal/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-fbr-invoice-portal/plan.md
  - specs/002-fbr-invoice-portal/research.md
  - specs/002-fbr-invoice-portal/data-model.md
  - specs/002-fbr-invoice-portal/quickstart.md
  - specs/002-fbr-invoice-portal/contracts/api-contracts.md
tests:
  - none
---

## Prompt

Project: Frontend Architecture & Implementation Plan — FBR Invoice Integration Portal

Goal of this plan:
Define the frontend architecture, implementation phases, UI structure, API integration strategy, and quality validation approach for building the Next.js application that interacts with the FastAPI backend.

Planning principles:
- Backend-driven UI (frontend reflects backend contracts, not invents logic)
- Security-first session handling
- Clear separation between UI state and server state
- Scalable component architecture
- Performance and UX optimized
- Spec-aligned form structure (based on FBR field definitions via backend)

External knowledge requirements:
- Use Context7 to retrieve latest official documentation for:
  - Next.js (App Router)
  - React (latest stable)
  - TypeScript
  - Better Auth
  - React Query (or equivalent data-fetching library)
  - Form validation libraries
- Always use latest stable versions of dependencies
- Combine official docs with frontend engineering best practices

Architecture to define:
1. Application architecture (App Router structure, layouts, route groups, Server vs Client Components)
2. State architecture (server state, UI state, caching, error handling)
3. Auth architecture (Better Auth integration, protected routes, token usage, logout)
4. API integration layer (central client, request/response handling, error normalization)
5. Form architecture (schema-driven forms, dynamic fields, validation layering)
6. UI structure (dashboard, invoice forms, tables, filters)

Implementation phases:
Phase 1 — Foundation (Next.js setup, dependencies, folder structure, styling)
Phase 2 — Authentication (Better Auth, login/signup, route protection, session)
Phase 3 — Core Layout & Navigation (sidebar, header, environment selector, dashboard)
Phase 4 — Invoice Creation UI (dynamic forms, validation, draft save, validation trigger)
Phase 5 — Validated Invoices UI (data table, multi-select, post-to-FBR, status indicators)
Phase 6 — Invoice History (filters, detail view, FBR response display)
Phase 7 — PDF Download Flow (API integration, file handling)
Phase 8 — UX Hardening (loading skeletons, error boundaries, toast system, accessibility)

Decisions to document:
- Server Components vs Client Components boundaries
- React Query vs alternatives for server state
- Form library choice and schema integration
- Global state vs local state tradeoffs
- Table rendering strategy
- Error display patterns
- Token storage approach
- Caching and revalidation strategy

## Response snapshot

Created comprehensive frontend implementation plan for FBR Invoice Integration Portal on branch 002-fbr-invoice-portal.

**Phase 0: Research (Completed)**
Dispatched 5 parallel research agents using Context7 to fetch latest documentation:
1. UI component libraries (shadcn/ui, Material-UI, Chakra UI, Tailwind CSS)
2. State management strategies (React Query, SWR, native Next.js)
3. Form handling libraries (React Hook Form, Formik, Zod, Yup)
4. Better Auth integration with Next.js App Router
5. Next.js App Router architecture and best practices

Consolidated findings in research.md with technology decisions:
- UI: shadcn/ui + Tailwind CSS (minimal bundle, accessibility-first, zero lock-in)
- State: React Query for server state, useState/useReducer for UI state
- Forms: React Hook Form + Zod (performance, TypeScript-first, dynamic arrays)
- Auth: Better Auth with HTTP-only cookies (security, Next.js native)
- Architecture: App Router with Server Components by default

**Phase 1: Design & Contracts (Completed)**
Created comprehensive design artifacts:

1. **data-model.md**: TypeScript interfaces and types
   - Core entities: User, Invoice, LineItem, Session, FBRResponse
   - Form models with Zod schemas
   - API request/response models
   - UI state models (filters, table state, modals)
   - Error models and type guards
   - Constants and utility types

2. **contracts/api-contracts.md**: REST API contracts
   - 20+ endpoint definitions with request/response examples
   - Authentication endpoints (signup, login, logout, session)
   - Invoice endpoints (CRUD, validate, post, PDF)
   - Dashboard and user endpoints
   - Error codes and rate limiting
   - Idempotency support

3. **quickstart.md**: Setup and development guide
   - Step-by-step project setup (30-45 minutes)
   - Environment configuration
   - Better Auth setup
   - React Query setup
   - API client setup
   - Common issues and solutions
   - Development commands

4. **plan.md**: Comprehensive implementation plan
   - Technical context (TypeScript, Next.js 15+, dependencies)
   - Constitution check (all requirements met ✅)
   - Project structure (detailed folder hierarchy)
   - 6 architecture decisions documented with rationale
   - 8 implementation phases with tasks and acceptance criteria
   - API integration points
   - Testing strategy
   - Performance optimization
   - Security considerations
   - Risk mitigation
   - Success metrics

**Key Architecture Decisions:**

1. **UI Components**: shadcn/ui + Tailwind CSS
   - Rationale: 70% smaller bundle than MUI, accessibility-first, full customization
   - Bundle impact: ~60-70KB vs 180KB+ for MUI

2. **State Management**: React Query + Native React Hooks
   - Rationale: Built-in optimistic updates, sophisticated caching, meets < 1s perceived delay
   - Caching: 5-minute stale time, 10-minute cache time

3. **Form Handling**: React Hook Form + Zod
   - Rationale: Uncontrolled components for performance, handles 100+ line items without lag
   - Bundle: ~9KB vs Formik's ~15KB

4. **Authentication**: Better Auth with HTTP-only cookies
   - Rationale: Native Next.js support, XSS protection, CSRF protection, session persistence
   - Security: HTTP-only, secure flag, SameSite=lax

5. **Data Tables**: TanStack Table v8
   - Rationale: Headless UI, built-in sorting/filtering/pagination, TypeScript-first
   - Features: Multi-column sorting, row selection, column visibility

6. **Server vs Client Components**: Server by default, Client only when necessary
   - Server: Layouts, static content, initial data fetching
   - Client: Forms, interactive elements, React Query hooks, browser APIs

**Implementation Phases (8 phases, 22-30 days estimated):**

Phase 1: Foundation & Setup (2-3 days)
- Next.js project setup, dependencies, folder structure, Better Auth, middleware

Phase 2: Authentication UI (2-3 days)
- Login/signup pages, form validation, session handling, logout

Phase 3: Dashboard Layout & Navigation (2-3 days)
- Sidebar, header, environment selector, dashboard stats

Phase 4: Invoice Creation Form (4-5 days)
- Dynamic line items, auto-calculation, validation, save draft, validate

Phase 5: Validated Invoices & Posting (3-4 days)
- Data table, multi-select, bulk posting, progress indicator

Phase 6: Invoice History & Filtering (3-4 days)
- Advanced filters, invoice details, PDF download, pagination

Phase 7: Draft Management & Editing (2-3 days)
- Edit drafts, delete drafts, resume functionality

Phase 8: UX Hardening & Polish (3-4 days)
- Loading skeletons, error boundaries, toast notifications, accessibility

**Constitution Compliance:**
✅ All architectural constraints met
✅ Security standards implemented
✅ API design rules followed
✅ No business logic in frontend
✅ Environment isolation enforced
✅ JWT tokens in HTTP-only cookies only

**Performance Targets:**
- Initial page load: < 3 seconds on 3G
- Time to Interactive: < 5 seconds
- Lighthouse score: > 80
- Form validation: < 500ms feedback
- Bundle size: < 200KB gzipped

**Deliverables:**
- research.md (technology decisions with rationale)
- data-model.md (TypeScript interfaces and schemas)
- api-contracts.md (20+ REST API endpoints)
- quickstart.md (setup guide)
- plan.md (comprehensive implementation plan)

## Outcome

- ✅ Impact: Complete frontend architecture and implementation plan ready for task generation
- 🧪 Tests: No tests created (planning phase)
- 📁 Files: 5 files created (plan.md, research.md, data-model.md, quickstart.md, api-contracts.md)
- 🔁 Next prompts: `/sp.tasks` to generate detailed task breakdown from implementation plan
- 🧠 Reflection: Successfully completed comprehensive planning with parallel research agents. All technology decisions documented with rationale. 8 implementation phases defined with clear acceptance criteria. Constitution compliance verified. Ready for task generation and implementation.

## Evaluation notes (flywheel)

- Failure modes observed: None - all research agents completed successfully, all artifacts generated
- Graders run and results (PASS/FAIL): Constitution check - PASS (all requirements met)
- Prompt variant (if applicable): Standard /sp.plan workflow with parallel research agents
- Next experiment (smallest change to try): Consider pre-generating common Zod schemas during planning phase to reduce implementation time
