# Implementation Tasks: Automation Database Separation

**Feature ID**: 1-automation-db-separation  
**Created**: 2026-04-24  
**Status**: Ready for Implementation  
**Total Estimated Effort**: 17-24 days (3-4 weeks)  
**Total Tasks**: 113

---

## Overview

This document breaks down the automation database separation feature into executable tasks organized by user story. Each phase represents a complete, independently testable increment of functionality.

**User Stories**:
1. **US1**: Bulk Invoice Upload and Transfer - Users can upload invoices that are automatically transferred daily
2. **US2**: Failed Transfer Recovery - Admins can recover from transfer failures
3. **US3**: Data Cleanup - System automatically cleans up old automation data

---

## Task Format

Each task follows this format:
```
- [ ] [TaskID] [P?] [Story?] Description with file path
```

- **TaskID**: Sequential number (T001, T002, etc.)
- **[P]**: Parallelizable task (can be done concurrently with other [P] tasks)
- **[Story]**: User story label ([US1], [US2], [US3])
- **Description**: Clear action with exact file path

---

## Phase 1: Setup & Infrastructure (2-3 days)

**Goal**: Set up multi-database architecture and development environment

**Tasks**:

- [ ] T001 Create new Neon database project for automation database
- [x] T002 Add AUTOMATION_DATABASE_URL to backend/.env and backend/.env.example
- [x] T003 Add transfer and cleanup configuration to backend/.env (TRANSFER_SCHEDULE_HOUR, CLEANUP_RETENTION_DAYS, etc.)
- [x] T004 Create second SQLAlchemy engine in backend/src/database/session.py for automation database
- [x] T005 Create get_automation_db() dependency function in backend/src/database/session.py
- [x] T006 Create alembic_automation.ini configuration file in backend/
- [x] T007 Create backend/alembic/versions/automation/ directory for automation DB migrations
- [x] T008 Update backend/alembic/env.py to support multi-database migrations
- [ ] T009 Test database connections for both main and automation databases
- [x] T010 Document multi-database setup in backend/README.md

**Acceptance Criteria**:
- Both databases are accessible from backend
- get_db() returns main database session
- get_automation_db() returns automation database session
- Alembic can run migrations on both databases independently

---

## Phase 2: Foundational - Database Schema (3-4 days)

**Goal**: Create automation database schema and migrate existing data

**Tasks**:

- [x] T011 Create initial Alembic migration for automation database schema in backend/alembic/versions/automation/
- [x] T012 [P] Create TransferLog model in backend/src/models/transfer_log.py
- [x] T013 [P] Add transferred_at and transfer_error fields to AutomationInvoice model in backend/src/models/automation_invoice.py
- [x] T014 [P] Add TRANSFERRED and TRANSFER_FAILED status to AutomationInvoiceStatus enum in backend/src/models/automation_invoice.py
- [x] T015 [P] Add source, transferred_at, and automation_invoice_id fields to Invoice model in backend/src/models/invoice.py
- [x] T016 Create Alembic migration for new Invoice fields in backend/alembic/versions/
- [x] T017 Run migrations on automation database (alembic -c alembic_automation.ini upgrade head)
- [x] T018 Run migrations on main database (alembic upgrade head)
- [x] T019 Create data migration script in backend/scripts/migrate_automation_data.py to copy existing automation data
- [x] T020 Test data migration script with rollback capability
- [x] T021 Update all automation API endpoints to use get_automation_db() in backend/src/api/v1/automation/*.py
- [x] T022 Update AI agent database connection to use automation database in ai-agent/agent.py
- [x] T023 Test that automation endpoints work with new database

**Acceptance Criteria**:
- Automation database has all required tables (automation_invoice, excel_upload_session, automation_log, transfer_log)
- Main database has updated invoice table with source tracking fields
- Existing automation data successfully migrated to automation database
- All automation endpoints use automation database
- AI agent connects to automation database

---

## Phase 3: User Story 1 - Bulk Invoice Upload and Transfer (4-5 days)

**User Story**: As a business user, I want to upload bulk invoices that are automatically transferred to the main database daily, so I can review and post them manually.

**Goal**: Implement daily transfer job that moves validated invoices from automation DB to main DB

**Independent Test Criteria**:
- Upload Excel file with 10 invoices
- Wait for 7 PM transfer job (or trigger manually)
- Verify 10 invoices appear in main database with source="automation" and status="validated"
- Verify original invoices marked as "transferred" in automation database
- Verify transfer logged in transfer_log table

**Tasks**:

### Transfer Service Implementation

- [ ] T024 [US1] Create TransferService class in backend/src/services/transfer_service.py
- [ ] T025 [US1] Implement transform_invoice_data() method in TransferService to convert JSON to structured format
- [ ] T026 [US1] Implement transfer_validated_invoices() method in TransferService with batch processing
- [ ] T027 [US1] Implement duplicate prevention logic in TransferService (check automation_invoice_id)
- [ ] T028 [US1] Implement transfer logging in TransferService (create TransferLog records)
- [ ] T029 [US1] Add error handling and transaction management per invoice in TransferService

### Scheduler Integration

- [ ] T030 [US1] Add transfer_validated_invoices job to scheduler in backend/src/services/scheduler.py
- [ ] T031 [US1] Configure CronTrigger for 7 PM PKT (hour=19, minute=0, timezone=PAKISTAN_TZ)
- [ ] T032 [US1] Test scheduler job runs at correct time
- [ ] T033 [US1] Add logging for transfer job start/completion in scheduler

### Admin Endpoints

- [x] T034 [P] [US1] Create admin transfer router in backend/src/api/v1/admin/transfer.py
- [x] T034a [US1] Verify require_admin dependency includes JWT verification in backend/src/middleware/rbac.py
- [x] T035 [P] [US1] Implement POST /admin/transfer/trigger endpoint for manual transfer
- [x] T036 [P] [US1] Implement GET /admin/transfer/logs endpoint to view transfer history
- [x] T037 [P] [US1] Implement GET /admin/transfer/stats endpoint for aggregate statistics
- [x] T037a [P] [US1] Implement rate limiting for admin transfer endpoints in backend/src/api/v1/admin/transfer.py (10 requests/hour per admin)
- [x] T038 [US1] Add admin transfer router to main app in backend/src/main.py
- [x] T039 [US1] Test manual transfer trigger endpoint

### Frontend Integration

- [x] T040 [P] [US1] Add source field to invoice history API response in backend/src/api/v1/invoices.py
- [x] T041 [P] [US1] Add source filter to GET /invoices/history endpoint query parameters
- [ ] T042 [P] [US1] Update invoice history page to show source badge in frontend/src/app/(protected)/invoices/history/page.tsx
- [ ] T043 [P] [US1] Add source filter dropdown to invoice history UI in frontend/src/app/(protected)/invoices/history/page.tsx
- [ ] T044 [P] [US1] Update invoice detail view to show transfer metadata in frontend/src/components/invoice-detail.tsx
- [ ] T045 [US1] Test filtering invoices by source in UI

### Integration Testing

- [ ] T046 [US1] Test end-to-end flow: upload → validate → transfer → view in history
- [ ] T047 [US1] Test transfer with 100+ invoices (performance)
- [ ] T048 [US1] Test transfer with invalid data (error handling)
- [ ] T049 [US1] Verify transferred invoices can be posted to FBR manually

**Deliverables**:
- Transfer job runs daily at 7 PM PKT
- Validated invoices transferred to main database with correct status
- Users can see transferred invoices in history with source indicator
- Admin can manually trigger transfer
- Transfer operations logged for audit

---

## Phase 4: User Story 2 - Failed Transfer Recovery (2-3 days)

**User Story**: As a system administrator, I want to recover from failed transfers, so users don't lose access to their invoices.

**Goal**: Implement retry mechanism and admin tools for transfer failure recovery

**Independent Test Criteria**:
- Simulate transfer failure (disconnect database during transfer)
- Verify failed invoices marked as "transfer_failed" in automation database
- Verify transfer failure logged with error details
- Admin can view failed transfers in logs
- Admin can retry failed transfers successfully
- Retried invoices appear in main database

**Tasks**:

### Retry Implementation

- [x] T050 [US2] Implement retry_failed_transfers() method in TransferService in backend/src/services/transfer_service.py
- [x] T051 [US2] Add error classification logic (transient vs permanent) in TransferService
- [x] T052 [US2] Update transfer_validated_invoices() to mark failures as TRANSFER_FAILED status
- [x] T053 [US2] Add detailed error logging with stack traces in TransferService

### Admin Retry Endpoint

- [x] T054 [US2] Implement POST /admin/transfer/retry endpoint in backend/src/api/v1/admin/transfer.py
- [x] T055 [US2] Add request validation for invoice_ids array in retry endpoint
- [x] T056 [US2] Return detailed retry results (success/failure per invoice) in retry endpoint
- [ ] T057 [US2] Test retry endpoint with various failure scenarios

### Monitoring & Alerts

- [ ] T058 [P] [US2] Add transfer failure metrics (counter, histogram) in backend/src/services/transfer_service.py
- [ ] T059 [P] [US2] Add health check endpoint for transfer job status in backend/src/api/v1/health.py
- [ ] T060 [US2] Document alerting setup for transfer failures in docs/operations/monitoring.md

### Testing

- [ ] T061 [US2] Test transfer failure scenarios (database down, network error, invalid data)
- [ ] T062 [US2] Test retry mechanism with previously failed invoices
- [ ] T063 [US2] Verify no data loss during transfer failures
- [ ] T064 [US2] Test concurrent transfer attempts (should be prevented)

**Deliverables**:
- Failed transfers are detected and logged
- Admin can view failed transfer details
- Admin can retry failed transfers
- No data loss during failures
- Monitoring and alerting configured

---

## Phase 5: User Story 3 - Data Cleanup (1-2 days)

**User Story**: As a system administrator, I want old automation data automatically cleaned up, so the database doesn't grow indefinitely.

**Goal**: Implement daily cleanup job to delete old automation data

**Independent Test Criteria**:
- Create test data older than 2 days in automation database
- Run cleanup job (manually or wait for 2 AM)
- Verify old automation_invoice records deleted
- Verify old excel_upload_session records deleted
- Verify automation_log records preserved (longer retention)
- Verify cleanup logged with deletion counts

**Tasks**:

### Cleanup Service Implementation

- [x] T065 [US3] Create CleanupService class in backend/src/services/cleanup_service.py
- [x] T066 [US3] Implement cleanup_old_automation_data() method to delete old invoices and sessions
- [x] T067 [US3] Implement cleanup_old_logs() method with configurable retention for automation_log
- [x] T068 [US3] Add cleanup logging (count of deleted records) in CleanupService
- [x] T069 [US3] Add safety checks (don't delete transfer_failed invoices) in CleanupService

### Scheduler Integration

- [x] T070 [US3] Add cleanup_old_automation_data job to scheduler in backend/src/services/scheduler.py
- [x] T071 [US3] Configure CronTrigger for 2 AM PKT (hour=2, minute=0, timezone=PAKISTAN_TZ)
- [x] T072 [US3] Add CLEANUP_RETENTION_DAYS and AUTOMATION_LOG_RETENTION_DAYS to settings in backend/src/config/settings.py
- [ ] T073 [US3] Test cleanup job with various retention periods

### Testing

- [ ] T074 [US3] Create test data with various ages (1 day, 2 days, 3 days old)
- [ ] T075 [US3] Test cleanup deletes only data older than retention period
- [ ] T076 [US3] Test cleanup preserves transfer_failed invoices
- [ ] T077 [US3] Test cleanup preserves audit logs per configured retention
- [ ] T078 [US3] Verify database size remains stable over time

**Deliverables**:
- Cleanup job runs daily at 2 AM PKT
- Old automation data deleted automatically
- Audit logs preserved per retention policy
- Database size remains stable
- Cleanup operations logged

---

## Phase 6: AI Agent Modifications (2-3 days)

**Goal**: Remove FBR posting from AI agent, keep validation during upload

**Tasks**:

- [x] T079 [P] Remove FBR posting logic from ai-agent/agent.py (lines 229-246 per plan)
- [x] T080 [P] Disable or remove FBRPosterSkill in ai-agent/skills/fbr_poster.py
- [x] T081 [P] Update AI agent to log that manual posting is required instead of posting
- [x] T082 Verify FBR validation still works during Excel upload in backend/src/api/v1/automation/excel.py
- [x] T083 Update AI agent documentation to reflect new behavior in ai-agent/README.md
- [ ] T084 Test that AI agent no longer posts to FBR
- [ ] T085 Test that AI agent still validates invoices during upload
- [ ] T086 Test that AI agent logs appropriately when invoices are ready for transfer

**Acceptance Criteria**:
- AI agent does not post invoices to FBR
- FBR validation still occurs during Excel upload
- AI agent logs indicate manual posting required
- No breaking changes to upload workflow

---

## Phase 7: Polish & Cross-Cutting Concerns (3-4 days)

**Goal**: Complete testing, documentation, and deployment preparation

**Tasks**:

### Testing

- [x] T087 [P] Write unit tests for TransferService in backend/tests/unit/test_transfer_service.py
- [x] T088 [P] Write unit tests for CleanupService in backend/tests/unit/test_cleanup_service.py
- [ ] T089 [P] Write integration tests for transfer flow in backend/tests/integration/test_transfer_flow.py
- [ ] T090 [P] Write integration tests for cleanup flow in backend/tests/integration/test_cleanup_flow.py
- [x] T091 [P] Write API tests for admin transfer endpoints in backend/tests/api/test_admin_transfer.py
- [ ] T092 Load test transfer job with 1000+ invoices
- [ ] T093 Test multi-database connection pooling under load
- [ ] T094 Test error scenarios and recovery paths
- [ ] T095 Verify test coverage >80% for new code

### Documentation

- [ ] T096 [P] Update API documentation with new endpoints in docs/api/
- [ ] T097 [P] Create operations runbook for transfer failures in docs/operations/transfer-runbook.md
- [ ] T098 [P] Document multi-database setup in docs/architecture/database-architecture.md
- [ ] T099 [P] Update deployment guide with migration steps in docs/deployment/
- [ ] T100 Update CHANGELOG.md with feature details

### Deployment Preparation

- [ ] T101 Create deployment checklist in docs/deployment/automation-db-separation-checklist.md
- [ ] T102 Prepare rollback plan in docs/deployment/rollback-plan.md
- [ ] T103 Set up monitoring dashboards for transfer and cleanup jobs
- [ ] T104 Configure alerts for transfer failures and cleanup issues
- [ ] T105 Perform dry-run deployment in staging environment
- [ ] T106 Verify all environment variables documented in .env.example

### Final Validation

- [ ] T107 Run full test suite (unit + integration + API tests)
- [ ] T108 Perform end-to-end testing of all user scenarios
- [ ] T109 Verify performance meets success criteria (1000 invoices in <10 min)
- [ ] T110 Code review and security review
- [ ] T111 Update feature status to "Ready for Production"

**Deliverables**:
- Comprehensive test suite with >80% coverage
- Complete documentation (API, operations, deployment)
- Deployment checklist and rollback plan
- Monitoring and alerting configured
- Feature validated and ready for production

---

## Dependencies & Execution Order

### Critical Path (Must Complete in Order)

1. **Phase 1** (Setup) → **Phase 2** (Foundational) → **Phase 3** (US1)
2. **Phase 3** (US1) → **Phase 4** (US2) - Retry depends on transfer implementation
3. **Phase 2** (Foundational) → **Phase 5** (US3) - Cleanup depends on schema
4. **Phase 2** (Foundational) → **Phase 6** (AI Agent) - Agent changes depend on schema

### Parallel Opportunities

**After Phase 2 completes**, these can run in parallel:
- **Phase 3** (US1 - Transfer) + **Phase 5** (US3 - Cleanup) + **Phase 6** (AI Agent)
- **Phase 4** (US2 - Retry) must wait for Phase 3

**Within each phase**, tasks marked [P] can run in parallel.

### Dependency Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ↓
    ├─→ Phase 3 (US1 - Transfer) → Phase 4 (US2 - Retry)
    ├─→ Phase 5 (US3 - Cleanup)
    └─→ Phase 6 (AI Agent)
    ↓
Phase 7 (Polish)
```

---

## Parallel Execution Examples

### Phase 2 - Foundational (5 parallel tasks)

```bash
# Terminal 1
Task T012: Create TransferLog model

# Terminal 2
Task T013: Add fields to AutomationInvoice model

# Terminal 3
Task T014: Add status enum values

# Terminal 4
Task T015: Add fields to Invoice model

# Terminal 5
Task T016: Create migration for Invoice
```

### Phase 3 - US1 Transfer (4 parallel tasks after T029)

```bash
# Terminal 1
Task T034-T037: Admin endpoints

# Terminal 2
Task T040-T041: Backend API updates

# Terminal 3
Task T042-T044: Frontend updates

# Terminal 4
Task T058-T059: Monitoring setup
```

---

## Implementation Strategy

### MVP Scope (Week 1-2)

**Minimum Viable Product** includes:
- Phase 1: Setup ✅
- Phase 2: Foundational ✅
- Phase 3: US1 (Transfer) ✅
- Basic testing

**Delivers**: Core functionality - invoices transfer daily, users can post manually

### Iteration 2 (Week 3)

- Phase 4: US2 (Retry) ✅
- Phase 5: US3 (Cleanup) ✅
- Phase 6: AI Agent ✅

**Delivers**: Complete feature with recovery and cleanup

### Iteration 3 (Week 4)

- Phase 7: Polish ✅
- Comprehensive testing
- Documentation
- Production deployment

**Delivers**: Production-ready feature

---

## Task Summary

| Phase | Task Count | Parallelizable | Estimated Days |
|-------|------------|----------------|----------------|
| Phase 1: Setup | 10 | 0 | 2-3 |
| Phase 2: Foundational | 13 | 4 | 3-4 |
| Phase 3: US1 - Transfer | 28 | 14 | 4-5 |
| Phase 4: US2 - Retry | 15 | 3 | 2-3 |
| Phase 5: US3 - Cleanup | 14 | 0 | 1-2 |
| Phase 6: AI Agent | 8 | 3 | 2-3 |
| Phase 7: Polish | 25 | 6 | 3-4 |
| **Total** | **113** | **30** | **17-24** |

---

## Success Metrics

### Functional Metrics
- ✅ All 111 tasks completed
- ✅ All user stories independently testable
- ✅ All acceptance criteria met

### Quality Metrics
- ✅ Test coverage >80%
- ✅ Zero critical bugs
- ✅ All documentation complete

### Performance Metrics
- ✅ Transfer 1000 invoices in <10 minutes
- ✅ Transfer success rate >99.9%
- ✅ Cleanup job completes in <5 minutes

---

## Next Steps

1. **Review Tasks**: Review this task breakdown with team
2. **Assign Tasks**: Assign tasks to team members
3. **Set Up Tracking**: Create issues/tickets for each task
4. **Begin Phase 1**: Start with T001 (Create Neon database)
5. **Daily Standups**: Track progress and blockers

---

## Notes

- Tasks marked [P] can be parallelized for faster completion
- Each phase is independently testable
- MVP can be deployed after Phase 3
- Estimated 3-4 weeks for complete implementation
- All file paths are relative to project root

---

**Ready to begin implementation!** 🚀
