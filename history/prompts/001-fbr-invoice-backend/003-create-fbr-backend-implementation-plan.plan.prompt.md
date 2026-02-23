---
id: 003
title: Create FBR backend implementation plan
stage: plan
date: 2026-02-22
surface: agent
model: claude-opus-4-6
feature: 001-fbr-invoice-backend
branch: 001-fbr-invoice-backend
user: Anas2338
command: /sp.plan
labels: ["architecture", "planning", "fbr", "backend", "fastapi", "sqlmodel"]
links:
  spec: specs/001-fbr-invoice-backend/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-fbr-invoice-backend/plan.md
  - specs/001-fbr-invoice-backend/research.md
  - specs/001-fbr-invoice-backend/data-model.md
  - specs/001-fbr-invoice-backend/contracts/openapi.yaml
  - specs/001-fbr-invoice-backend/quickstart.md
  - CLAUDE.md (updated with tech stack)
tests:
  - Constitution check passed (all principles satisfied)
  - Technology stack validated via Context7 documentation
---

## Prompt

Project: Backend Architecture & Implementation Plan — FBR Invoice Integration Portal

Goal: Define technical architecture, implementation phases, integration approach, and validation strategy for building the FastAPI backend that integrates with FBR systems.

Planning principles:
- Spec-first development using FBR technical specification as source of truth
- Security-first backend design
- Separation of concerns (API, services, integration, data layer)
- Auditability and compliance readiness
- Scalable and environment-isolated architecture

User correction: Use Neon PostgreSQL database instead of Supabase

## Response snapshot

Created comprehensive architectural plan for FBR Invoice Integration Backend with complete Phase 0 (research) and Phase 1 (design) artifacts.

**Planning Artifacts Created**:

1. **plan.md** (7 implementation phases):
   - Phase 1: Foundation (project setup, dependencies, JWT middleware)
   - Phase 2: Data Layer (SQLModel models, migrations)
   - Phase 3: Core Invoice APIs (CRUD operations)
   - Phase 4: FBR Validation Integration
   - Phase 5: FBR Posting Integration (with idempotency)
   - Phase 6: Logging & Audit
   - Phase 7: Hardening (rate limiting, retry tuning)

2. **research.md** (technology decisions):
   - FastAPI 0.115+ (async web framework)
   - SQLModel 0.0.24+ (ORM with Pydantic integration)
   - httpx 0.28+ (async HTTP client with retry)
   - Neon PostgreSQL (serverless PostgreSQL)
   - python-jose (JWT handling)
   - Alembic (database migrations)
   - pytest + pytest-asyncio + respx (testing)

3. **data-model.md** (database schema):
   - 4 tables: Invoice, FBRResponse, AuditLog, IdempotencyCache
   - JSONB storage for invoice payloads (flexible schema)
   - Optimistic locking via version field
   - State machine enforcement (draft → validated → posted/failed)
   - Comprehensive indexes for query performance

4. **contracts/openapi.yaml** (API specification):
   - 10 REST endpoints with full OpenAPI 3.1 spec
   - JWT Bearer authentication
   - Request/response schemas
   - Error responses (400, 401, 403, 404, 409)
   - Idempotency header support

5. **quickstart.md** (developer guide):
   - Prerequisites and setup instructions
   - Environment configuration
   - Database migration steps
   - Testing commands
   - Troubleshooting guide
   - Development workflow

**Key Architectural Decisions**:

1. **Async Architecture**: Fully async (FastAPI + httpx + asyncpg) for non-blocking I/O during FBR API calls (1-3s latency)

2. **Hybrid Storage**: JSONB for invoice payloads + normalized metadata for efficient filtering

3. **Optimistic Locking**: Version field on Invoice model to prevent race conditions without holding locks during slow FBR calls

4. **PostgreSQL Idempotency Cache**: 24h TTL cache in PostgreSQL (no Redis dependency) for preventing duplicate posts

5. **Selective Retry Logic**: Retry only 5xx and 429 responses (not 4xx client errors) with exponential backoff

6. **JWT Dependency Injection**: FastAPI Depends() pattern for clean, reusable authentication

**Architecture Highlights**:

- **Layered Design**: API → Service → Integration → Data (clear separation of concerns)
- **Environment Isolation**: Separate sandbox/production configs with explicit selection
- **State Machine**: Enforced invoice lifecycle (draft → validated → posted/failed)
- **Security**: JWT on every request, row-level user_id filtering, API key for FBR
- **Audit Trail**: Immutable logs for all FBR interactions
- **Concurrency**: Optimistic locking + idempotency for safe concurrent operations

**Constitution Compliance**:
- ✅ Compliance-First: FBR spec drives all models
- ✅ Security by Design: JWT + row-level isolation
- ✅ Spec-Driven: No hardcoded assumptions
- ✅ Data Integrity: Complete audit trail
- ✅ Environment Isolation: Strict separation
- ✅ Architectural Constraints: FastAPI + SQLModel + Neon PostgreSQL
- ✅ API Design: RESTful + versioned + schema-based

**Technology Research**:
- Fetched FastAPI documentation for dependency injection and async patterns
- Fetched SQLModel documentation for async sessions and relationships
- Fetched httpx documentation for retry logic and timeout handling
- Validated all technology choices against project requirements

**Agent Context Updated**:
- Added Python 3.11+ to CLAUDE.md
- Added FastAPI, SQLModel, httpx, asyncpg to framework list
- Added Neon PostgreSQL to database list

## Outcome

- ✅ Impact: Complete architectural plan ready for implementation (Phase 2: tasks generation)
- 🧪 Tests: Constitution check passed, technology stack validated
- 📁 Files: 5 planning artifacts created (plan, research, data-model, contracts, quickstart)
- 🔁 Next prompts: Ready for `/sp.tasks` to generate implementation tasks
- 🧠 Reflection: Comprehensive plan with clear phases, well-researched technology decisions, detailed data model, complete API contracts, and developer-friendly quickstart guide. All constitution principles satisfied. Neon PostgreSQL correctly used instead of Supabase.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Constitution check - PASS (all 10 principles satisfied)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
