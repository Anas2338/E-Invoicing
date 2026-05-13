# Quickstart: Running Separated Services

**Feature**: 001-separate-ai-agent  
**Date**: 2026-05-13

## Prerequisites

- Python 3.11+
- Node.js 20+
- Two Neon PostgreSQL databases (already provisioned — main and automation)
- `uv` package manager (required — both services use uv for dependency management)

## 1. Main Backend (Manual Invoices)

```bash
cd backend/

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with main database URL, JWT secret, FBR credentials

# Run
uv run uvicorn src.main:app --port 8001 --reload
```

**Serves**: `http://localhost:8001/api/v1/`
- `/invoices/*` — Manual invoice CRUD
- `/auth/*` — Authentication
- `/dashboard/*` — User dashboard
- `/fbr/*` — FBR integration
- `/admin/*` — Admin operations
- `/profile/*` — User profile
- `/health` — Health check (main backend only)

## 2. AI-Agent (Automation)

```bash
cd ai-agent/

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with automation database URL, JWT secret (same as main), FBR credentials

# Run
uv run uvicorn src.main:app --port 8002 --reload
```

**Serves**: `http://localhost:8002/api/v1/automation/`
- All 24 automation endpoints under `/automation/*`

## 3. Frontend

```bash
cd frontend/

# Install dependencies
npm install

# Configure environment
# .env.local:
#   NEXT_PUBLIC_API_BASE_URL=http://localhost:8001/api/v1
#   NEXT_PUBLIC_AI_AGENT_API_URL=http://localhost:8002/api/v1

# Run
npm run dev
```

**Serves**: `http://localhost:3000`

## Verification Checklist

- [ ] Main backend starts without errors on port 8001
- [ ] AI-agent starts without errors on port 8002
- [ ] Frontend starts without errors on port 3000
- [ ] Login works (authenticates against main backend)
- [ ] Create manual invoice → appears in history
- [ ] Download manual Excel template → valid `.xlsx` file
- [ ] Upload manual Excel → invoices created in main DB
- [ ] Navigate to Automation → Dashboard → stats load from AI-agent
- [ ] Upload automation Excel → session created, progress tracked
- [ ] Automation invoice management (retry, pause, resume, block, delete) works
- [ ] Print automation invoice PDF → valid PDF with FBR logo + QR
- [ ] Stop AI-agent → main backend continues working
- [ ] Stop main backend → automation dashboard shows appropriate error

## Environment Variables Reference

### Main Backend (`backend/.env`)
```
DATABASE_URL=postgresql://...       # Main database
AUTH_JWT_SECRET=<shared-secret>     # Same as AI-agent
ENCRYPTION_KEY=<key>
FBR_SANDBOX_BASE_URL=https://...
FBR_PRODUCTION_BASE_URL=https://...
FBR_API_KEY=<key>
FBR_CLIENT_ID=<id>
ALLOWED_ORIGINS=http://localhost:3000
CSRF_SECRET=<secret>
LOG_LEVEL=INFO
DB_ECHO=False
DRY_RUN=False
```

### AI-Agent (`ai-agent/.env`)
```
DATABASE_URL=postgresql://...       # Automation database
AUTH_JWT_SECRET=<shared-secret>     # Same as main backend
ENCRYPTION_KEY=<key>
FBR_SANDBOX_BASE_URL=https://...
FBR_PRODUCTION_BASE_URL=https://...
FBR_API_KEY=<key>
FBR_CLIENT_ID=<id>
ANTHROPIC_API_KEY=<key>
ALLOWED_ORIGINS=http://localhost:3000
CSRF_SECRET=<secret>
LOG_LEVEL=INFO
DB_ECHO=False
DRY_RUN=False
TRANSFER_SCHEDULE_HOUR=18
TRANSFER_SCHEDULE_MINUTE=0
CLEANUP_SCHEDULE_HOUR=2
CLEANUP_SCHEDULE_MINUTE=0
CLEANUP_RETENTION_DAYS=2
AUTOMATION_LOG_RETENTION_DAYS=90
```

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001/api/v1
NEXT_PUBLIC_BACKEND_URL=http://localhost:8001
NEXT_PUBLIC_AI_AGENT_API_URL=http://localhost:8002/api/v1
```
