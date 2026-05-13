# Feature Specification: Separate AI-Agent (Automation) from Main Backend

**Feature Branch**: `001-separate-ai-agent`  
**Created**: 2026-05-13  
**Status**: Draft  
**Input**: User description: "Separate automation (AI-agent) code from main backend into a standalone ai-agent/ directory for FBR compliance. The main backend handles current/past-date manual invoices. The ai-agent handles future-date Excel-uploaded automation invoices. Both databases already exist separately. All functionality must remain the same after separation. Frontend will call two separate backends."

## Clarifications

### Session 2026-05-13

- Q: How should the unified invoice history work after separation, given the main backend can no longer query the automation database? → A: Frontend merges — the main backend returns only manual invoices from its `/invoices/unified-history` endpoint, and the frontend calls both backends (main + AI-agent) and merges/sorts the combined results for display.
- Q: How should CSRF protection work across two separate backends? → A: Independent CSRF — each backend issues and validates its own CSRF tokens. The frontend manages two separate tokens (one per backend). Both backends use identical CSRF configuration (same secret, same cookie settings).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Portal Operator Uses Manual Invoices Normally (Priority: P1)

A portal operator logs into the system and performs all standard invoice operations — creating manual invoices, viewing invoice history, downloading Excel templates for bulk manual upload, uploading manual Excel files, printing PDFs, and posting invoices to FBR. All of these operations must work exactly as they did before the separation, with no visible changes to the user.

**Why this priority**: Manual invoice operations are the core of the business (current and past-date invoices). If these break, the business cannot operate. This is also what FBR audits — so the backend serving these must be clean of any future-date automation logic.

**Independent Test**: Can be fully tested by logging into the main backend and performing the complete manual invoice lifecycle (create → validate → post to FBR → print PDF) without the AI-agent service even running. Delivers a fully functional FBR invoice portal for current-date invoices.

**Acceptance Scenarios**:

1. **Given** a logged-in user on the main backend, **When** they create a manual invoice with valid data, **Then** the invoice is saved to the main database and appears in their invoice history.
2. **Given** a logged-in user on the main backend, **When** they download the manual Excel template, **Then** they receive an Excel file with columns for manual invoice fields (without scheduled_date/scheduled_time).
3. **Given** a logged-in user on the main backend, **When** they upload a valid manual Excel file, **Then** all rows are parsed and invoices are created in the main database.
4. **Given** a logged-in user on the main backend with auto-posting enabled, **When** the scheduler runs, **Then** their validated manual invoices are automatically posted to FBR.
5. **Given** a logged-in user on the main backend, **When** they print a transferred manual invoice, **Then** a PDF with FBR logo and QR code is generated successfully.

---

### User Story 2 - Automation User Uploads Future-Date Invoices via AI-Agent (Priority: P1)

A user with automation access uploads an Excel file containing future-dated invoices through the automation dashboard. The file is processed by the AI-agent service independently of the main backend. The user can view the processing status, see validated/failed counts, and manage automation invoices (retry, pause, resume, block, delete).

**Why this priority**: The automation path for future-dated invoices is equally critical to the business. Without it, users cannot bulk-schedule future invoices. This service must be fully isolated in its own deployable unit so that FBR auditing the main backend finds no trace of future-date processing.

**Independent Test**: Can be fully tested by pointing the frontend to the AI-agent service and performing the complete automation lifecycle (upload Excel → monitor progress → manage invoices → print PDFs) without the main backend needing any automation code. Delivers a fully functional AI-agent for future-date invoice processing.

**Acceptance Scenarios**:

1. **Given** a user with automation access, **When** they upload an Excel file with future-dated invoices to the AI-agent, **Then** the file is accepted, an upload session is created in the automation database, and validation begins.
2. **Given** an active upload session, **When** the user polls for status, **Then** they see real-time progress (processed rows, validated/failed/expired counts).
3. **Given** validated automation invoices, **When** the user views the automation dashboard, **Then** they see all invoices with status badges, filtering, and pagination.
4. **Given** a failed automation invoice, **When** the user clicks retry, **Then** the invoice is re-validated and re-submitted for processing.
5. **Given** multiple automation invoices, **When** the user performs bulk actions (pause, resume, delete, block), **Then** all selected invoices are updated accordingly.
6. **Given** a transferred automation invoice, **When** the user clicks print, **Then** a PDF is generated from the AI-agent service.

