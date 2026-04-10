# Implementation Plan: AI Agent for Invoice Automation

**Branch**: `001-invoice-automation` | **Date**: 2026-04-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-invoice-automation/spec.md`

## Summary

Add an AI Agent powered by Claude Code to replace the existing hourly FTE worker with intelligent, continuous invoice processing. The AI Agent will monitor Excel uploads within 1 minute, process invoices with 5-minute precision (not hourly batches), intelligently classify errors, apply adaptive retry strategies, prioritize processing based on business rules, and perform hourly health checks. The agent runs as a Docker container with modular Python-based Agent Skills that orchestrate existing services (FBRClient, ValidationService) without modification.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI 0.115+, SQLModel 0.0.23+, APScheduler 3.10+ (for internal scheduling), httpx 0.28+ (async HTTP), pandas 2.2+, openpyxl 3.1+, Claude Code API (Anthropic SDK)  
**Storage**: Neon PostgreSQL (existing), extend automation_invoice table, create ai_agent_health_check table  
**Testing**: pytest 7.4+, pytest-asyncio 0.21+  
**Target Platform**: Docker container (Linux), managed via docker-compose alongside FastAPI backend  
**Project Type**: Web application (backend + AI agent container)  
**Performance Goals**: 
- Detect new uploads within 1 minute (95% of time)
- Process invoices within 5 minutes of scheduled time (90% of time)
- Health checks complete within 30 seconds
- 95% error classification accuracy

**Constraints**: 
- Must reuse existing FBRClient, ValidationService, database models
- No modification to manual invoice workflow
- Must maintain complete audit trail in automation_log
- Support both SANDBOX and PRODUCTION FBR environments
- Docker and docker-compose required in deployment environment

**Scale/Scope**: 
- Support up to 10,000 invoices per user
- Process up to 1,000 invoices per Excel upload
- Handle concurrent processing across multiple users
- 24/7 continuous operation with hourly health checks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Compliance-First Development
- AI Agent will use existing FBRClient which implements FBR specifications
- No changes to FBR validation or submission logic
- All FBR interactions remain spec-compliant

### ✅ Security by Design
- AI Agent operates within existing authentication framework
- Row-level data isolation maintained (user_id filtering)
- No new security vulnerabilities introduced
- Agent runs in isolated Docker container

### ✅ Spec-Driven Implementation
- AI Agent orchestrates existing spec-driven services
- No changes to FBR spec parsing or validation
- FBRClient remains single source of truth for FBR interactions

### ✅ Data Integrity and Auditability
- All AI Agent decisions logged to automation_log with rationale
- Complete audit trail maintained for all actions
- FBR responses stored unmodified (existing behavior preserved)

### ✅ Environment Isolation
- AI Agent respects existing SANDBOX/PRODUCTION separation
- No cross-environment contamination risk
- Environment selection per invoice maintained

### ✅ Security Standards
- AI Agent operates within existing JWT authentication framework
- Row-level isolation enforced in all database queries
- No new authentication mechanisms introduced

### ✅ Architectural Constraints
- Backend: FastAPI (unchanged)
- ORM: SQLModel (extended with new fields)
- Database: Neon PostgreSQL (schema extensions only)
- No business logic in frontend (AI Agent is backend component)
- All FBR communication through existing backend service layer

### ✅ Data Rules
- Invoice payloads stored as JSON (existing pattern)
- FBR responses stored unmodified (existing pattern)
- No invoice deletion (status transitions only)
- Precise numeric handling for monetary values (existing)

### ✅ API Design Rules
- RESTful conventions maintained
- /api/v1/ versioning pattern preserved
- New endpoints for AI Agent status/monitoring only
- No changes to existing invoice endpoints

### ⚠️ Development Guidelines
- **Potential Complexity**: Adding AI Agent as new component increases system complexity
- **Justification**: Required for intelligent error handling, adaptive retry logic, and continuous monitoring that simple cron jobs cannot provide
- **Mitigation**: Modular Agent Skills design, comprehensive logging, health checks

**Gate Status**: ✅ PASS - All constitutional principles satisfied. Complexity increase justified by business requirements for intelligent automation.

## Project Structure

### Documentation (this feature)

```text
specs/001-invoice-automation/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Database schema changes
├── quickstart.md        # Phase 1: AI Agent setup guide
├── contracts/           # Phase 1: API contracts (if needed)
└── tasks.md             # Phase 2: Implementation tasks (created by /sp.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── automation_invoice.py      # EXTEND: add retry_count, last_retry_at, priority
│   │   ├── automation_log.py          # USE: store AI decisions in details field
│   │   └── ai_agent_health_check.py   # NEW: health check model
│   ├── services/
│   │   ├── fbr_client.py              # REUSE: no changes
│   │   ├── validation_service.py      # REUSE: no changes
│   │   ├── fte_worker_service.py      # DEPRECATE: replaced by AI Agent
│   │   └── automation_service.py      # REUSE: Excel parsing
│   ├── workers/
│   │   ├── fte_worker.py              # DEPRECATE: replaced by AI Agent
│   │   └── ai_agent/                  # NEW: AI Agent implementation
│   │       ├── __init__.py
│   │       ├── agent.py               # Main AI Agent orchestrator
│   │       ├── skills/                # Agent Skills (Python modules)
│   │       │   ├── __init__.py
│   │       │   ├── excel_monitor.py   # Detect new uploads
│   │       │   ├── invoice_validator.py  # Validate invoices
│   │       │   ├── fbr_poster.py      # Submit to FBR
│   │       │   ├── error_handler.py   # Classify errors
│   │       │   ├── retry_manager.py   # Retry strategies
│   │       │   └── priority_scheduler.py  # Prioritize processing
│   │       └── config.py              # Agent configuration
│   ├── api/v1/
│   │   └── automation/
│   │       └── agent_status.py        # NEW: AI Agent status endpoint
│   └── schemas/
│       └── agent.py                   # NEW: AI Agent schemas
└── tests/
    └── unit/
        └── workers/
            └── ai_agent/              # NEW: AI Agent tests

