# Tasks: Separate AI-Agent (Automation) from Main Backend

**Input**: Design documents from `/specs/001-separate-ai-agent/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/automation-api.md

**Tests**: Not explicitly requested in spec — test tasks omitted. Validation via quickstart.md verification checklist.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Two backend services (`backend/` + `ai-agent/`) + one frontend (`frontend/`) per plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the ai-agent/ directory structure, package configuration, and environment templates

- [x] T001 Create ai-agent/ top-level directory structure with all subdirectories: `ai-agent/src/`, `ai-agent/src/config/`, `ai-agent/src/database/`, `ai-agent/src/models/`, `ai-agent/src/schemas/`, `ai-agent/src/services/`, `ai-agent/src/api/v1/automation/`, `ai-agent/src/api/middleware/`, `ai-agent/src/middleware/`, `ai-agent/src/utils/`, `ai-agent/assets/`, `ai-agent/alembic/versions/`
- [x] T002 [P] Create `ai-agent/pyproject.toml` with uv-managed dependencies: fastapi, sqlmodel, sqlalchemy, pydantic-settings, uvicorn, httpx, psycopg2-binary, python-jose[cryptography], passlib[bcrypt], alembic, python-dotenv, pandas, openpyxl, apscheduler, slowapi, anthropic, reportlab, qrcode, pillow, cryptography, python-magic, python-magic-bin, fastapi-csrf-protect, pytz, psutil
- [x] T003 [P] Create `ai-agent/.env.example` with all required environment variables per quickstart.md (DATABASE_URL, AUTH_JWT_SECRET, ENCRYPTION_KEY, FBR_*, ANTHROPIC_API_KEY, ALLOWED_ORIGINS, CSRF_SECRET, schedule parameters)
- [x] T004 [P] Create `ai-agent/.gitignore` with Python/uv patterns (__pycache__, .venv, .env, *.pyc, uv.lock exception if committed)
- [x] T005 [P] Create `ai-agent/Dockerfile` with multi-stage build using uv for dependency installation and uvicorn runner
- [x] T006 [P] Create `ai-agent/alembic.ini` and `ai-agent/alembic/env.py` configured for the automation database

**Checkpoint**: ai-agent/ directory skeleton ready, dependencies installable via `uv sync`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core AI-agent infrastructure that MUST be complete before automation endpoints can be served

**⚠️ CRITICAL**: No user story work for US2/US3 can begin until this phase is complete

- [x] T007 Create `ai-agent/src/config/__init__.py` and `ai-agent/src/config/settings.py` — automation-specific Settings class using pydantic-settings with: automation_database_url, auth_jwt_secret (same secret as main backend), encryption_key, fbr_sandbox_base_url, fbr_production_base_url, fbr_api_key, fbr_client_id, anthropic_api_key, allowed_origins, csrf_secret, transfer_schedule_hour/minute, cleanup_schedule_hour/minute, cleanup_retention_days, automation_log_retention_days, dry_run, log_level, db_echo
- [x] T008 Create `ai-agent/src/database/__init__.py` and `ai-agent/src/database/session.py` — automation DB engine only: create SQLAlchemy engine from settings.automation_database_url with pool_pre_ping=True, pool_size=5, max_overflow=10, pool_recycle=300, pool_timeout=30, connect_timeout=60; import all automation models; create automation_metadata tables on startup; provide get_automation_db_session() context manager and get_automation_db() FastAPI dependency
- [x] T009 [P] Create `ai-agent/src/api/deps.py` — FastAPI dependencies: get_database_session() yielding automation DB session, get_pagination_params(skip=0, limit=100), get_current_user() placeholder
- [x] T010 [P] Copy `backend/src/api/middleware/auth_middleware.py` to `ai-agent/src/api/middleware/auth_middleware.py` — update all internal imports to use `ai-agent.src.*` paths; identical JWT validation logic using settings.auth_jwt_secret
- [x] T011 [P] Copy `backend/src/middleware/rbac.py` to `ai-agent/src/middleware/rbac.py` — update imports for ai-agent paths; keep require_automation_access dependency
- [x] T012 Copy `backend/src/middleware/csrf_middleware.py` to `ai-agent/src/middleware/csrf_middleware.py` (if separate file) or ensure CSRF configuration is included in ai-agent main.py middleware stack
- [x] T013 [P] Copy `backend/src/utils/secure_file_validator.py` to `ai-agent/src/utils/secure_file_validator.py` — update imports for ai-agent paths
- [x] T014 [P] Copy required utilities from `backend/src/utils/helpers.py` to `ai-agent/src/utils/helpers.py` — calculate_hash, validate_fbr_invoice_structure, and any other functions used by automation services
- [x] T015 Copy `backend/src/utils/error_handlers.py` to `ai-agent/src/utils/error_handlers.py` — update imports for ai-agent paths; StarletteHTTPException, RequestValidationError, generic Exception handlers
- [x] T016 [P] Copy `backend/src/utils/rate_limits.py` to `ai-agent/src/utils/rate_limits.py` — update imports for ai-agent paths; rate limit definitions used by automation endpoints
- [x] T017 Create `ai-agent/src/main.py` — FastAPI app with: title "FBR AI Agent - Invoice Automation Service", version "1.0.0", docs at /api/v1/docs; middleware stack (CORSMiddleware, SecurityHeadersMiddleware, RequestSizeLimitMiddleware, SessionTimeoutMiddleware, CSRFMiddleware, AuthMiddleware); include automation_router under prefix /api/v1 with tags ["automation"]; lifecycle events (on_startup: create automation DB tables, start automation scheduler; on_shutdown: stop scheduler); root / health endpoint returning service-specific status; CORS configured from settings.allowed_origins

**Checkpoint**: AI-agent starts on port 8002 with `uv run uvicorn src.main:app --port 8002`, health endpoint responds, middleware active

---

## Phase 3: User Story 1 - Portal Operator Uses Manual Invoices Normally (Priority: P1) 🎯 MVP

**Goal**: Main backend (`backend/`) contains ZERO automation code. All manual invoice operations (create, list, Excel upload, PDF print, FBR post) work identically as before the separation.

**Independent Test**: Start the main backend on port 8001 (AI-agent does NOT need to be running). Login, create a manual invoice, download Excel template, upload manual Excel file, print PDF, post to FBR. All operations succeed without errors.

### Implementation for User Story 1

- [x] T018 [US1] Remove `from src.api.v1.automation import router as automation_router` and `app.include_router(automation_router, ...)` from `backend/src/main.py`
- [x] T019 [P] [US1] Remove automation engine creation (automation_engine) from `backend/src/database/session.py`: delete lines creating automation_engine from settings.automation_database_url, delete automation model imports (AutomationInvoice, AutomationLog, ExcelUploadSession, AIAgentHealthCheck), delete automation_metadata import, delete automation_metadata.create_all() call, delete get_automation_db_session() function, delete get_automation_db() function
- [x] T020 [P] [US1] Delete the entire `backend/src/api/v1/automation/` directory (all 7 route files: `__init__.py`, excel.py, dashboard.py, retry.py, health.py, agent_status.py, file_management.py, pdf.py)
- [x] T021 [P] [US1] Delete 5 automation model files from `backend/src/models/`: automation_base.py, automation_invoice.py, automation_log.py, ai_agent_health_check.py, excel_upload_session.py
- [x] T022 [P] [US1] Delete 4 automation schema files from `backend/src/schemas/`: automation.py, agent.py, excel.py, file_management.py
- [x] T023 [P] [US1] Delete 4 automation service files from `backend/src/services/`: automation_service.py, excel_service.py, file_management_service.py, background_validation_service.py
- [x] T024 [P] [US1] Delete `backend/src/utils/excel_validator.py` (moves to ai-agent/)
- [x] T025 [P] [US1] Remove automation-related settings from `backend/src/config/settings.py`: automation_database_url, transfer_schedule_hour, transfer_schedule_minute, cleanup_schedule_hour, cleanup_schedule_minute, cleanup_retention_days, automation_log_retention_days, anthropic_api_key (if only used by automation)
- [x] T026 [US1] Fix manual Excel upload in `backend/src/api/v1/invoices.py`: remove `from src.database.session import get_automation_db` import; extract manual-only Excel methods into `backend/src/utils/manual_excel_helper.py` containing `generate_manual_excel_template()` (creates Excel with manual columns, no scheduled_date/time) and `parse_excel_for_manual_invoice()` (parses Excel rows, validates dates are past/today, auto-populates from saved items); update the `/excel/template/download` endpoint to use ManualExcelHelper instead of ExcelService(automation_db); update `/excel/upload` endpoint to remove automation_db dependency, use ManualExcelHelper for parsing
- [x] T027 [US1] Audit `backend/src/api/v1/invoices.py` for remaining automation references: verify `automation_invoice_id` is properly nullable in InvoiceResponse (already nullable in model), verify unified-history endpoint returns only manual invoices (no automation DB join), verify no other imports from automation modules remain
- [x] T028 [US1] Remove automation-related alembic migration files from `backend/alembic/versions/`: a1b2c3d4e5f6_*, 5a391983efbf_*, ac863f48f1f9_*, c942623196b2_*, eb8c6704d50a_*, f038b6c5a63d_*, 20260424_002816_*
- [x] T029 [US1] Verify `backend/src/models/__init__.py` — confirm no automation models in __all__ (already excluded per current code), no changes needed
- [x] T030 [US1] Verify `backend/src/models/user.py` — confirm `automation_enabled` column remains (flag controls frontend UI access, not automation logic); this is a user attribute, not automation code
- [x] T031 [US1] Run backend startup validation: `cd backend && uv run uvicorn src.main:app --port 8001` — confirm app starts without import errors, all non-automation routers load, scheduler starts

**Checkpoint**: Main backend runs clean — zero automation files present, all manual invoice operations functional

---

## Phase 4: User Story 2 - Automation User Uploads Future-Date Invoices via AI-Agent (Priority: P1)

**Goal**: AI-agent serves all 24 automation endpoints identically. Users can upload Excel with future-dated invoices, monitor validation progress, manage invoices (retry, pause, resume, block, delete, bulk actions), and generate PDFs.

**Independent Test**: Start AI-agent on port 8002. Using curl/Postman (authenticated with JWT from main backend), exercise: upload automation Excel → poll status → list invoices → view detail → retry failed → pause/resume → block/unblock → print single PDF → print batch PDF → bulk delete → list upload sessions → delete session. All 24 endpoints return expected responses.

### Implementation for User Story 2

**Models (MOVED from backend)**:

- [x] T032 [P] [US2] Copy `backend/src/models/automation_base.py` → `ai-agent/src/models/automation_base.py` — update imports to `ai-agent.src.*` paths; defines automation_metadata (separate SQLAlchemy MetaData instance)
- [x] T033 [P] [US2] Copy `backend/src/models/automation_invoice.py` → `ai-agent/src/models/automation_invoice.py` — update imports; AutomationInvoice model with all fields per data-model.md, AutomationInvoiceStatus enum (PENDING, EXPIRED, VALIDATED, TRANSFERRED, TRANSFER_FAILED, FAILED, BLOCKED, PAUSED)
- [x] T034 [P] [US2] Copy `backend/src/models/automation_log.py` → `ai-agent/src/models/automation_log.py` — update imports; AutomationLog model, AutomationLogAction enum (VALIDATE, SUBMIT, RETRY, BLOCK, UNBLOCK, PAUSE, RESUME, DELETE, TRANSFER), AutomationLogStatus enum (SUCCESS, FAILURE, IN_PROGRESS)
- [x] T035 [P] [US2] Copy `backend/src/models/excel_upload_session.py` → `ai-agent/src/models/excel_upload_session.py` — update imports; ExcelUploadSession model, ExcelUploadProcessingStatus enum
- [x] T036 [P] [US2] Create `ai-agent/src/models/__init__.py` — export all 4 automation models

**Schemas (MOVED from backend)**:

- [x] T037 [P] [US2] Copy `backend/src/schemas/automation.py` → `ai-agent/src/schemas/automation.py` — update imports; DashboardStatsResponse, InvoiceListResponse, InvoiceDetailResponse, BatchPdfRequest, etc.
- [x] T038 [P] [US2] Copy `backend/src/schemas/excel.py` → `ai-agent/src/schemas/excel.py` — update imports; ExcelUploadResponse, ExcelUploadStatusResponse
- [x] T039 [P] [US2] Copy `backend/src/schemas/file_management.py` → `ai-agent/src/schemas/file_management.py` — update imports; UploadSessionListResponse, BlockInvoiceRequest, BulkBlockRequest, BulkDeleteRequest, BulkRetryRequest, etc.
- [x] T040 [P] [US2] Create `ai-agent/src/schemas/__init__.py`

**Shared Services (COPIED from backend)**:

- [x] T041 [P] [US2] Copy `backend/src/services/validation_service.py` → `ai-agent/src/services/validation_service.py` — update all imports to `ai-agent.src.*` paths; no logic changes (FBR-spec validation rules are identical)
- [x] T042 [P] [US2] Copy `backend/src/services/fbr_client.py` → `ai-agent/src/services/fbr_client.py` — update imports; FBR API HTTP client for sandbox/production
- [x] T043 [P] [US2] Copy `backend/src/services/fbr_service.py` → `ai-agent/src/services/fbr_service.py` — update imports; FBR service wrapper used by automation validation

**Automation Services (MOVED from backend)**:

- [x] T044 [P] [US2] Copy `backend/src/services/automation_service.py` → `ai-agent/src/services/automation_service.py` — update all imports to `ai-agent.src.*` paths; core automation business logic (get_invoice_by_id, get_dashboard_stats, get_invoice_list, get_invoice_detail with logs, retry_invoice, pause/resume/block/unblock, bulk operations, delete)
- [x] T045 [P] [US2] Copy `backend/src/services/excel_service.py` → `ai-agent/src/services/excel_service.py` — update imports; full Excel processing (generate automation template with scheduled_date/scheduled_time, parse Excel, validate future dates, create automation invoices)
- [x] T046 [P] [US2] Copy `backend/src/services/file_management_service.py` → `ai-agent/src/services/file_management_service.py` — update imports; upload session management, Excel file deletion
- [x] T047 [P] [US2] Copy `backend/src/services/background_validation_service.py` → `ai-agent/src/services/background_validation_service.py` — update imports; background validation worker for Excel upload sessions
- [x] T048 [P] [US2] Copy `backend/src/utils/excel_validator.py` → `ai-agent/src/utils/excel_validator.py` — update imports; REQUIRED_COLUMNS (18 automation columns including scheduled_date/scheduled_time), validation methods

**PDF Service (NEW for AI-agent)**:

- [x] T049 [US2] Create `ai-agent/src/services/pdf_service.py` — dedicated automation PDF generation: reads from AutomationInvoice.invoice_data JSON (not structured Invoice model), generates FBR-compliant PDF with logo and QR code, uses same reportlab/qrcode/Pillow stack; copy `backend/src/assets/fbr_logo.png` and `backend/src/assets/NotoSansArabic-Regular.ttf` to `ai-agent/assets/`; supports single and batch PDF generation
- [x] T050 [US2] Copy `backend/src/assets/fbr_logo.png` → `ai-agent/assets/fbr_logo.png`
- [x] T051 [US2] Copy `backend/src/assets/NotoSansArabic-Regular.ttf` → `ai-agent/assets/NotoSansArabic-Regular.ttf` (if exists)

**API Routes (MOVED from backend)**:

- [x] T052 [P] [US2] Copy `backend/src/api/v1/automation/excel.py` → `ai-agent/src/api/v1/automation/excel.py` — update ALL imports to `ai-agent.src.*` paths; endpoints: GET /automation/template/download, POST /automation/excel/upload, GET /automation/excel/status/{session_id}
- [x] T053 [P] [US2] Copy `backend/src/api/v1/automation/dashboard.py` → `ai-agent/src/api/v1/automation/dashboard.py` — update ALL imports; endpoints: GET /automation/dashboard/stats, GET /automation/dashboard/invoices, GET /automation/dashboard/invoice/{id}, GET /automation/dashboard/download/{session_id}
- [x] T054 [P] [US2] Copy `backend/src/api/v1/automation/retry.py` → `ai-agent/src/api/v1/automation/retry.py` — update ALL imports; endpoints: POST /automation/invoice/{id}/retry
- [x] T055 [P] [US2] Copy `backend/src/api/v1/automation/file_management.py` → `ai-agent/src/api/v1/automation/file_management.py` — update ALL imports; endpoints: GET /automation/upload-sessions, DELETE /automation/upload-session/{id}, DELETE /automation/upload-session/{id}/file, POST /automation/invoice/{id}/block, POST /automation/invoice/{id}/unblock, DELETE /automation/invoice/{id}, POST /automation/invoices/bulk-block, POST /automation/invoices/bulk-delete, POST /automation/invoices/bulk-retry, POST /automation/invoice/{id}/pause, POST /automation/invoice/{id}/resume, POST /automation/invoices/bulk-pause, POST /automation/invoices/bulk-resume
- [x] T056 [P] [US2] Copy `backend/src/api/v1/automation/pdf.py` → `ai-agent/src/api/v1/automation/pdf.py` — update ALL imports (use ai-agent's pdf_service, not backend's); simplify to handle AutomationInvoice only (remove manual Invoice handling branches); endpoints: GET /automation/invoices/{id}/pdf, POST /automation/invoices/batch-pdf
- [x] T057 Create `ai-agent/src/api/v1/automation/__init__.py` — APIRouter with prefix="/automation"; include sub-routers from excel, dashboard, retry, health, agent_status, file_management, pdf modules
- [x] T058 [P] [US2] Create `ai-agent/src/services/__init__.py` — empty service package init
- [x] T059 [P] [US2] Create `ai-agent/src/utils/__init__.py` — empty utils package init
- [x] T060 [US2] Create `ai-agent/src/api/__init__.py` and `ai-agent/src/api/v1/__init__.py` — empty API package init files
- [x] T061 [US2] Run AI-agent startup validation: `cd ai-agent && uv run uvicorn src.main:app --port 8002` — confirm app starts, automation router loads, all 24 endpoints registered, no import errors

**Checkpoint**: AI-agent serves all automation endpoints. Upload Excel, monitor progress, manage invoices, print PDFs — all work independently.

---

## Phase 5: User Story 3 - Administrator Manages AI-Agent Health (Priority: P2)

**Goal**: AI-agent exposes health check and agent status endpoints for operational monitoring. Main backend continues working when AI-agent is down.

**Independent Test**: Start AI-agent on port 8002. Call GET /automation/health — returns healthy status, DB connected, FBR API reachable. Call GET /automation/agent/status — returns detailed metrics (pending count, failed count, backlogs, CPU/memory, anomalies, recommendations). Stop AI-agent, verify main backend on port 8001 still serves manual invoices.

### Implementation for User Story 3

- [x] T062 [US3] Copy `backend/src/api/v1/automation/health.py` → `ai-agent/src/api/v1/automation/health.py` — update ALL imports to `ai-agent.src.*` paths; endpoint: GET /automation/health returns DB connectivity, FBR API reachability, overall status
- [x] T063 [US3] Copy `backend/src/api/v1/automation/agent_status.py` → `ai-agent/src/api/v1/automation/agent_status.py` — update ALL imports; endpoint: GET /automation/agent/status returns detailed health metrics per contracts/automation-api.md section 24
- [x] T064 [P] [US3] Copy `backend/src/models/ai_agent_health_check.py` → `ai-agent/src/models/ai_agent_health_check.py` — update imports; AIAgentHealthCheck model with all fields per data-model.md
- [x] T065 [P] [US3] Copy `backend/src/schemas/agent.py` → `ai-agent/src/schemas/agent.py` — update imports; AIAgentHealthCheckResponse, AIAgentDecisionListResponse, AIAgentDecisionLog, AIAgentStatusSummary
- [x] T066 [US3] Update `ai-agent/src/models/__init__.py` — add AIAgentHealthCheck to exports
- [x] T067 [US3] Update `ai-agent/src/api/v1/automation/__init__.py` — ensure health and agent_status sub-routers are included (if not already from T057)
- [x] T068 [US3] Verify independence: stop AI-agent, confirm `backend/` on port 8001 still starts and serves manual invoice endpoints without errors; main backend `/health` endpoint reports only main backend status (not AI-agent)

**Checkpoint**: AI-agent health monitoring functional. Main backend independence verified.

---

## Phase 6: User Story 4 - Frontend Seamlessly Communicates with Both Backends (Priority: P1)

**Goal**: Frontend routes automation API calls to AI-agent URL, all other calls to main backend URL. Users see no visible difference.

**Independent Test**: Configure frontend with both backend URLs. Login. Create manual invoice — verify network tab shows request to main backend URL. Navigate to automation dashboard — verify network tab shows requests to AI-agent URL. Upload automation Excel — verify request goes to AI-agent. Print manual invoice — verify PDF request to main backend.

### Implementation for User Story 4

- [x] T069 [US4] Update `frontend/src/services/automationApi.ts` — change `API_BASE_URL` from `NEXT_PUBLIC_API_BASE_URL` to `NEXT_PUBLIC_AI_AGENT_API_URL` with fallback `http://localhost:8002/api/v1`; update CSRF token retrieval to use AI-agent-specific cookie/storage key (scope per backend URL)
- [x] T070 [US4] Update `frontend/src/lib/api.ts` — add per-backend CSRF token management: store separate CSRF tokens for main backend and AI-agent; update `fetchWithAuth()` to attach correct CSRF token based on request destination
- [x] T071 [US4] Update `frontend/src/contexts/UploadSessionContext.tsx` — ensure polling calls `automationApi.getUploadStatus()` which now points to AI-agent URL (no code change needed if T069 is correct, but verify)
- [x] T072 [US4] Update `frontend/.env.local` — add `NEXT_PUBLIC_AI_AGENT_API_URL=http://localhost:8002/api/v1` alongside existing `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_BACKEND_URL`
- [x] T073 [US4] Update `frontend/next.config.js` — add proxy rewrite rule for AI-agent if needed (or ensure direct CORS access from browser to AI-agent works); verify CSP `connect-src` includes AI-agent URL
- [x] T074 [US4] Update `frontend/src/app/(protected)/automation/dashboard/page.tsx` — if unified invoice history is shown, implement frontend merge: fetch manual invoices from main backend, automation invoices from AI-agent, merge and sort by date for display
- [x] T075 [US4] Run frontend validation: `cd frontend && npm run dev` — confirm app starts on port 3000 without errors; all pages load; no console errors about API connectivity