---

### User Story 3 - Administrator Manages AI-Agent Health (Priority: P2)

An administrator monitors the health of the AI-agent service independently. They can view agent status, processing backlogs, FBR API connectivity, and system resource usage. If the AI-agent goes down, the main backend continues operating normally for manual invoices.

**Why this priority**: Operational visibility into the AI-agent is important but the system remains functional for manual invoices even without it. Monitoring can be added after the core separation is complete.

**Independent Test**: Can be fully tested by accessing the AI-agent health endpoints directly. Delivers operational insight into the AI-agent service status.

**Acceptance Scenarios**:

1. **Given** the AI-agent is running, **When** an admin checks health status, **Then** they see overall status, pending/failed invoice counts, FBR API latency, database latency, and system resource metrics.
2. **Given** the AI-agent is down, **When** a user performs manual invoice operations on the main backend, **Then** all manual operations continue to work without errors.

---

### User Story 4 - Frontend Seamlessly Communicates with Both Backends (Priority: P1)

The frontend application routes API calls to the correct backend: manual invoice operations go to the main backend, automation operations go to the AI-agent backend. Users see no difference — the UI works exactly as before.

**Why this priority**: The frontend is the user's only interface. If it can't talk to both backends correctly, the separation is invisible in code but broken in practice.

**Independent Test**: Can be fully tested by configuring the frontend with both backend URLs and verifying each feature area (manual invoices, automation dashboard, Excel upload) communicates with the correct backend. Delivers a unified user experience across two backend services.

**Acceptance Scenarios**:

1. **Given** the frontend is configured with both backend URLs, **When** a user creates a manual invoice, **Then** the API call goes to the main backend (not the AI-agent).
2. **Given** the frontend is configured with both backend URLs, **When** a user uploads an automation Excel file, **Then** the API call goes to the AI-agent backend (not the main backend).
3. **Given** the frontend is configured with both backend URLs, **When** a user views the automation dashboard, **Then** dashboard stats and invoice lists are fetched from the AI-agent.
4. **Given** either backend is unreachable, **When** the user accesses features served by the other backend, **Then** those features continue to work independently.

---

### Edge Cases

