# Research: Separate AI-Agent from Main Backend

**Feature**: 001-separate-ai-agent  
**Date**: 2026-05-13

## 1. Shared Code Strategy: Duplication vs. Shared Library

**Decision**: Duplicate shared services into ai-agent/ rather than extract a shared library.

**Rationale**:
- The user explicitly stated "deploy backend and ai-agent separately" — a shared library would require a third package/deployable, adding complexity
- The shared services (FBR validation, FBR client) are stable, FBR-spec-mandated implementations that change only when FBR updates its specification
- Backend-to-backend communication (e.g., ai-agent calling main backend for validation) introduces network latency, failure modes, and tight coupling that violates the independent deployability goal
- A shared library (`shared/` or `common/`) would need its own CI/CD, versioning, and packaging — overkill for ~3 stable files
- Duplication is the simplest approach that meets FBR compliance: when FBR audits the `backend/` folder, zero automation code exists there

**Alternatives considered**:
- **Shared pip-installable package**: Rejected — adds packaging complexity, versioning overhead, and doesn't materially reduce risk since the shared code is stable
- **Backend-to-backend API calls**: Rejected — creates runtime coupling, adds network failure modes, violates SC-006 (main backend must work with AI-agent stopped)
- **Git submodules**: Rejected — adds repository complexity; the shared code is too small to justify

**Mitigation for code drift**: The `specs/001-separate-ai-agent/` documentation records which files are duplicated. Future FBR spec updates must update both copies.

## 2. Manual Excel Upload Decoupling

**Decision**: Extract manual-only Excel methods from `ExcelService` into a lightweight `ManualExcelHelper` in `backend/src/utils/`.

**Rationale**:
- Confirmed via code analysis: `generate_manual_excel_template()` and `parse_excel_for_manual_invoice()` do NOT use `self.db` (automation DB) — they operate purely in memory with pandas DataFrames
- The `automation_db` is passed to `ExcelService()` constructor but unused by manual methods
- Extracting these methods removes the last `get_automation_db` dependency from `invoices.py`
- The full `ExcelService` (with automation methods) moves to ai-agent/

**Alternatives considered**:
- **Keep stripped-down ExcelService in backend**: Rejected — confusing to have two classes named ExcelService
- **Rewrite manual methods from scratch**: Rejected — existing code is tested and working

## 3. Authentication & Session Sharing

**Decision**: Both backends use identical `AuthMiddleware` with the same `auth_jwt_secret`. Users login through the main backend only; the AI-agent validates JWT tokens issued by the main backend.

**Rationale**:
- The auth middleware code is small (~100 lines) — duplication is acceptable
- JWT-based auth with shared secret means a token from one backend is valid for the other
- AI-agent does NOT expose its own `/auth/login` endpoint — all authentication flows through main backend
- This matches the current architecture where a single JWT secret is used

**Alternatives considered**:
- **AI-agent with its own login**: Rejected — duplicates user management, confusing UX
- **OAuth2 proxy in front of both**: Rejected — over-engineering for two services behind same auth

## 4. CSRF Token Management

**Decision**: Independent CSRF per backend (selected in spec clarification). Each backend issues and validates its own CSRF tokens with identical configuration. Frontend manages separate tokens.

**Rationale**:
- Both services use `fastapi-csrf-protect` with the same configuration pattern
- Frontend's `automationApi.ts` already reads CSRF token from cookie/storage — just needs to scope it per backend URL
- Independent CSRF avoids cross-origin token sharing issues and keeps each service's security boundary clean

**Alternatives considered**:
- **Shared CSRF secret**: Rejected — tokens include host/domain binding; sharing secrets doesn't make tokens portable
- **Disable CSRF for AI-agent**: Rejected — violates Security by Design principle; internal services still need CSRF protection

## 5. Automation PDF Generation

**Decision**: Create a dedicated `pdf_service.py` in ai-agent/ that works directly with `AutomationInvoice` objects (JSON-based invoice_data), rather than depending on the main backend's `PDFService` which expects structured `Invoice` ORM model.

**Rationale**:
- The main backend's `PDFService.generate_invoice_pdf()` takes `Invoice` (structured columns) but automation invoices store data in `invoice_data` JSON
- The automation `pdf.py` currently handles both AutomationInvoice and Invoice — after separation, it only handles AutomationInvoice
- The PDF layout (FBR logo, QR code, line items, totals) is identical — only the data extraction differs
- The ai-agent needs its own assets directory with `fbr_logo.png` and `NotoSansArabic-Regular.ttf`

