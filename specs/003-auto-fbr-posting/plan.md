# Implementation Plan: Auto FBR Posting with Time-Based Controls

**Branch**: `003-auto-fbr-posting` | **Date**: 2026-05-01 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/003-auto-fbr-posting/spec.md`

## Summary

Implement automatic FBR posting for validated invoices with user-configurable time windows and manual override capabilities. Users can enable auto-posting in their profile with start/end times (supporting midnight-spanning windows), and the AI agent will automatically post invoices to FBR during active hours. The system enforces daily limits, handles network failures safely, posts invoices sequentially, and provides emergency pause controls. Users retain the ability to manually post individual invoices at any time regardless of auto-posting settings.

**Technical Approach**: Extend existing User model with auto-posting configuration fields, add new invoice statuses for FBR posting lifecycle, create new AI agent job for FBR posting that runs every 5 minutes, implement backend API endpoints for configuration and manual posting, and build frontend UI components in profile and invoice history pages.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript/Node.js 20+ (frontend)  
**Primary Dependencies**: FastAPI, SQLModel, APScheduler (backend), Next.js 16+, React 19 (frontend)  
**Package Manager**: uv (Python - Rust-based, extremely fast), npm/pnpm (frontend)  
**Storage**: Neon PostgreSQL (main database for invoices), separate automation database (for automation_invoices)  
**Testing**: pytest (backend), Jest/React Testing Library (frontend)  
**Target Platform**: Linux server (backend/agent), Web browsers (frontend)  
**Project Type**: Web application (backend + frontend + AI agent)  
**Performance Goals**: 
- Auto-posting check cycle completes within 30 seconds for 100 concurrent users
- Manual posting responds within 10 seconds
- Profile settings save within 2 seconds
- UI updates within 30 seconds of status change

**Constraints**: 
- Sequential invoice posting (one at a time per user)
- FBR API rate limits (10 invoices per user per 5-minute cycle)
- Network failure handling without duplicates (mark as failed, require manual verification)
- Midnight-spanning time windows supported
- Daily limit continuity for midnight-spanning windows

**Scale/Scope**: 
- Support 1000 concurrent users with auto-posting enabled
- Handle 100,000+ invoices per day across all users
- 5-minute agent cycle interval
- 3 retry attempts with exponential backoff

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Compliance-First Development
- **Status**: PASS
- **Verification**: All FBR posting logic uses existing FBRClient which follows FBR technical specifications. No new FBR API interactions introduced, only orchestration of existing validated posting logic.

### ✅ Security by Design
- **Status**: PASS
- **Verification**: 
  - JWT authentication required for all profile and posting endpoints
  - Row-level isolation enforced (users can only configure/post their own invoices)
  - FBR credentials validated before allowing Production posting
  - Re-authentication required when switching Sandbox → Production
  - All configuration changes logged for audit trail

### ✅ Spec-Driven Implementation
- **Status**: PASS
- **Verification**: Uses existing FBRClient and invoice models derived from FBR specifications. No modifications to FBR payload structure or validation logic.

### ✅ Data Integrity and Auditability
- **Status**: PASS
- **Verification**: 
  - All posting attempts logged with timestamp, user, invoice, result
  - Invoice status transitions tracked (TRANSFERRED → FBR_POSTING → FBR_POSTED/FBR_FAILED)
  - FBR responses stored unmodified
  - Auto-posting configuration changes logged

### ✅ Environment Isolation
- **Status**: PASS
- **Verification**: 
  - User selects environment (Sandbox/Production) in profile settings
  - Agent posts to user's configured environment only
  - No cross-environment contamination possible
  - Separate FBR tokens for Sandbox and Production

### ✅ Architectural Constraints
- **Status**: PASS
- **Verification**: 
  - Backend: FastAPI only (new endpoints in existing structure)
  - Frontend: Next.js 16+ App Router only (new components in existing pages)
  - ORM: SQLModel only (extend existing User and Invoice models)
  - Database: Neon PostgreSQL only (add columns to existing tables)
  - Authentication: Better Auth only (use existing JWT middleware)
  - No business logic in frontend (all posting logic in backend/agent)

### ✅ Data Rules
- **Status**: PASS
- **Verification**: 
  - Invoice status transitions tracked (no deletion)
  - FBR responses stored unmodified
  - All posting attempts logged with structured data
  - Daily counters reset at midnight PKT

### ✅ API Design Rules
- **Status**: PASS
- **Verification**: 
  - RESTful conventions followed
  - Endpoints versioned under /api/v1/
  - Schema-based contracts (Pydantic models)
  - Error handling preserves FBR response payloads

### ✅ Environment Workflow Rules
- **Status**: PASS
- **Verification**: 
  - Users explicitly select environment per configuration
  - Production posting requires credential validation
  - Clear distinction between Sandbox and Production flows

### ✅ Non-Functional Standards
- **Status**: PASS
- **Verification**: 
  - Manual posting endpoint responds < 10 seconds (target from spec)
  - Profile settings save < 2 seconds (target from spec)
  - Agent handles concurrent users without conflicts (per-user isolation)

### ✅ Development Guidelines
- **Status**: PASS
- **Verification**: 
  - Smallest viable diff (extend existing models, add new endpoints)
  - No refactoring of unrelated code
  - All changes testable and traceable

## Project Structure

### Documentation (this feature)

```text
specs/003-auto-fbr-posting/
├── plan.md              # This file
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output (to be generated)
├── data-model.md        # Phase 1 output (to be generated)
├── quickstart.md        # Phase 1 output (to be generated)
├── contracts/           # Phase 1 output (to be generated)
│   ├── auto-posting-config-api.yaml
│   ├── manual-posting-api.yaml
│   └── posting-status-api.yaml
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── user.py                    # EXTEND: Add auto-posting config fields
│   │   └── invoice.py                 # EXTEND: Add FBR posting statuses
│   ├── services/
│   │   ├── fbr_client.py              # REUSE: Existing FBR posting logic
│   │   └── auto_posting_service.py    # NEW: Auto-posting orchestration
│   ├── api/v1/
│   │   ├── user_profile.py            # EXTEND: Add auto-posting config endpoints
│   │   └── invoices.py                # EXTEND: Add manual posting endpoint
│   └── schemas/
│       └── auto_posting.py            # NEW: Pydantic schemas for auto-posting
└── tests/
    ├── test_auto_posting_service.py   # NEW: Service tests
    └── test_auto_posting_api.py       # NEW: API endpoint tests