- What happens when the AI-agent is unreachable but the user visits the automation dashboard? The frontend should display an appropriate error message (e.g., "Automation service is currently unavailable").
- What happens when a user with `automation_enabled = false` tries to access automation pages? The frontend should redirect them (same behavior as before separation).
- How does the manual Excel upload work when it previously shared code with automation Excel processing? The manual upload only needs template generation and parsing (no automation DB), so these lightweight methods stay in the main backend.
- What happens to the unified invoice history endpoint that previously combined manual and automation invoices? After separation, the main backend's `/invoices/unified-history` returns only manual invoices. The frontend fetches from both backends (main + AI-agent) and merges/sorts the combined results for display.
- How are shared dependencies (FBR validation rules, FBR API client) kept in sync between both backends? These are stable, FBR-spec-mandated implementations that change only when FBR updates its specification.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The main backend MUST NOT contain any automation-specific code (routes, services, models, schemas) for processing future-dated invoices.
- **FR-002**: The AI-agent MUST be a standalone web service with its own application entry point, configuration, and database connection.
- **FR-003**: The AI-agent MUST serve all automation endpoints under the same URL paths as before (`/api/v1/automation/*`) so the frontend transition is minimal.
- **FR-004**: The main backend MUST continue to serve all manual invoice endpoints (`/api/v1/invoices/*`, `/api/v1/auth/*`, `/api/v1/dashboard/*`, `/api/v1/fbr/*`, etc.) without change.
- **FR-005**: The frontend MUST direct automation API calls to the AI-agent backend URL and all other API calls to the main backend URL.
- **FR-006**: The main backend's manual Excel upload MUST NOT depend on the automation database or any automation services.
- **FR-007**: The AI-agent MUST include copies of shared services (FBR validation, FBR client) that are necessary for its independent operation.
- **FR-008**: Both backends MUST maintain the same authentication middleware so users authenticate once and their session is valid for both services.
- **FR-015**: Each backend MUST manage its own CSRF protection independently. The AI-agent MUST include CSRF middleware with the same configuration as the main backend. The frontend MUST handle separate CSRF tokens for each backend.
- **FR-009**: The AI-agent MUST have its own scheduler for automation-specific background jobs (cleanup, expiration) independent of the main backend's scheduler.
- **FR-010**: The main backend's scheduler MUST continue running auto-posting jobs that post validated manual invoices to FBR, unaffected by the AI-agent's presence or absence.
- **FR-011**: The AI-agent MUST expose health check endpoints for monitoring its operational status independently.
- **FR-012**: The main backend's root `/health` endpoint MUST NOT report AI-agent status (each service reports its own health).
- **FR-013**: All existing automation features (Excel upload with progress tracking, invoice management with bulk actions, PDF generation, retry, pause/resume, block/unblock, upload session management) MUST work identically through the AI-agent.
- **FR-014**: The `automation_invoice_id` field on manual invoices (linking to their automation origin) MUST become optional/nullable since cross-database references are no longer directly queryable from the main backend.

### Key Entities

- **Manual Invoice** (main database): Current and past-date invoices created through the portal UI or manual Excel upload. Exists in the main backend database. No future dates permitted.
- **Automation Invoice** (automation database): Future-dated invoices uploaded via Excel through the automation system. Exists in the AI-agent's separate database. Contains scheduling fields (scheduled_date, scheduled_time) and status tracking through the automation pipeline.
- **Upload Session** (automation database): Tracks an Excel file upload from submission through validation completion. Owned by the AI-agent service.
- **AI Agent Health Check** (automation database): Periodic snapshots of AI-agent operational metrics, stored by the AI-agent itself.
- **Automation Log** (automation database): Audit trail of all actions performed on automation invoices (validate, submit, retry, block, pause, resume, etc.).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The main backend directory contains zero files related to automation (no automation routes, models, schemas, or services). Verifiable by file audit.
- **SC-002**: The AI-agent directory is a fully self-contained service that starts and serves all automation endpoints without importing from the backend directory.
- **SC-003**: All 24 existing automation API endpoints return identical responses when called at the AI-agent URL as they did when called at the main backend URL.
- **SC-004**: Manual invoice operations (create, list, update, Excel upload, PDF print, FBR post) function with 100% feature parity after separation.
- **SC-005**: The frontend builds and runs without errors, correctly routing automation requests to the AI-agent and all other requests to the main backend.
- **SC-006**: The main backend continues to function even when the AI-agent service is completely stopped.
- **SC-007**: Zero cross-imports exist from the main backend to the AI-agent directory, and zero cross-imports from the AI-agent to the main backend directory.

## Assumptions

- The two databases (main and automation) are already separate and will remain so. No database migration or consolidation is needed.
- Both backends will share the same authentication secret so that a session token issued by the main backend is accepted by the AI-agent.
- The FBR validation rules and FBR API client implementations are stable and rarely change. Duplicating these into the AI-agent is acceptable.
- Manual Excel upload methods (`generate_manual_excel_template`, `parse_excel_for_manual_invoice`) that currently live in `ExcelService` do not actually use the automation database — they can be extracted into lightweight helpers in the main backend.
- The unified invoice history endpoint on the main backend returns only manual invoices. The frontend fetches from both backends and merges/sorts results for a combined view.
- The frontend will be configured with two environment variables (`NEXT_PUBLIC_API_BASE_URL` for main backend, `NEXT_PUBLIC_AI_AGENT_API_URL` for AI-agent).