**Alternatives considered**:
- **Convert AutomationInvoice to Invoice-like dict before PDF**: Rejected — adds unnecessary indirection; simpler to read directly from invoice_data JSON
- **Keep PDF generation in main backend, call via API**: Rejected — violates SC-006 (AI-agent should work independently)

## 6. Cross-Database Transfer Flow

**Decision**: The `TransferService` (defined but not yet actively called in codebase) is excluded from the initial separation scope. The automation-to-main transfer concern is deferred.

**Rationale**:
- Code analysis shows `TransferService` is defined in `transfer_service.py` but not imported/called anywhere — it appears to be future/planned code
- Automation invoices currently stay in the automation DB throughout their lifecycle
- When transfer is implemented, it will be an API call from AI-agent to main backend (or a background job in AI-agent that calls main backend's invoice creation endpoint)
- This doesn't block the separation since no active transfer flow exists

**Alternatives considered**:
- **Implement transfer now**: Rejected — out of scope for this separation; adds risk
- **Remove TransferService entirely**: Considered but not done — it may be needed later

## 7. Frontend API Routing Strategy

**Decision**: Single frontend with per-service API client instances. `automationApi.ts` uses `NEXT_PUBLIC_AI_AGENT_API_URL`. All other services use `NEXT_PUBLIC_API_BASE_URL`.

**Rationale**:
- The frontend already has a clean separation: `automationApi.ts` (24 methods) vs. `api.ts`/`api-client.ts` (all other endpoints)
- Only `automationApi.ts` needs URL change — all other API clients unchanged
- Next.js rewrites proxy can be configured for both backends
- No need for API gateway or BFF pattern — direct calls from browser to both backends with CORS configured

**Alternatives considered**:
- **BFF (Backend for Frontend)**: Rejected — adds another service to maintain; over-engineering
- **API Gateway routing by path**: Rejected — requires infrastructure change (nginx, Traefik); not available in Hugging Face Spaces deployment

## 8. Scheduler Architecture

**Decision**: Main backend scheduler continues running auto-posting job (posts main Invoice records to FBR). AI-agent gets its own scheduler for automation-specific jobs (expired invoice cleanup, log retention cleanup, AI agent health checks).

**Rationale**:
- The auto-posting job in `scheduler.py` queries `User` and `Invoice` (main DB models) — it operates entirely on the main database
- Automation-specific scheduled tasks (background validation, cleanup) move to AI-agent
- Each service's scheduler is independently manageable — AI-agent downtime doesn't affect main backend auto-posting

## 9. Environment Configuration

**Decision**: Each service has its own `.env` file. The AI-agent has:
- `DATABASE_URL` (automation DB)
- `AUTH_JWT_SECRET` (same value as main backend)
- `FBR_SANDBOX_BASE_URL`, `FBR_PRODUCTION_BASE_URL`, `FBR_API_KEY`, `FBR_CLIENT_ID` (same as main backend)
- `ANTHROPIC_API_KEY` (AI agent specific)
- `CSRF_SECRET` (can be same or different from main backend)
- `ALLOWED_ORIGINS` (frontend URL)
- Automation scheduling parameters (transfer_schedule, cleanup_schedule)

The main backend removes: `AUTOMATION_DATABASE_URL`, `ANTHROPIC_API_KEY` (if not used elsewhere), automation schedule parameters.

## 10. Package Management

**Decision**: Both services use `uv` as the exclusive Python package and project manager. Each service has its own `pyproject.toml` with service-specific dependencies and its own `uv.lock` file.

**Rationale**:
- `uv` is 10-100x faster than pip for dependency resolution and installation
- Consistent with the existing backend which already uses `uv` (has `pyproject.toml` and `uv.lock`)
- `uv run` provides reproducible execution across both services
- Each service's `pyproject.toml` declares only its needed dependencies (no cross-contamination)

## 11. Deployment Strategy

**Decision**: Two separate Hugging Face Spaces (or equivalent) — one for main backend, one for AI-agent. Or two separate Docker containers on same host. Each has its own health check endpoint. Dockerfiles use multi-stage builds with `uv` for fast, reproducible builds.

**Rationale**:
- Independent scaling: AI-agent may need different resources than main backend
- Independent deployment: can update one without affecting the other
- FBR audit: main backend deployment is clean of automation code
- SC-006 validated: main backend runs with AI-agent stopped