**Checkpoint**: Frontend routes correctly — manual operations to main backend, automation to AI-agent. Unified experience preserved.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, and documentation

- [x] T076 [P] Run full quickstart.md validation checklist: start both backends + frontend, execute all verification items (login, manual invoice CRUD, manual Excel upload, automation Excel upload, automation dashboard, PDF generation, health checks, independence test)
- [x] T077 Verify zero cross-imports: `grep -r "from backend" ai-agent/src/` returns no results; `grep -r "from ai-agent" backend/src/` returns no results (SC-007)
- [x] T078 Verify no automation files remain in backend: `ls backend/src/api/v1/automation/ 2>/dev/null` returns "No such file"; `ls backend/src/models/automation_* 2>/dev/null` returns "No such file" (SC-001)
- [x] T079 [P] Update any remaining import paths in ai-agent/ that reference `src.` to use `ai-agent.src.` — run `grep -r "from src\." ai-agent/src/` and fix any occurrences
- [x] T080 [P] Run backend test suite: `cd backend && uv run pytest` — confirm all existing tests pass with automation code removed
- [x] T081 Run `uv sync` in both backend/ and ai-agent/ to generate uv.lock files

**Checkpoint**: All success criteria from spec verified. Services ready for independent deployment.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) — BLOCKS US2 and US3
- **User Story 1 (Phase 3)**: Can start in PARALLEL with Phase 2 — US1 modifies backend, Phase 2 builds AI-agent foundational (different directories)
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion — AI-agent must have settings, DB, middleware before routes can be added
- **User Story 3 (Phase 5)**: Depends on US2 (Phase 4) — needs AI-agent infrastructure + models/schemas updated
- **User Story 4 (Phase 6)**: Depends on US2 (Phase 4) — needs AI-agent endpoints running to configure frontend routing. Can partially start earlier (env vars, config)
- **Polish (Phase 7)**: Depends on ALL user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent — modifies backend only, does not require AI-agent
- **User Story 2 (P1)**: Depends on Foundational (Phase 2) — needs AI-agent core infrastructure
- **User Story 3 (P2)**: Depends on US2 (Phase 4) — builds on AI-agent models, schemas, and router
- **User Story 4 (P1)**: Depends on US2 (Phase 4) — needs AI-agent endpoints for routing verification