ai-agent/
├── agent.py                           # EXTEND: Add FBR posting job
├── skills/
│   └── fbr_poster.py                  # NEW: FBR posting skill
└── config.py                          # EXTEND: Add auto-posting config

frontend/
├── src/
│   ├── app/(protected)/
│   │   ├── profile/
│   │   │   └── page.tsx               # EXTEND: Add auto-posting config section
│   │   └── invoices/history/
│   │       └── page.tsx               # EXTEND: Add auto-posting status & manual post button
│   ├── components/
│   │   ├── profile/
│   │   │   └── AutoPostingSettings.tsx  # NEW: Auto-posting config component
│   │   └── invoices/
│   │       ├── AutoPostingStatus.tsx    # NEW: Status indicator component
│   │       └── ManualPostButton.tsx     # NEW: Manual post button component
│   └── services/
│       └── autoPostingApi.ts          # NEW: API client for auto-posting
└── tests/
    └── components/
        └── AutoPostingSettings.test.tsx  # NEW: Component tests
```

**Structure Decision**: Web application structure (Option 2) selected. The project already follows this pattern with separate backend/ (FastAPI), frontend/ (Next.js), and ai-agent/ (Python scheduler) directories. This feature extends existing files and adds new components within the established structure without creating new top-level directories.

## Complexity Tracking

> No constitution violations requiring justification. All gates passed.

## Phase 0: Research & Technical Decisions

### Research Areas

1. **Time Window Logic with Midnight Spanning**
   - Decision: Support time windows that cross midnight (e.g., 22:00-02:00)
   - Rationale: Enables night-shift operations and international business hours
   - Implementation: Compare current time against start/end with special logic for spans
   - Alternatives considered: Same-day only (rejected - too restrictive), 24-hour window (rejected - doesn't provide time control)

2. **Daily Limit Reset Behavior**
   - Decision: For midnight-spanning windows, continue using previous day's limit until window ends
   - Rationale: Prevents mid-window limit resets that would confuse users
   - Implementation: Track window start date, use that date's limit until window closes
   - Alternatives considered: Reset at midnight (rejected - disrupts active posting), split proportionally (rejected - too complex)

3. **Network Failure Handling**
   - Decision: Mark as failed and require manual verification before reposting
   - Rationale: Prevents duplicate invoices in FBR system when network fails after FBR acceptance
   - Implementation: Timeout detection, mark as FBR_FAILED with specific error code
   - Alternatives considered: Retry posting (rejected - risk of duplicates), idempotency keys (rejected - FBR API doesn't support), query FBR for existence (rejected - no reliable query API)

4. **Invoice Posting Concurrency**
   - Decision: Sequential posting (one invoice at a time per user)
   - Rationale: Simpler error handling, respects FBR rate limits naturally, avoids race conditions
   - Implementation: Process invoices in order, wait for response before next
   - Alternatives considered: Concurrent posting (rejected - complex error handling), hybrid batching (rejected - premature optimization)

5. **Emergency Pause Behavior**
   - Decision: Disable auto-posting entirely, require manual re-enable
   - Rationale: Safest for emergency situations, ensures user has resolved issue before resuming
   - Implementation: Set auto_posting_enabled = false, require explicit profile update
   - Alternatives considered: Temporary pause (rejected - user might forget to resume), pause until end of day (rejected - arbitrary timing)

6. **Database Schema Changes**
   - Decision: Add columns to existing User table, extend Invoice status enum
   - Rationale: Minimal schema changes, leverages existing infrastructure
   - Implementation: Alembic migration to add columns with defaults
   - Alternatives considered: New auto_posting_config table (rejected - overkill for 1:1 relationship), JSON column (rejected - harder to query)

7. **Agent Job Scheduling**
   - Decision: Add new job to existing APScheduler instance in ai-agent/agent.py
   - Rationale: Reuses existing infrastructure, no new processes needed
   - Implementation: New _post_to_fbr_job() method, 5-minute interval trigger
   - Alternatives considered: Separate agent process (rejected - unnecessary complexity), cron job (rejected - less flexible)

8. **Frontend State Management**
   - Decision: Use React hooks with API polling for status updates
   - Rationale: Simple, works with existing architecture, no WebSocket infrastructure needed
   - Implementation: useEffect with 30-second interval, fetch status from API
   - Alternatives considered: WebSocket (rejected - overkill for 30s updates), Server-Sent Events (rejected - adds complexity)

### Technology Stack Confirmation

- **Backend**: FastAPI 0.104+ with SQLModel 0.0.14+
- **Database**: Neon PostgreSQL 15+ (existing)
- **ORM**: SQLModel (existing)
- **Agent Scheduler**: APScheduler 3.10+ (existing)
- **Package Manager**: uv (Python - 10-100x faster than pip)
- **Frontend**: Next.js 16+ with React 19, TypeScript 5+
- **API Client**: httpx (backend), fetch API (frontend)
- **Testing**: pytest (backend), Jest + React Testing Library (frontend)

### Performance Considerations

1. **Agent Cycle Performance**
   - Target: Complete 5-minute cycle for 100 users in < 30 seconds
   - Strategy: Per-user limit of 10 invoices per cycle, sequential processing
   - Monitoring: Log cycle duration, alert if > 30 seconds

2. **Database Query Optimization**
   - Index on (user_id, status, scheduled_date, scheduled_time) for invoice queries
   - Index on (user_id, auto_posting_enabled) for user filtering
   - Use connection pooling (existing)

3. **API Response Times**
   - Manual posting: < 10 seconds (includes FBR API call)
   - Profile settings: < 2 seconds (database update only)
   - Status queries: < 1 second (simple SELECT)

## Phase 1: Data Model & API Contracts

### Data Model Changes

See [data-model.md](./data-model.md) for complete entity definitions.

**Summary of Changes**:

1. **User Model Extensions** (backend/src/models/user.py):
   - `auto_posting_enabled: bool` (default: False)
   - `auto_posting_start_time: time` (default: 09:00)
   - `auto_posting_end_time: time` (default: 18:00)
   - `auto_posting_environment: str` (default: "SANDBOX")
   - `auto_posting_daily_limit: int` (default: 100)
   - `auto_posting_paused_until: datetime` (nullable)

2. **Invoice Model Extensions** (backend/src/models/invoice.py):
   - Add to InvoiceStatus enum: `FBR_POSTING`, `FBR_POSTED`, `FBR_FAILED`
   - `fbr_posted_at: datetime` (nullable)
   - `fbr_posting_error: str` (nullable)
   - `fbr_retry_count: int` (default: 0)

3. **New Entity: DailyPostingCounter** (backend/src/models/daily_posting_counter.py):
   - `id: UUID` (primary key)
   - `user_id: UUID` (foreign key to users)
   - `date: date` (PKT timezone)
   - `posted_count: int`
   - `window_start_date: date` (for midnight-spanning windows)
   - Unique constraint on (user_id, date)

4. **New Entity: PostingLog** (backend/src/models/posting_log.py):
   - `id: UUID` (primary key)
   - `user_id: UUID` (foreign key to users)
   - `invoice_id: UUID` (foreign key to invoices)
   - `action: str` (auto/manual)
   - `result: str` (success/failure)
   - `environment: str` (SANDBOX/PRODUCTION)
   - `error_details: JSON` (nullable)
   - `agent_cycle_id: str` (nullable)
   - `created_at: datetime`

### API Contracts

See [contracts/](./contracts/) directory for complete OpenAPI specifications.

**New Endpoints**:

1. **GET /api/v1/profile/auto-posting** - Get auto-posting configuration
2. **PUT /api/v1/profile/auto-posting** - Update auto-posting configuration
3. **POST /api/v1/profile/auto-posting/emergency-pause** - Emergency pause auto-posting
4. **POST /api/v1/invoices/{invoice_id}/post-to-fbr** - Manual post to FBR
5. **GET /api/v1/invoices/posting-status** - Get posting status and statistics

**Extended Endpoints**:

1. **GET /api/v1/profile** - Include auto-posting config in response
2. **GET /api/v1/invoices/history** - Include FBR posting statuses

### Migration Strategy

1. **Database Migration** (Alembic):
   - Add columns to users table with safe defaults
   - Add new statuses to invoice status enum
   - Create daily_posting_counter table
   - Create posting_log table
   - Add indexes for performance

2. **Backward Compatibility**:
   - All new columns have defaults (no breaking changes)
   - Existing invoices remain in current statuses
   - Auto-posting disabled by default for all users

3. **Rollback Plan**:
   - Alembic downgrade removes new columns
   - Agent job can be disabled via config
   - Frontend changes are additive (no breaking changes)

## Phase 2: Implementation Roadmap

*Note: Detailed tasks will be generated by `/sp.tasks` command. This section provides high-level implementation order.*

### Stage 1: Database & Models (Foundation)
1. Create Alembic migration for schema changes
2. Extend User model with auto-posting fields
3. Extend Invoice model with FBR posting statuses
4. Create DailyPostingCounter model
5. Create PostingLog model
6. Run migration and verify schema

### Stage 2: Backend Services (Core Logic)
1. Create AutoPostingService with time window logic
2. Implement daily limit tracking and reset
3. Implement sequential posting logic
4. Implement network failure handling
5. Add posting log creation
6. Write service unit tests

### Stage 3: Backend API (Endpoints)
1. Add auto-posting config endpoints to user_profile.py
2. Add manual posting endpoint to invoices.py
3. Add posting status endpoint to invoices.py
4. Implement request validation (Pydantic schemas)
5. Add authentication and authorization checks
6. Write API integration tests

### Stage 4: AI Agent (Automation)
1. Create FBRPosterSkill in ai-agent/skills/
2. Add _post_to_fbr_job() to agent.py
3. Implement user filtering (auto_posting_enabled)
4. Implement time window checking
5. Implement daily limit enforcement
6. Add error handling and retry logic
7. Add logging and monitoring
8. Write agent tests

### Stage 5: Frontend Components (UI)
1. Create AutoPostingSettings component for profile page
2. Create AutoPostingStatus component for invoice history
3. Create ManualPostButton component for invoice history
4. Implement API client (autoPostingApi.ts)
5. Add form validation and error handling
6. Add loading states and feedback
7. Write component tests

### Stage 6: Integration & Testing (E2E)
1. Test complete auto-posting flow (enable → agent posts → status updates)
2. Test manual posting override
3. Test time window enforcement (including midnight spans)
4. Test daily limit enforcement
5. Test emergency pause
6. Test network failure handling
7. Test concurrent user scenarios
8. Performance testing (100 users, 1000 invoices)

### Stage 7: Documentation & Deployment
1. Update API documentation
2. Create user guide for auto-posting feature
3. Create admin guide for monitoring
4. Update deployment scripts
5. Create runbook for troubleshooting
6. Deploy to staging environment
7. User acceptance testing
8. Deploy to production

## Risk Assessment

### High Risk
1. **Network Failure Duplicates**: If FBR accepts invoice but network fails before confirmation
   - Mitigation: Mark as failed, require manual verification (clarified in spec)
   - Monitoring: Alert on high failure rates

2. **Midnight-Spanning Window Edge Cases**: Daily limit reset during active window
   - Mitigation: Continue using previous day's limit until window ends (clarified in spec)
   - Testing: Comprehensive test cases for midnight transitions

### Medium Risk
1. **Agent Performance Degradation**: Cycle takes > 30 seconds with many users
   - Mitigation: Per-user limit of 10 invoices per cycle, monitoring and alerts
   - Scaling: Can increase agent instances if needed

2. **FBR API Rate Limiting**: Exceeding FBR rate limits
   - Mitigation: Sequential posting, 10 invoices per user per 5 minutes
   - Monitoring: Track FBR API response codes

### Low Risk
1. **Database Migration Issues**: Schema changes fail
   - Mitigation: Test migration on staging first, have rollback plan
   - Backup: Database backup before migration

2. **Frontend State Sync**: UI shows stale status
   - Mitigation: 30-second polling interval, manual refresh button
   - Enhancement: Can add WebSocket later if needed

## Success Metrics

1. **Functional Metrics**:
   - 95% of invoices posted successfully on first attempt
   - Zero invoices posted outside configured time windows
   - 100% accuracy on daily limit enforcement
   - Manual posting works 100% of time regardless of auto-posting state

2. **Performance Metrics**:
   - Agent cycle completes in < 30 seconds for 100 users
   - Manual posting responds in < 10 seconds
   - Profile settings save in < 2 seconds
   - UI updates within 30 seconds of status change

3. **Reliability Metrics**:
   - Zero duplicate invoices in FBR system
   - 99.9% agent uptime
   - Retry logic succeeds within 3 attempts for 90% of retryable errors

4. **User Experience Metrics**:
   - Users can configure auto-posting in < 2 minutes
   - Emergency pause takes effect within 5 minutes
   - Clear error messages for all failure scenarios

## Next Steps

1. Run `/sp.tasks` to generate detailed task breakdown
2. Review and approve implementation plan
3. Create feature branch and begin Stage 1 (Database & Models)
4. Set up monitoring and alerting for agent performance
5. Schedule user acceptance testing after Stage 6

---

**Plan Status**: ✅ Complete - Ready for task generation  
**Last Updated**: 2026-05-01  
**Approved By**: Pending review
