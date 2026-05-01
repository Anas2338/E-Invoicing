# Tasks: Auto FBR Posting with Time-Based Controls

**Input**: Design documents from `/specs/003-auto-fbr-posting/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in specification - tasks focus on implementation

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/`
- **Frontend**: `frontend/src/`
- **AI Agent**: `ai-agent/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and environment setup

- [ ] T001 Install uv package manager if not already installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [ ] T002 [P] Setup backend virtual environment with uv in backend/.venv
- [ ] T003 [P] Install backend dependencies with uv pip install in backend/
- [ ] T004 [P] Verify frontend dependencies are installed in frontend/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Schema Changes

- [ ] T005 Create Alembic migration file for auto-posting support in backend/alembic/versions/
- [ ] T006 Add 6 auto-posting columns to users table in migration (auto_posting_enabled, auto_posting_start_time, auto_posting_end_time, auto_posting_environment, auto_posting_daily_limit, auto_posting_paused_until)
- [ ] T007 Add 3 new invoice statuses to invoice_status enum in migration (FBR_POSTING, FBR_POSTED, FBR_FAILED)
- [ ] T008 Add 3 FBR posting columns to invoices table in migration (fbr_posted_at, fbr_posting_error, fbr_retry_count)
- [ ] T009 Create daily_posting_counters table in migration with fields (id, user_id, date, posted_count, window_start_date, created_at, updated_at)
- [ ] T010 Create posting_logs table in migration with fields (id, user_id, invoice_id, action, result, environment, error_details, agent_cycle_id, created_at)
- [ ] T011 Add indexes for performance in migration (users.auto_posting_enabled, invoices.fbr_posting, daily_counters, posting_logs)
- [ ] T012 Run Alembic migration and verify schema changes in database

### Model Extensions

- [ ] T013 [P] Extend User model with auto-posting fields in backend/src/models/user.py
- [ ] T014 [P] Extend Invoice model with FBR posting statuses and fields in backend/src/models/invoice.py
- [ ] T015 [P] Create DailyPostingCounter model in backend/src/models/daily_posting_counter.py
- [ ] T016 [P] Create PostingLog model in backend/src/models/posting_log.py

### Pydantic Schemas

- [ ] T017 [P] Create AutoPostingConfig schema in backend/src/schemas/auto_posting.py
- [ ] T018 [P] Create AutoPostingConfigUpdate schema in backend/src/schemas/auto_posting.py
- [ ] T019 [P] Create ManualPostingResponse schema in backend/src/schemas/auto_posting.py
- [ ] T020 [P] Create PostingStatus schema in backend/src/schemas/auto_posting.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Configure Auto-Posting Settings (Priority: P1) 🎯 MVP

**Goal**: Enable users to configure auto-posting settings in their profile (toggle, time window, environment, daily limit)

**Independent Test**: Navigate to profile settings, configure auto-posting parameters, save settings, verify they persist across sessions

### Backend Implementation for User Story 1

- [ ] T021 [P] [US1] Implement time window validation logic in backend/src/services/auto_posting_service.py (supports midnight-spanning)
- [ ] T022 [P] [US1] Implement daily limit validation logic in backend/src/services/auto_posting_service.py (1-1000 range)
- [ ] T023 [US1] Implement GET /api/v1/profile/auto-posting endpoint in backend/src/api/v1/user_profile.py
- [ ] T024 [US1] Implement PUT /api/v1/profile/auto-posting endpoint in backend/src/api/v1/user_profile.py
- [ ] T025 [US1] Implement POST /api/v1/profile/auto-posting/emergency-pause endpoint in backend/src/api/v1/user_profile.py
- [ ] T026 [US1] Implement temporary pause until date/time logic in PUT /api/v1/profile/auto-posting endpoint (FR-007)
- [ ] T027 [US1] Add validation for Sandbox→Production environment switch (require re-authentication) in backend/src/api/v1/user_profile.py
- [ ] T028 [US1] Add audit logging for configuration changes in backend/src/api/v1/user_profile.py

### Frontend Implementation for User Story 1

- [ ] T029 [P] [US1] Create AutoPostingSettings component in frontend/src/components/profile/AutoPostingSettings.tsx
- [ ] T030 [P] [US1] Create auto-posting API client functions in frontend/src/services/autoPostingApi.ts
- [ ] T031 [US1] Integrate AutoPostingSettings component into profile page in frontend/src/app/(protected)/profile/page.tsx
- [ ] T032 [US1] Add form validation for time window (supports midnight-spanning) in AutoPostingSettings component
- [ ] T033 [US1] Add form validation for daily limit (1-1000) in AutoPostingSettings component
- [ ] T034 [US1] Add environment selector with confirmation dialog for Production in AutoPostingSettings component
- [ ] T035 [US1] Add loading states and error handling in AutoPostingSettings component
- [ ] T036 [US1] Add success feedback after saving settings in AutoPostingSettings component

**Checkpoint**: User Story 1 complete - users can configure auto-posting settings in profile

---

## Phase 4: User Story 2 - Automatic Invoice Posting During Active Hours (Priority: P2)

**Goal**: AI agent automatically posts invoices to FBR during configured time windows, respecting daily limits

**Independent Test**: Configure auto-posting settings, upload validated invoices, wait for scheduled time window, verify invoices are automatically posted to FBR

### Backend Service Layer for User Story 2

- [ ] T037 [P] [US2] Implement is_within_time_window() function in backend/src/services/auto_posting_service.py (handles midnight-spanning)
- [ ] T038 [P] [US2] Implement get_daily_limit_remaining() function in backend/src/services/auto_posting_service.py (handles midnight-spanning continuity)
- [ ] T039 [P] [US2] Implement get_or_create_daily_counter() function in backend/src/services/auto_posting_service.py
- [ ] T040 [P] [US2] Implement increment_daily_counter() function in backend/src/services/auto_posting_service.py
- [ ] T041 [P] [US2] Implement calculate_failure_rate() function in backend/src/services/auto_posting_service.py (FR-028)
- [ ] T042 [US2] Implement post_invoice_to_fbr() function in backend/src/services/auto_posting_service.py (sequential posting, network failure handling)
- [ ] T043 [US2] Implement create_posting_log() function in backend/src/services/auto_posting_service.py
- [ ] T044 [US2] Add error classification logic (retryable vs permanent) in backend/src/services/auto_posting_service.py
- [ ] T045 [US2] Add retry scheduling with exponential backoff in backend/src/services/auto_posting_service.py
- [ ] T046 [US2] Add auto-pause logic when failure rate exceeds 20% in last hour (FR-028) in backend/src/services/auto_posting_service.py
- [ ] T047 [US2] Add auto-resume logic after 1 hour if failure rate drops below threshold (FR-029) in backend/src/services/auto_posting_service.py

### AI Agent Implementation for User Story 2

- [ ] T048 [P] [US2] Create FBRPosterSkill class in ai-agent/skills/fbr_poster.py
- [ ] T049 [US2] Implement get_users_with_auto_posting_enabled() in ai-agent/skills/fbr_poster.py (checks pause status and failure rate)
- [ ] T050 [US2] Implement get_eligible_invoices_for_user() in ai-agent/skills/fbr_poster.py (filters by status, time, limit)
- [ ] T051 [US2] Implement post_invoices_for_user() in ai-agent/skills/fbr_poster.py (sequential posting)
- [ ] T052 [US2] Add _post_to_fbr_job() method to AIAgent class in ai-agent/agent.py
- [ ] T053 [US2] Schedule FBR posting job with 5-minute interval in ai-agent/agent.py
- [ ] T054 [US2] Add logging for agent cycle start/end in ai-agent/agent.py
- [ ] T055 [US2] Add logging for per-user posting results in ai-agent/agent.py
- [ ] T056 [US2] Add heartbeat update during posting cycle in ai-agent/agent.py

**Checkpoint**: User Story 2 complete - AI agent automatically posts invoices during configured hours

---

## Phase 5: User Story 3 - Manual Override for Individual Invoices (Priority: P3)

**Goal**: Users can manually post individual invoices immediately, regardless of auto-posting settings or time window

**Independent Test**: Disable auto-posting or be outside time window, select an invoice, click manual post button, verify immediate posting to FBR

### Backend Implementation for User Story 3

- [ ] T057 [US3] Implement POST /api/v1/invoices/{invoice_id}/post-to-fbr endpoint in backend/src/api/v1/invoices.py
- [ ] T058 [US3] Implement POST /api/v1/invoices/{invoice_id}/post-to-fbr/override-limit endpoint in backend/src/api/v1/invoices.py
- [ ] T059 [US3] Add validation for invoice status (must be TRANSFERRED) in manual posting endpoint
- [ ] T060 [US3] Add daily limit check with warning response in manual posting endpoint
- [ ] T061 [US3] Add duplicate posting prevention (check if already FBR_POSTING) in manual posting endpoint
- [ ] T062 [US3] Integrate with auto_posting_service.post_invoice_to_fbr() for actual posting
- [ ] T063 [US3] Count manual posts toward daily limit in manual posting endpoint
- [ ] T064 [US3] Add immediate error feedback for manual posting failures

### Frontend Implementation for User Story 3

- [ ] T065 [P] [US3] Create ManualPostButton component in frontend/src/components/invoices/ManualPostButton.tsx
- [ ] T066 [P] [US3] Add manual posting API functions in frontend/src/services/autoPostingApi.ts
- [ ] T067 [US3] Integrate ManualPostButton into invoice history page in frontend/src/app/(protected)/invoices/history/page.tsx
- [ ] T068 [US3] Add loading state during manual posting in ManualPostButton component
- [ ] T069 [US3] Add daily limit warning dialog in ManualPostButton component
- [ ] T070 [US3] Add success/error feedback after manual posting in ManualPostButton component
- [ ] T071 [US3] Disable button for invoices not in TRANSFERRED status in ManualPostButton component
- [ ] T072 [US3] Refresh invoice list after successful manual posting

**Checkpoint**: User Story 3 complete - users can manually post invoices anytime

---

## Phase 6: User Story 4 - Monitor Posting Status and Statistics (Priority: P4)

**Goal**: Users can view real-time auto-posting status, today's statistics, and next check time on invoice history page

**Independent Test**: Enable auto-posting, view invoice history page, verify status indicators and statistics display correctly and update in real-time

### Backend Implementation for User Story 4

- [ ] T073 [US4] Implement GET /api/v1/invoices/posting-status endpoint in backend/src/api/v1/invoices.py
- [ ] T074 [US4] Implement GET /api/v1/invoices/posting-history endpoint in backend/src/api/v1/invoices.py
- [ ] T075 [US4] Add logic to calculate current status (active/outside_hours/disabled/paused/limit_reached) in posting-status endpoint
- [ ] T076 [US4] Add logic to calculate next check time based on agent schedule in posting-status endpoint
- [ ] T077 [US4] Add logic to fetch today's statistics (posted_count, failed_count, remaining_limit) in posting-status endpoint
- [ ] T078 [US4] Add pagination support for posting-history endpoint
- [ ] T079 [US4] Add filters for posting-history (action, result, date_range) in posting-history endpoint

### Frontend Implementation for User Story 4

- [ ] T080 [P] [US4] Create AutoPostingStatus component in frontend/src/components/invoices/AutoPostingStatus.tsx
- [ ] T081 [P] [US4] Add posting status API functions in frontend/src/services/autoPostingApi.ts
- [ ] T082 [US4] Integrate AutoPostingStatus into invoice history page in frontend/src/app/(protected)/invoices/history/page.tsx
- [ ] T083 [US4] Add status indicator with color coding (green/orange/red) in AutoPostingStatus component
- [ ] T084 [US4] Add today's statistics display (posted/failed/remaining) in AutoPostingStatus component
- [ ] T085 [US4] Add next check time countdown in AutoPostingStatus component
- [ ] T086 [US4] Add emergency pause button in AutoPostingStatus component
- [ ] T087 [US4] Add 30-second polling for status updates in AutoPostingStatus component
- [ ] T088 [US4] Add quick link to profile settings in AutoPostingStatus component

**Checkpoint**: User Story 4 complete - users can monitor auto-posting status and statistics

---

## Phase 7: User Story 5 - Receive Notifications About Posting Activity (Priority: P5)

**Goal**: Users receive automated notifications about posting activity in the dashboard notification center (daily summaries, limit alerts, failure warnings)

**Independent Test**: Configure auto-posting, allow invoices to be posted throughout the day, verify notifications appear in dashboard notification center at appropriate times with correct information

### Backend Implementation for User Story 5

- [ ] T089 [P] [US5] Create notification service in backend/src/services/notification_service.py
- [ ] T090 [US5] Implement create_daily_summary_notification() function in notification_service.py
- [ ] T091 [US5] Implement create_daily_limit_reached_notification() function in notification_service.py
- [ ] T092 [US5] Implement create_high_failure_rate_notification() function in notification_service.py
- [ ] T093 [US5] Implement create_auto_posting_paused_notification() function in notification_service.py
- [ ] T094 [US5] Implement create_auto_posting_resumed_notification() function in notification_service.py
- [ ] T095 [US5] Add daily summary job to AI agent (runs at midnight PKT) in ai-agent/agent.py
- [ ] T096 [US5] Add notification triggers in auto_posting_service.py (limit reached, high failure rate)
- [ ] T097 [US5] Add notification trigger in emergency pause endpoint
- [ ] T098 [US5] Add notification trigger when pause period ends in AI agent

**Checkpoint**: User Story 5 complete - users receive dashboard notifications about posting activity

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Security Implementation (FR-053 to FR-058)

- [ ] T099 [P] Implement JWT authentication verification for all auto-posting endpoints in backend/src/api/v1/
- [ ] T100 [P] Implement row-level data isolation checks (user can only access own invoices/config) in backend/src/api/v1/
- [ ] T101 [P] Implement FBR credential validation before allowing Production posting in backend/src/services/auto_posting_service.py
- [ ] T102 [P] Implement re-authentication requirement when switching Sandbox → Production in backend/src/api/v1/user_profile.py
- [ ] T103 [P] Implement audit logging for all auto-posting configuration changes in backend/src/services/audit_service.py
- [ ] T104 [P] Implement environment isolation validation (no cross-posting) in backend/src/services/auto_posting_service.py

### Error Handling & Retry Logic

- [ ] T105 [P] Implement exponential backoff retry logic (1 min, 5 min, 15 min) with timing validation in backend/src/services/auto_posting_service.py
- [ ] T106 [P] Implement error classification (retryable vs permanent) in backend/src/services/auto_posting_service.py
- [ ] T107 [P] Add comprehensive error handling across all endpoints in backend/src/api/v1/

### General Polish

- [ ] T108 [P] Add input sanitization for all form fields in frontend components
- [ ] T109 [P] Add rate limiting for manual posting endpoint in backend/src/api/v1/invoices.py
- [ ] T110 [P] Optimize database queries with proper indexes (verify migration indexes are effective)
- [ ] T111 [P] Add logging for all FBR API interactions in backend/src/services/auto_posting_service.py
- [ ] T112 [P] Add monitoring metrics for agent performance in ai-agent/agent.py
- [ ] T113 [P] Update API documentation with new endpoints in backend/docs/
- [ ] T114 [P] Create user guide for auto-posting feature in docs/AUTO_POSTING_GUIDE.md
- [ ] T115 [P] Create troubleshooting guide for common issues in docs/AUTO_POSTING_TROUBLESHOOTING.md

### Validation & Testing

- [ ] T116 Verify all acceptance scenarios from spec.md are met
- [ ] T117 Run quickstart.md validation steps
- [ ] T118 Performance testing with 100 concurrent users
- [ ] T119 Security review of auto-posting endpoints and agent logic

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - No dependencies on other stories (but logically builds on US1)
  - User Story 3 (P3): Can start after Foundational - No dependencies on other stories (but uses US2 service layer)
  - User Story 4 (P4): Can start after Foundational - No dependencies on other stories (but displays US2 data)
  - User Story 5 (P5): Can start after Foundational - No dependencies on other stories (but notifies about US2 events)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

All user stories are designed to be independently implementable after Foundational phase:

- **User Story 1 (P1)**: Configuration UI and backend - standalone
- **User Story 2 (P2)**: AI agent posting - uses US1 config but can be tested independently
- **User Story 3 (P3)**: Manual override - uses US2 service but can be tested independently
- **User Story 4 (P4)**: Status monitoring - displays US2 data but can be tested independently
- **User Story 5 (P5)**: Notifications - triggered by US2 events but can be tested independently

### Within Each User Story

- Backend services before API endpoints
- API endpoints before frontend components
- Frontend components before integration
- Core implementation before error handling and polish

### Parallel Opportunities

**Phase 1 (Setup)**: All tasks can run in parallel (T002, T003, T004)

**Phase 2 (Foundational)**:
- Database migration tasks are sequential (T005-T012)
- Model extensions can run in parallel after migration (T013, T014, T015, T016)
- Pydantic schemas can run in parallel (T017, T018, T019, T020)

**Phase 3 (User Story 1)**:
- Backend tasks: T021 and T022 can run in parallel, then T023-T027 sequential
- Frontend tasks: T028 and T029 can run in parallel, then T030-T035 sequential
- Backend and Frontend can run in parallel

**Phase 4 (User Story 2)**:
- Backend service functions can run in parallel (T036, T037, T038, T039)
- AI agent tasks: T044 can start, then T045-T047 in parallel, then T048-T052 sequential
- Backend and AI agent can run in parallel

**Phase 5 (User Story 3)**:
- Backend tasks are mostly sequential (T053-T060)
- Frontend tasks: T061 and T062 can run in parallel, then T063-T068 sequential
- Backend and Frontend can run in parallel

**Phase 6 (User Story 4)**:
- Backend tasks are mostly sequential (T069-T075)
- Frontend tasks: T076 and T077 can run in parallel, then T078-T084 sequential
- Backend and Frontend can run in parallel

**Phase 7 (User Story 5)**:
- T085, T086 can run in parallel
- T087-T091 can run in parallel after T085
- T092-T095 sequential after notification functions ready

**Phase 8 (Polish)**: Most tasks can run in parallel (T096-T104)

---

## Parallel Example: User Story 1

```bash
# Backend - parallel service functions:
Task T021: "Implement time window validation logic in backend/src/services/auto_posting_service.py"
Task T022: "Implement daily limit validation logic in backend/src/services/auto_posting_service.py"