### Within Each User Story

- Models → Schemas → Services → API Routes → Integration
- Copy/move files first, then update imports
- Container files (__init__.py, main.py) after their contents exist

### Parallel Opportunities

**Phase 1 + Phase 2 + US1 can all run concurrently:**
```
Developer A: T001-T006 (Setup: ai-agent skeleton, pyproject.toml, Dockerfile)
Developer B: T007-T017 (Foundational: ai-agent settings, DB, middleware, main.py)
Developer C: T018-T031 (US1: Clean backend, remove automation code)
```

**Phase 4 (US2) can be parallelized heavily:**
```
Models group:    T032-T036 (5 model files — all independent)
Schemas group:   T037-T040 (3 schema files + __init__ — all independent)
Services group:  T041-T051 (8 service files + assets — all independent)
Routes group:    T052-T060 (5 route files + __init__ files — all independent)
```

**Phase 5 (US3) can run in parallel with US4:**
```
Developer A: T062-T068 (Health endpoints)
Developer B: T069-T075 (Frontend routing)
```

---

## Parallel Example: User Story 2 (AI-Agent Build)

```bash
# Launch ALL model tasks together:
Task: "Copy automation_base.py → ai-agent/src/models/"
Task: "Copy automation_invoice.py → ai-agent/src/models/"
Task: "Copy automation_log.py → ai-agent/src/models/"
Task: "Copy excel_upload_session.py → ai-agent/src/models/"
Task: "Create ai-agent/src/models/__init__.py"

# Launch ALL shared service copies together:
Task: "Copy validation_service.py → ai-agent/src/services/"
Task: "Copy fbr_client.py → ai-agent/src/services/"
Task: "Copy fbr_service.py → ai-agent/src/services/"

# Launch ALL automation service moves together:
Task: "Copy automation_service.py → ai-agent/src/services/"
Task: "Copy excel_service.py → ai-agent/src/services/"
Task: "Copy file_management_service.py → ai-agent/src/services/"
Task: "Copy background_validation_service.py → ai-agent/src/services/"
Task: "Copy excel_validator.py → ai-agent/src/utils/"
Task: "Create ai-agent/src/services/pdf_service.py"

# Launch ALL route file moves together:
Task: "Copy excel.py → ai-agent/src/api/v1/automation/"
Task: "Copy dashboard.py → ai-agent/src/api/v1/automation/"
Task: "Copy retry.py → ai-agent/src/api/v1/automation/"
Task: "Copy file_management.py → ai-agent/src/api/v1/automation/"
Task: "Copy pdf.py → ai-agent/src/api/v1/automation/"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Start Phase 3: US1 — Clean Backend (T018-T031)
3. **STOP and VALIDATE**: Main backend runs clean, all manual operations work
4. Deploy cleaned backend → FBR audit passes

### Incremental Delivery

1. Complete Setup + Foundational (Phase 1 + 2) → AI-agent infrastructure ready
2. Complete US1 (Phase 3) → Clean backend deployed (FBR compliance achieved!)
3. Complete US2 (Phase 4) → AI-agent serves automation endpoints
4. Complete US3 (Phase 5) → Health monitoring available
5. Complete US4 (Phase 6) → Frontend unified experience
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With 3 developers:

1. **Together**: Complete Phase 1 Setup (T001-T006)
2. **Parallel**:
   - Developer A: Phase 3 — US1 Clean Backend (T018-T031)
   - Developer B: Phase 2 — AI-agent Foundational (T007-T017)
   - Developer C: Phase 4 models/schemas prep (T032-T040, can start copying files)
3. **After Phase 2 done**:
   - Developer B + C: Phase 4 — US2 AI-Agent Build (T041-T061, heavily parallelizable)
4. **After US2 done**:
   - Developer A: Phase 5 — US3 Health (T062-T068)
   - Developer B: Phase 6 — US4 Frontend (T069-T075)
5. **Together**: Phase 7 — Polish & Validation (T076-T081)

---

## Notes

- [P] tasks = different files, no dependencies — safe to run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Files being "copied" from backend → ai-agent require import path updates (from `src.` to `ai-agent.src.`) after copying
- The existing backend code serves as the source of truth until files are successfully moved and verified
- Commit after each phase or logical group
- Stop at any checkpoint to validate story independently
- US1 (backend cleanup) and US2 (AI-agent build) operate on different directories — no merge conflicts
- The `automation_enabled` flag on User model stays in backend (user attribute, not automation code)
- Both services share the same JWT secret — configure identical AUTH_JWT_SECRET in both .env files