ai-agent/                              # NEW: Docker container for AI Agent
├── Dockerfile                         # AI Agent container definition
├── requirements.txt                   # AI Agent dependencies
├── main.py                            # AI Agent entry point
└── config/
    └── ralph_loop.yaml                # Ralph Loop configuration

docker-compose.yml                     # EXTEND: add ai-agent service

frontend/                              # NO CHANGES
└── (existing structure unchanged)
```

**Structure Decision**: Web application with backend + AI agent container. The AI Agent runs as a separate Docker container managed by docker-compose, communicating with the PostgreSQL database and reusing backend services. The existing FTE worker (fte_worker.py, fte_worker_service.py) will be deprecated and replaced by the AI Agent. Frontend remains unchanged as all automation is backend-driven.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New AI Agent component | Intelligent error classification, adaptive retry logic, continuous monitoring (1-min detection, 5-min precision) cannot be achieved with simple cron-based hourly batch processing | Hourly FTE worker insufficient: cannot detect uploads within 1 minute, cannot process at 5-minute precision, lacks intelligent decision-making for error handling and prioritization |
| Docker container for AI Agent | Isolation, independent resource allocation, 24/7 operation, separate from web server lifecycle | Integrating into FastAPI backend would couple agent lifecycle to web server, making restarts and monitoring more complex. Separate container provides better isolation and operational flexibility |
| Agent Skills architecture | Modular, testable components for different automation concerns (monitoring, validation, posting, error handling, retry, prioritization) | Monolithic agent code would be harder to test, maintain, and extend. Skills provide clear separation of concerns and reusability |

---

## Phase 0: Research ✅ COMPLETE

**Deliverable**: `research.md`

**Completed**: 2026-04-10

**Key Decisions Documented**:
1. Docker containerization strategy (multi-stage Alpine build)
2. Scheduling architecture (APScheduler with dual intervals)
3. Database connection management (connection pool with pre-ping)
4. AI Agent architecture (Orchestrator-Skills pattern)
5. Claude API integration (prompt-based decision making with caching)
6. Continuous monitoring pattern (cursor-based polling)
7. Error handling & retry logic (exponential backoff + circuit breaker)
8. Docker Compose configuration (three-service architecture)
9. Modular skills design (base class + registry)
10. Graceful shutdown strategy (signal handling + checkpointing)
11. "Ralph Loop" clarification (not a real tool, use APScheduler)

---

## Phase 1: Design & Contracts ✅ COMPLETE

**Deliverables**: 
- `data-model.md` - Database schema changes
- `quickstart.md` - Setup and deployment guide
- No API contracts needed (agent is background service)

**Completed**: 2026-04-10

**Database Schema Changes**:
1. Extended `automation_invoice` table with 3 fields (retry_count, last_retry_at, priority)
2. Created `ai_agent_health_check` table (18 fields)
3. Reused `automation_log` table for AI decisions (no schema change)
4. Added 4 new indexes for retry tracking and prioritization

**Setup Guide Includes**:
1. Docker Compose configuration for AI Agent service
2. Environment variable setup (Claude API key)
3. Database migration instructions
4. Testing procedures for AI Agent
5. Troubleshooting guide
6. Performance comparison (FTE worker vs AI Agent)

---

## Phase 2: Implementation Tasks

**Status**: NOT STARTED

**Next Command**: `/sp.tasks`

This will generate `tasks.md` with detailed implementation tasks based on this plan.

---

## Summary

**Planning Complete**: ✅

**Artifacts Created**:
1. ✅ plan.md (this file)
2. ✅ research.md (technical decisions)
3. ✅ data-model.md (database schema)
4. ✅ quickstart.md (setup guide)

**Ready for**: Task generation via `/sp.tasks` command

**Estimated Implementation Effort**:
- Database migration: 1 day
- AI Agent core infrastructure: 3-5 days
- Agent Skills implementation: 5-7 days
- Claude API integration: 2-3 days
- Docker setup and deployment: 2-3 days
- Testing and refinement: 3-5 days
- **Total**: 16-24 days (3-4 weeks)

**Critical Path**:
1. Database migration (blocks everything)
2. AI Agent orchestrator skeleton (blocks skills)
3. Skills implementation (can be parallelized)
4. Claude API integration (can be done in parallel with skills)
5. Docker deployment (final integration)

**Risk Areas**:
1. Claude API rate limiting (mitigation: implement rate limiter, use caching)
2. Database connection exhaustion (mitigation: connection pooling with limits)
3. Agent crashes losing in-flight work (mitigation: checkpointing system)
4. FBR API downtime (mitigation: circuit breaker, retry logic)

**Success Criteria**:
- AI Agent detects uploads within 1 minute (95% of time)
- Processes invoices within 5 minutes of scheduled time (90% of time)
- Error classification accuracy >95%
- Retry success rate >70%
- Zero duplicate processing between agent and old FTE worker
- Health checks complete within 30 seconds
- Agent runs continuously for 7+ days without restart