# Frontend - parallel component and API client:
Task T028: "Create AutoPostingSettings component in frontend/src/components/profile/AutoPostingSettings.tsx"
Task T029: "Create auto-posting API client functions in frontend/src/services/autoPostingApi.ts"

# Backend and Frontend can work in parallel
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T020) - CRITICAL
3. Complete Phase 3: User Story 1 (T021-T035)
4. **STOP and VALIDATE**: Test configuration UI independently
5. Deploy/demo if ready

**MVP Delivers**: Users can configure auto-posting settings in their profile

### Incremental Delivery

1. **Foundation** (Phase 1-2): Database and models ready
2. **MVP** (Phase 3): Configuration UI → Test independently → Deploy
3. **Core Value** (Phase 4): Auto-posting agent → Test independently → Deploy
4. **Flexibility** (Phase 5): Manual override → Test independently → Deploy
5. **Visibility** (Phase 6): Status monitoring → Test independently → Deploy
6. **Engagement** (Phase 7): Notifications → Test independently → Deploy
7. **Polish** (Phase 8): Cross-cutting improvements

Each phase adds value without breaking previous functionality.

### Parallel Team Strategy

With multiple developers after Foundational phase completes:

- **Developer A**: User Story 1 (Configuration) - T021-T035
- **Developer B**: User Story 2 (Agent) - T036-T052
- **Developer C**: User Story 3 (Manual Override) - T053-T068

Stories complete and integrate independently.

---

## Task Summary

- **Total Tasks**: 119
- **Setup Tasks**: 4 (T001-T004)
- **Foundational Tasks**: 16 (T005-T020)
- **User Story 1 Tasks**: 16 (T021-T036) - Configuration
- **User Story 2 Tasks**: 20 (T037-T056) - Auto-posting Agent
- **User Story 3 Tasks**: 16 (T057-T072) - Manual Override
- **User Story 4 Tasks**: 16 (T073-T088) - Status Monitoring
- **User Story 5 Tasks**: 10 (T089-T098) - Dashboard Notifications
- **Polish Tasks**: 21 (T099-T119) - Security, Error Handling, Validation

**Parallel Opportunities**: 40+ tasks marked [P] can run in parallel within their phase

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (36 tasks) delivers configuration UI

**Full Feature**: All 119 tasks deliver complete auto-posting system with all 5 user stories

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Use `uv pip install` for all Python package installations
- All times handled in PKT timezone (UTC+5)
- Sequential posting enforced (one invoice at a time per user)
- Network failures marked as non-retryable to prevent duplicates
