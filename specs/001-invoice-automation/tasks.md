# Tasks: AI Agent for Invoice Automation

**Input**: Design documents from `/specs/001-invoice-automation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Tests are NOT explicitly requested in the feature specification, so test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Total Tasks**: 103 (T001-T103)
**Updated**: 2026-04-10 - Added missing critical tasks from /sp.analyze remediation

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

This is a web application with:
- Backend: `backend/src/`
- AI Agent: `ai-agent/`
- Frontend: `frontend/src/` (no changes for this feature)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency installation

- [ ] T001 Install AI Agent dependencies using uv in backend/pyproject.toml: anthropic>=0.18.0, apscheduler>=3.10.0, httpx>=0.28.0
- [ ] T002 Create ai-agent directory structure: ai-agent/, ai-agent/config/, ai-agent/logs/
- [ ] T003 Create ai-agent/requirements.txt with dependencies: anthropic, apscheduler, sqlmodel, httpx, psycopg2-binary, python-dotenv
- [ ] T004 Create ai-agent/Dockerfile with multi-stage Alpine build per research.md
- [ ] T005 Update docker-compose.yml to add ai-agent service with health checks and resource limits
- [ ] T006 Add ANTHROPIC_API_KEY to .env file and docker-compose.yml environment variables for AI Agent service

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Extend AutomationInvoice model in backend/src/models/automation_invoice.py with retry_count, last_retry_at, priority fields
- [ ] T008 Create AIAgentHealthCheck model in backend/src/models/ai_agent_health_check.py with 18 fields per data-model.md
- [ ] T009 Update User model in backend/src/models/user.py to add automation_invoices and excel_upload_sessions relationships
- [ ] T010 Create Alembic migration in backend/alembic/versions/ to add retry fields and ai_agent_health_check table
- [ ] T011 Run database migration: uv run alembic upgrade head
- [ ] T012 Verify new indexes exist: idx_retry_tracking, idx_priority_processing, idx_health_check_timestamp, idx_health_check_status
- [ ] T013 Update backend/src/database/session.py to import AIAgentHealthCheck model

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Excel Template Download and Upload (Priority: P1) 🎯 MVP

**Goal**: Enable users to download Excel template, fill with invoice data, and upload for bulk scheduling

**Independent Test**: Login, download template, fill with sample data (10 invoices with scheduled times), upload file, verify system accepts and stores data in database

### Implementation for User Story 1

- [ ] T014 [P] [US1] Verify AutomationInvoice model exists in backend/src/models/automation_invoice.py (already implemented)
- [ ] T015 [P] [US1] Verify ExcelUploadSession model exists in backend/src/models/excel_upload_session.py (already implemented)
- [ ] T016 [P] [US1] Verify AutomationLog model exists in backend/src/models/automation_log.py (already implemented)
- [ ] T017 [US1] Verify Excel template download endpoint exists in backend/src/api/v1/automation.py (already implemented)
- [ ] T018 [US1] Verify Excel upload endpoint exists in backend/src/api/v1/automation.py with validation for structure, duplicates, concurrent uploads, 1000-row limit (already implemented)
- [ ] T019 [US1] Verify automation_service.py exists in backend/src/services/automation_service.py with Excel parsing logic (already implemented)
- [ ] T020 [US1] Test Excel template download via curl or frontend
- [ ] T021 [US1] Test Excel upload with valid data (10 invoices)
- [ ] T022 [US1] Test Excel upload rejection for duplicate invoice numbers
- [ ] T023 [US1] Test Excel upload rejection for missing columns
- [ ] T024 [US1] Test Excel upload rejection for >1000 rows
- [ ] T025 [US1] Test concurrent upload blocking

**Checkpoint**: User Story 1 complete - users can download template and upload bulk invoices

---

## Phase 4: User Story 2 - Autonomous Invoice Processing (Priority: P1)

**Goal**: FTE worker automatically validates and submits invoices at scheduled times (DEPRECATED - will be replaced by AI Agent in US5)

**Independent Test**: Upload Excel with invoices scheduled for current hour, wait for hourly check, verify valid invoices submitted to FBR and database updated

**Note**: This user story represents the OLD FTE worker implementation. It will be deprecated and replaced by the AI Agent (User Story 5). Tasks here are verification only.

### Implementation for User Story 2

- [ ] T026 [US2] Verify FTE worker exists in backend/src/workers/fte_worker.py (already implemented, will be deprecated)
- [ ] T027 [US2] Verify FBRClient exists in backend/src/services/fbr_client.py for FBR submission (already implemented)
- [ ] T028 [US2] Verify ValidationService exists in backend/src/services/validation_service.py (already implemented)
- [ ] T029 [US2] Document FTE worker deprecation plan in backend/src/workers/fte_worker.py with comment: "DEPRECATED: This worker will be replaced by AI Agent. See ai-agent/ directory."

**Checkpoint**: User Story 2 verified - FTE worker exists but marked for deprecation

---

## Phase 5: User Story 3 - Automation Dashboard and Monitoring (Priority: P2)

**Goal**: Dashboard showing real-time statistics, invoice list with filters, and Excel export

**Independent Test**: Upload and process invoices, access dashboard, verify statistics accurate, filters work, Excel export generates file from database

### Implementation for User Story 3

- [ ] T030 [P] [US3] Verify dashboard statistics endpoint exists in backend/src/api/v1/automation.py: GET /api/v1/automation/dashboard/stats (already implemented)
- [ ] T031 [P] [US3] Verify invoice list endpoint exists in backend/src/api/v1/automation.py: GET /api/v1/automation/dashboard/invoices with pagination and filters (already implemented)
- [ ] T032 [P] [US3] Verify invoice detail endpoint exists in backend/src/api/v1/automation.py: GET /api/v1/automation/invoice/{id} (already implemented)
- [ ] T033 [P] [US3] Verify manual retry endpoint exists in backend/src/api/v1/automation.py: POST /api/v1/automation/invoice/{id}/retry (already implemented)
- [ ] T034 [US3] Verify Excel export endpoint exists in backend/src/api/v1/automation.py: GET /api/v1/automation/dashboard/download/{session_id} (already implemented)
- [ ] T035 [US3] Test dashboard statistics endpoint returns correct counts
- [ ] T036 [US3] Test invoice list filtering by status (pending, submitted, failed)
- [ ] T037 [US3] Test invoice list filtering by date range
- [ ] T038 [US3] Test invoice detail view shows complete information
- [ ] T039 [US3] Test manual retry for failed invoice
- [ ] T040 [US3] Test Excel export generates file from database with status/reason columns

**Checkpoint**: User Story 3 complete - dashboard provides full visibility into automation

---

## Phase 6: User Story 4 - Integration with Existing Manual Invoice System (Priority: P3)

**Goal**: Ensure automation coexists with manual invoice workflow without interference

**Independent Test**: Create manual invoices via existing system, upload automated invoices, verify both work independently

### Implementation for User Story 4

- [ ] T041 [US4] Verify automation data uses separate tables (automation_invoice, not main invoice table)
- [ ] T042 [US4] Verify user_id isolation enforced in all automation queries
- [ ] T043 [US4] Test manual invoice creation still works after automation feature deployed
- [ ] T044 [US4] Test automated invoices don't appear in manual invoice list
- [ ] T045 [US4] Test manual invoices don't appear in automation dashboard
- [ ] T046 [US4] Verify no shared state between manual and automated workflows

**Checkpoint**: User Story 4 complete - automation and manual workflows coexist independently

---

## Phase 7: User Story 5 - AI Agent for Continuous Monitoring and Intelligent Processing (Priority: P1)

**Goal**: AI Agent replaces FTE worker with continuous monitoring, 5-minute precision, intelligent error handling, adaptive retry, and prioritization

**Independent Test**: Upload Excel with various scheduled times, monitor AI Agent logs, verify 1-minute detection, 5-minute processing precision, intelligent retry for failures, prioritization working, hourly health checks

### Implementation for User Story 5

#### AI Agent Core Infrastructure

- [ ] T047 [P] [US5] Create ai-agent/main.py as entry point with signal handling for graceful shutdown
- [ ] T048 [P] [US5] Create ai-agent/config.py with configuration management (DATABASE_URL, ANTHROPIC_API_KEY, FBR URLs, intervals) and business rule configuration (priority weights, thresholds)
- [ ] T049 [US5] Create ai-agent/agent.py as main orchestrator with APScheduler BackgroundScheduler setup
- [ ] T050 [US5] Implement database connection pool in ai-agent/database.py with pre-ping and connection recycling per research.md
- [ ] T051 [US5] Implement Claude API client wrapper in ai-agent/claude_client.py with rate limiting and prompt caching

#### Agent Skills Implementation

- [ ] T052 [P] [US5] Create base skill class in ai-agent/skills/__init__.py with skill registry pattern and interface: execute(context), validate_input(data), handle_error(exception)
- [ ] T053 [P] [US5] Implement ExcelMonitorSkill in ai-agent/skills/excel_monitor.py for detecting new uploads within 1 minute using cursor-based polling
- [ ] T054 [P] [US5] Implement InvoiceValidatorSkill in ai-agent/skills/invoice_validator.py wrapping existing ValidationService
- [ ] T055 [P] [US5] Implement FBRPosterSkill in ai-agent/skills/fbr_poster.py wrapping existing FBRClient
- [ ] T056 [P] [US5] Implement ErrorHandlerSkill in ai-agent/skills/error_handler.py with Claude API integration for error classification (transient vs permanent)
- [ ] T057 [P] [US5] Implement RetryManagerSkill in ai-agent/skills/retry_manager.py with exponential backoff (base_delay * 2^retry_count + jitter), and circuit breaker per research.md
- [ ] T058 [P] [US5] Implement PrioritySchedulerSkill in ai-agent/skills/priority_scheduler.py for business rule-based prioritization (scheduled time, invoice value, retry count)

#### Scheduling and Monitoring

- [ ] T059 [US5] Configure APScheduler in ai-agent/agent.py with dual intervals: 5-minute invoice processing job (IntervalTrigger) and hourly health check job (CronTrigger at minute 0)
- [ ] T060 [US5] Implement 5-minute processing job in ai-agent/agent.py that queries pending invoices, applies prioritization, validates, posts to FBR, handles errors, logs decisions
- [ ] T061 [US5] Implement hourly health check job in ai-agent/agent.py that counts pending/failed invoices, tests FBR API, checks database, detects anomalies, stores results in ai_agent_health_check table
- [ ] T062 [US5] Implement anomaly detection in ai-agent/agent.py per FR-030: 20% failure rate in 1-hour window, 3 consecutive FBR failures, 500 invoice backlog, 5s database latency
- [ ] T063 [US5] Implement decision logging in ai-agent/agent.py that writes to automation_log table with standardized schema: decision_type, input_context, ai_decision, rationale, model_used, timestamp
- [ ] T064 [US5] Implement heartbeat file mechanism in ai-agent/agent.py for Docker health checks (/tmp/agent_heartbeat.txt updated every 5 minutes)

#### API Endpoints for AI Agent Status

- [ ] T065 [P] [US5] Create agent status schema in backend/src/schemas/agent.py with AIAgentStatus, AIAgentDecision models
- [ ] T066 [US5] Create agent status endpoint in backend/src/api/v1/automation/agent_status.py: GET /api/v1/automation/agent/health returning latest health check
- [ ] T067 [US5] Create agent decisions endpoint in backend/src/api/v1/automation/agent_status.py: GET /api/v1/automation/agent/decisions with pagination

#### Docker and Deployment

- [ ] T068 [US5] Verify ai-agent/Dockerfile created in Phase 1 (T004)
- [ ] T069 [US5] Verify docker-compose.yml updated in Phase 1 (T005)
- [ ] T070 [US5] Build AI Agent Docker image: docker-compose build ai-agent
- [ ] T071 [US5] Start all services: docker-compose up -d
- [ ] T072 [US5] Verify AI Agent container running: docker-compose ps
- [ ] T073 [US5] Verify AI Agent logs show scheduler started: docker-compose logs -f ai-agent

#### Testing and Validation

- [ ] T074 [US5] Test AI Agent detects new Excel upload within 1 minute (upload file, check logs for detection event)
- [ ] T075 [US5] Test AI Agent processes invoice within 5 minutes of scheduled time (set scheduled_time to current_time + 5min, verify processing)
- [ ] T076 [US5] Test AI Agent classifies transient error correctly (simulate network timeout, verify classification in logs)
- [ ] T077 [US5] Test AI Agent classifies permanent error correctly (upload invalid invoice, verify no retry scheduled)
- [ ] T078 [US5] Test AI Agent applies exponential backoff for retries (cause transient failure, verify retry delays: 5s, 10s, 20s, 40s)
- [ ] T079 [US5] Test AI Agent prioritizes high-value invoices (upload mix of high/low value, verify processing order)
- [ ] T080 [US5] Test AI Agent handles FBR rate limiting (simulate rate limit error, verify throttling and rescheduling)
- [ ] T081 [US5] Test AI Agent hourly health check runs and stores results (wait for top of hour, verify ai_agent_health_check table has new entry)
- [ ] T082 [US5] Test AI Agent detects anomalies (cause >20% failure rate in 1-hour window, verify anomaly logged)
- [ ] T083 [US5] Test AI Agent status endpoint returns current status: GET /api/v1/automation/agent/health
- [ ] T084 [US5] Test AI Agent decisions endpoint returns decision log: GET /api/v1/automation/agent/decisions
- [ ] T085 [US5] Test AI Agent graceful shutdown (docker-compose stop ai-agent, verify checkpointing and clean exit)
- [ ] T086 [US5] Test AI Agent restart recovery (stop and start container, verify agent resumes processing)

#### FTE Worker Deprecation

- [ ] T087 [US5] Stop old FTE worker if running: systemctl stop fte-worker (or kill process)
- [ ] T088 [US5] Disable old FTE worker from startup: systemctl disable fte-worker
- [ ] T089 [US5] Add deprecation notice to backend/src/workers/fte_worker.py: "DEPRECATED: Replaced by AI Agent in ai-agent/ directory. Do not use."

**Checkpoint**: User Story 5 complete - AI Agent fully operational, replacing FTE worker with superior capabilities

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T090 [P] Add comprehensive logging across all AI Agent skills with structured log format (timestamp, skill, action, result)
- [ ] T091 [P] Add error handling for Claude API failures (rate limits, timeouts, invalid responses) with fallback to rule-based logic
- [ ] T092 [P] Add monitoring metrics for AI Agent (processing latency, decision accuracy, retry success rate)
- [ ] T093 [P] Add environment variable validation on AI Agent startup (check DATABASE_URL, ANTHROPIC_API_KEY, FBR URLs)
- [ ] T094 Run full end-to-end test per quickstart.md: download template, upload 50 invoices, verify AI Agent processes all within 10 minutes
- [ ] T095 Verify SC-001: Users can download template and upload 100 invoices in under 3 minutes
- [ ] T096 Verify SC-011: AI Agent detects uploads within 1 minute (95% of time) - test with 20 uploads, measure detection latency
- [ ] T097 Verify SC-012: AI Agent processes invoices within 5 minutes of scheduled time (90% of time) - test with 20 invoices
- [ ] T098 Verify SC-013: AI Agent error classification accuracy ≥95% - manual validation of 100 random classifications
- [ ] T099 Verify SC-016: AI Agent anomaly detection accuracy ≥90% - test with 10 known anomaly scenarios
- [ ] T100 Verify SC-017: Zero duplicate processing between AI Agent and FTE worker
- [ ] T101 Performance test: upload 1000 invoices, verify AI Agent handles load without memory issues
- [ ] T102 Security audit: verify user_id isolation in all queries, no SQL injection vulnerabilities, API key not logged
- [ ] T103 Documentation review: ensure all code has docstrings, README updated, architecture diagrams current

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - mostly verification (already implemented)
- **User Story 2 (Phase 4)**: Depends on Foundational - verification only (FTE worker deprecated)
- **User Story 3 (Phase 5)**: Depends on Foundational - mostly verification (already implemented)
- **User Story 4 (Phase 6)**: Depends on Foundational - verification and testing
- **User Story 5 (Phase 7)**: Depends on Foundational - NEW IMPLEMENTATION (AI Agent)
- **Polish (Phase 8)**: Depends on User Story 5 completion

### User Story Dependencies

- **User Story 1 (P1)**: Independent - can start after Foundational
- **User Story 2 (P1)**: Independent - verification only, will be deprecated
- **User Story 3 (P2)**: Independent - can start after Foundational
- **User Story 4 (P3)**: Independent - can start after Foundational
- **User Story 5 (P1)**: Depends on US1, US2, US3 being verified - replaces US2 FTE worker

### Within Each User Story

- **US1**: Verification tasks can run in parallel (T013-T018), then testing tasks sequentially (T019-T024)
- **US2**: All verification tasks can run in parallel (T025-T028)
- **US3**: Verification tasks in parallel (T029-T033), then testing tasks sequentially (T034-T039)
- **US4**: All tasks sequential (T040-T045)
- **US5**: 
  - Core infrastructure tasks in parallel (T046-T050)
  - Skills implementation in parallel (T051-T057)
  - Scheduling tasks sequential (T058-T062)
  - API endpoints in parallel (T063-T065)
  - Docker tasks sequential (T066-T071)
  - Testing tasks sequential (T072-T084)
  - Deprecation tasks sequential (T085-T088)

### Parallel Opportunities

- All Setup tasks (T001-T005) can run in parallel
- All Foundational model tasks (T006-T008) can run in parallel, then migration (T009-T012) sequential
- US5 core infrastructure (T046-T050) can run in parallel
- US5 skills (T051-T057) can run in parallel
- US5 API endpoints (T063-T065) can run in parallel
- Polish tasks (T089-T093) can run in parallel

---

## Parallel Example: User Story 5 - AI Agent Skills

```bash
# Launch all skill implementations together (different files, no dependencies):
Task: "Implement ExcelMonitorSkill in ai-agent/skills/excel_monitor.py"
Task: "Implement InvoiceValidatorSkill in ai-agent/skills/invoice_validator.py"
Task: "Implement FBRPosterSkill in ai-agent/skills/fbr_poster.py"
Task: "Implement ErrorHandlerSkill in ai-agent/skills/error_handler.py"
Task: "Implement RetryManagerSkill in ai-agent/skills/retry_manager.py"
Task: "Implement PrioritySchedulerSkill in ai-agent/skills/priority_scheduler.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 3, 5 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Excel upload - mostly verification)
4. Complete Phase 4: User Story 2 (FTE worker - verification only)
5. Complete Phase 5: User Story 3 (Dashboard - mostly verification)
6. Complete Phase 7: User Story 5 (AI Agent - NEW IMPLEMENTATION)
7. **STOP and VALIDATE**: Test end-to-end with AI Agent
8. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Verify User Stories 1-3 → Existing automation working
3. Implement User Story 5 → AI Agent operational
4. Test User Story 4 → Integration verified
5. Polish → Production ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: Verify US1, US2, US3 (existing features)
   - Developer B: Implement US5 core infrastructure (T046-T050)
   - Developer C: Implement US5 skills (T051-T057)
3. Integrate and test US5 together
4. Developer A: Test US4 integration
5. All: Polish and production readiness

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Stories 1-3 are mostly verification (already implemented in previous work)
- User Story 5 (AI Agent) is the primary NEW implementation
- User Story 2 (FTE worker) will be deprecated by User Story 5
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Use uv package manager for all Python dependencies (not pip)
- All database operations use SQLModel with connection pooling
- All AI decisions logged with rationale using standardized schema (decision_type, input_context, ai_decision, rationale, model_used, timestamp)
- Docker health checks ensure AI Agent stays operational 24/7
- Business rules for prioritization configurable in ai-agent/config.py without code changes
- Anomaly detection thresholds: 20% failure rate in 1-hour window, 3 consecutive FBR failures, 500 invoice backlog, 5s database latency
- Exponential backoff formula: base_delay * (2 ^ retry_count) + random(0, 60) seconds
- Immediate retry = 5 seconds for transient errors
