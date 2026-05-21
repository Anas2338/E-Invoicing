# CLAUDE.md — FBR E-Invoicing Portal

## Project Overview

Digital invoicing portal for Pakistan's Federal Board of Revenue (FBR) e-invoicing system. Enables businesses to create, validate, and submit invoices to FBR's digital invoicing API, with bulk Excel upload automation and AI-agent-powered scheduling.

**Domain:** `taxntec.com` (production)
**FBR API:** `https://gw.fbr.gov.pk/di_data/v1/di`

## Architecture

Three-service architecture:

| Service | Path | Stack |
|---|---|---|
| **Frontend** | `frontend/` | Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS 4, shadcn/ui |
| **Backend** | `backend/` | FastAPI (Python 3.11+), SQLModel, PostgreSQL (Neon), Alembic |
| **AI Agent** | `ai-agent/` | FastAPI, SQLModel, Anthropic SDK — standalone orchestrator for automation |

The AI agent shares the backend's database models by importing from `backend/src/models/`. It runs as a separate Docker container on port 8002.

**Automation separation:** Automation tables (`automation_invoice`, `excel_upload_session`, `automation_log`, `ai_agent_health_check`) use a separate database from the main backend. Invoices transfer from automation DB to main DB during auto-posting.

## Tech Stack Quick Reference

- **State management:** TanStack React Query 5, React Hook Form 7 + Zod 4
- **Auth:** JWT (python-jose + passlib/bcrypt), CSRF protection (fastapi-csrf-protect)
- **PDF:** ReportLab + qrcode + Pillow
- **Excel:** Pandas + OpenPyXL
- **Scheduling:** APScheduler (5-min cycles in AI agent)
- **Rate limiting:** slowapi
- **Infrastructure:** Docker Compose, Nginx reverse proxy, GitHub Actions CI/CD

## Project Principles (from constitution)

1. **Compliance-First** — FBR spec is the single source of truth; all invoice data must conform
2. **Security by Design** — JWT auth, CSRF, rate limiting, row-level security, encrypted secrets
3. **Spec-Driven Implementation** — Use SDD workflow (`/sp.specify`, `/sp.plan`, `/sp.tasks`, `/sp.implement`)
4. **Data Integrity** — All FBR responses stored for audit; idempotency protection on submissions
5. **Environment Isolation** — Separate sandbox (`fbr_sandbox`) and production (`fbr_production`) credentials per user

## Key Backend Routes

All prefixed with `/api/v1/`:

| Prefix | Purpose |
|---|---|
| `/invoices` | Invoice CRUD, validation, FBR submission, history, bulk PDF |
| `/fbr` | FBR API integration |
| `/auth` | Auth, user profile, FBR credentials, saved items, next invoice number |
| `/profile` | Saved products, saved buyers, invoice numbering settings |
| `/masterdata` | Provinces, UOMs, tax rates (synced from FBR) |
| `/admin` | User management, FBR master data sync |
| `/dashboard` | Dashboard statistics |
| `/notifications` | User notifications |
| `/fbr-reference` | FBR reference data lookup |

**Middleware order:** SecurityHeaders → RequestSizeLimit (10MB) → SessionTimeout (30min) → CSRF → Auth → CORS → RateLimiter

## Key Files

### Frontend
- `frontend/src/lib/api.ts` — API client (fetch wrapper, auth helpers, endpoint functions)
- `frontend/src/lib/api/api-client.ts` — Master data service
- `frontend/src/components/invoices/sale-invoice-form.tsx` — Manual invoice creation form
- `frontend/src/components/profile/SavedItemsSection.tsx` — Saved items management (CRUD, Excel bulk upload)
- `frontend/src/components/profile/InvoiceSettingsSection.tsx` — Invoice numbering settings
- `frontend/src/components/automation/` — Automation dashboard components
- `frontend/src/app/(protected)/` — All authenticated routes

### Backend
- `backend/src/main.py` — App factory, route registration, middleware setup
- `backend/src/models/` — SQLModel definitions for all tables
- `backend/src/api/v1/saved_products.py` — Saved products CRUD + Excel upload
- `backend/src/api/middleware/auth_middleware.py` — JWT auth + `require_authentication` dependency
- `backend/src/api/deps.py` — `get_database_session` dependency
- `backend/src/utils/manual_excel_helper.py` — Excel invoice processing logic

### AI Agent
- `ai-agent/src/agent.py` — Main orchestrator (AIAgent class)
- `ai-agent/src/skills/` — Modular skill classes (priority_scheduler, error_handler, retry_manager, etc.)
- `ai-agent/src/ai_client.py` — AI provider abstraction

## Database Tables (Core)

- `users` — Email, name, role, FBR credentials (sandbox + production), approval status, invoice settings
- `invoices` + `invoice_items` — Manual invoices with line items
- `user_saved_product` — Saved items (item_code, item_name, hs_code, default_uom, default_rate, default_sale_type, transaction_type, SRO info)
- `user_saved_buyer` — Saved buyers (NTN/CNIC, business_name, province, address)
- `fbr_master_data` — Cached FBR reference: provinces, UOMs, tax rates, HS codes
- `automation_invoice` — Bulk-uploaded invoices (separate DB)
- `excel_upload_session` — Upload tracking (separate DB)
- `automation_log` — AI decision logs (separate DB)

## Code Conventions

- **No business logic in frontend components** — logic belongs in backend services
- **Don't invent APIs or data contracts** — verify against FBR spec or existing code
- **Never hardcode secrets** — use `.env` files
- **Prefer smallest viable diff** — don't refactor unrelated code
- **All FBR communication via backend service layer** — frontend never calls FBR directly
- **Use existing patterns** — check existing similar endpoints/components before creating new ones
- **Saved product fields `default_sale_type` and `transaction_type`** store transaction type **names** (e.g., "3rd Schedule Goods"), not codes

## Common Tasks

- **Run backend:** `cd backend && uvicorn src.main:app --reload`
- **Run frontend:** `cd frontend && npm run dev`
- **Run AI agent:** `cd ai-agent && uvicorn src.main:app --port 8002`
- **Database migrations:** `cd backend && alembic upgrade head`
- **Docker deploy:** `./deploy-cicd.sh`

## PHR & ADR Workflow

- PHR records go under `history/prompts/<feature-name>/` (or `general/`)
- PHR template: `.specify/templates/phr-template.prompt.md`
- ADR records go under `history/adr/`
- SDD workflow: `/sp.specify` → `/sp.plan` → `/sp.tasks` → `/sp.implement`
