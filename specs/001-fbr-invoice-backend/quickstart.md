# Quickstart Guide: FBR Invoice Integration Backend

**Feature**: Backend System for FBR Invoice Integration Portal
**Date**: 2026-02-22
**Target Audience**: Developers setting up local development environment

## Prerequisites

### Required Software

- **Python**: 3.11 or higher
- **uv**: 0.5.0+ (Fast Python package manager)
- **PostgreSQL**: 15+ (or Neon PostgreSQL account)
- **Git**: For version control
- **Docker** (optional): For local PostgreSQL if not using Neon

### Required Accounts

- **Neon PostgreSQL**: Create account at https://neon.tech
- **FBR Sandbox**: Obtain sandbox API credentials from FBR
- **Better Auth**: JWT secret key for token verification

## Initial Setup

### 1. Clone Repository

```bash
cd E-Invoicing
git checkout 001-fbr-invoice-backend
```

### 2. Install uv (if not installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: Install via pip
pip install uv
```

### 3. Install Dependencies

```bash
cd backend
uv sync
```

This installs:
- FastAPI 0.115+
- SQLModel 0.0.24+
- httpx 0.28+
- python-jose[cryptography]
- asyncpg (PostgreSQL async driver)
- alembic (database migrations)
- pytest + pytest-asyncio (testing)
- respx (HTTP mocking)

### 4. Configure Environment Variables

Create `.env` file in `backend/` directory:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Database (Neon PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=RS256

# FBR Sandbox
FBR_SANDBOX_VALIDATION_URL=https://esp.fbr.gov.pk:8244/FBR/Production/di_data/v1/di/validateinvoicedata
FBR_SANDBOX_POSTING_URL=https://esp.fbr.gov.pk:8244/FBR/Production/di_data/v1/di/postinvoicedata
FBR_SANDBOX_API_KEY=your-sandbox-api-key

# FBR Production
FBR_PRODUCTION_VALIDATION_URL=https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata
FBR_PRODUCTION_POSTING_URL=https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata
FBR_PRODUCTION_API_KEY=your-production-api-key

# API Configuration
API_V1_PREFIX=/api/v1
```

### 5. Set Up Database

#### Option A: Neon PostgreSQL (Recommended)

1. Create account at https://neon.tech
2. Create new project
3. Copy connection string to `DATABASE_URL` in `.env`
4. Connection string format: `postgresql+asyncpg://user:password@host/database`

#### Option B: Local PostgreSQL with Docker

```bash
# Start PostgreSQL container
docker run -d \
  --name fbr-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=fbr_invoices \
  -p 5432:5432 \
  postgres:15

# Update .env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fbr_invoices
```

### 6. Run Database Migrations

```bash
# Run migrations using uv
uv run alembic upgrade head
```

This creates all tables:
- `invoices`
- `fbr_responses`
- `audit_logs`
- `idempotency_cache`

### 7. Verify Setup

```bash
# Check database connection
uv run python -c "from src.db.session import engine; import asyncio; asyncio.run(engine.connect())"

# Should print: Connection successful
```

## Running the Application

### Development Server

```bash
# Start FastAPI development server
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Server starts at: http://localhost:8000

### API Documentation

Once server is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-22T10:30:00Z"
}
```

## Testing

### Run All Tests

```bash
uv run pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
uv run pytest tests/unit/

# Integration tests only
uv run pytest tests/integration/

# Contract tests only
uv run pytest tests/contract/

# With coverage report
uv run pytest --cov=src --cov-report=html
```

### Run Tests with Verbose Output

```bash
uv run pytest -v -s
```

### Test Database Setup

Tests use a separate test database. Configure in `tests/conftest.py`:

```python
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/fbr_invoices_test"
```

## Common Development Tasks

### Create New Database Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Review generated migration in alembic/versions/
# Edit if needed, then apply:
alembic upgrade head
```

### Rollback Migration

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### Add New Dependency

```bash
# Add production dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Update all dependencies
uv sync --upgrade

# Update lock file
uv lock
```

### Format Code

```bash
# Install formatters (if not already)
uv add --dev black isort

# Format code
uv run black src/ tests/
uv run isort src/ tests/
```

### Lint Code

```bash
# Install linters (if not already)
uv add --dev ruff mypy

# Run linters
uv run ruff check src/ tests/
uv run mypy src/
```

### Generate Test JWT Token

For testing endpoints locally:

```python
# Create test_jwt.py
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"
ALGORITHM = "RS256"

payload = {
    "sub": "test-user-123",
    "production_access": True,
    "exp": datetime.utcnow() + timedelta(hours=1)
}

token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(f"Bearer {token}")
```

Run:
```bash
uv run python test_jwt.py
```

Use token in requests:
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/invoices
```

## Project Structure Overview

```
backend/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration (Pydantic Settings)
│   ├── models/              # SQLModel database models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── api/                 # FastAPI routers
│   │   ├── deps.py          # Shared dependencies
│   │   └── v1/              # API v1 endpoints
│   ├── services/            # Business logic
│   ├── integrations/        # External API clients (FBR)
│   ├── middleware/          # FastAPI middleware
│   └── db/                  # Database utilities
│       ├── session.py       # Async session management
│       └── migrations/      # Alembic migrations
├── tests/
│   ├── conftest.py          # Pytest fixtures
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── contract/            # Contract tests
├── alembic.ini              # Alembic configuration
├── pyproject.toml           # uv project configuration
├── uv.lock                  # uv lock file for reproducible builds
└── .env                     # Environment variables (not in git)
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Implement Changes

- Write code in `src/`
- Write tests in `tests/`
- Update models if needed
- Create migration if schema changed

### 3. Run Tests

```bash
uv run pytest
```

### 4. Format and Lint

```bash
uv run black src/ tests/
uv run isort src/ tests/
uv run ruff check src/ tests/
uv run mypy src/
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: description of changes"
```

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

## Debugging

### Enable Debug Logging

In `.env`:
```bash
LOG_LEVEL=DEBUG
```

Or in code:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Debug Database Queries

Enable SQLAlchemy echo:
```python
# In src/db/session.py
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True  # Prints all SQL queries
)
```

### Debug FastAPI Requests

Use FastAPI's built-in logging:
```python
# In src/main.py
import logging
logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
```

### Interactive Python Shell

```bash
uv run python

>>> from src.db.session import get_session
>>> from src.models.invoice import Invoice
>>> # Test database operations interactively
```

## Troubleshooting

### Issue: Database Connection Failed

**Symptoms**: `asyncpg.exceptions.InvalidPasswordError` or connection timeout

**Solutions**:
1. Verify `DATABASE_URL` in `.env` is correct
2. Check Neon PostgreSQL dashboard for connection string
3. Ensure database is not paused (Neon auto-pauses after inactivity)
4. Test connection: `psql <DATABASE_URL>`

### Issue: Migration Failed

**Symptoms**: `alembic.util.exc.CommandError`

**Solutions**:
1. Check current migration version: `alembic current`
2. Check migration history: `alembic history`
3. Manually fix database schema if needed
4. Rollback and retry: `alembic downgrade -1 && alembic upgrade head`

### Issue: JWT Verification Failed

**Symptoms**: `401 Unauthorized` on all requests

**Solutions**:
1. Verify `JWT_SECRET_KEY` matches Better Auth configuration
2. Check token expiration: decode JWT at https://jwt.io
3. Ensure `JWT_ALGORITHM` matches (RS256 vs HS256)
4. Verify token format: `Bearer <token>`

### Issue: FBR API Timeout

**Symptoms**: `httpx.TimeoutException`

**Solutions**:
1. Check FBR API status (sandbox may be down)
2. Increase timeout in `src/integrations/fbr_client.py`
3. Verify API key is correct
4. Check network connectivity to FBR endpoints

### Issue: Import Errors

**Symptoms**: `ModuleNotFoundError`

**Solutions**:
1. Ensure dependencies are installed: `uv sync`
2. Reinstall dependencies: `uv sync --reinstall`
3. Check Python version: `python --version` (should be 3.11+)
4. Verify virtual environment: `uv venv` to recreate if needed

## Performance Optimization

### Database Connection Pooling

Configure in `src/db/session.py`:
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,        # Number of connections to maintain
    max_overflow=20,     # Additional connections when pool exhausted
    pool_timeout=30,     # Seconds to wait for connection
    pool_recycle=3600    # Recycle connections after 1 hour
)
```

### Query Optimization

Use `selectinload()` for eager loading:
```python
from sqlalchemy.orm import selectinload

stmt = (
    select(Invoice)
    .options(selectinload(Invoice.fbr_responses))
    .where(Invoice.id == invoice_id)
)
```

### Caching

Consider adding Redis for:
- Idempotency cache (instead of PostgreSQL)
- Session storage
- Rate limiting

## Security Best Practices

### 1. Never Commit Secrets

- Add `.env` to `.gitignore`
- Use environment variables for all secrets
- Rotate API keys regularly

### 2. Validate All Inputs

- Use Pydantic schemas for request validation
- Sanitize user inputs
- Validate JWT tokens on every request

### 3. Use HTTPS in Production

- Configure TLS/SSL certificates
- Redirect HTTP to HTTPS
- Use secure cookies

### 4. Rate Limiting

Implement rate limiting middleware:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/v1/invoices")
@limiter.limit("10/minute")
async def list_invoices():
    ...
```

## Next Steps

1. ✅ Complete Phase 1 (Foundation) - Project setup
2. ⏭️ Implement Phase 2 (Data Layer) - Database models
3. ⏭️ Implement Phase 3 (Core APIs) - Invoice CRUD
4. ⏭️ Implement Phase 4 (FBR Validation) - Validation integration
5. ⏭️ Implement Phase 5 (FBR Posting) - Posting integration
6. ⏭️ Implement Phase 6 (Logging & Audit) - Audit trail
7. ⏭️ Implement Phase 7 (Hardening) - Security & performance

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Neon PostgreSQL Documentation](https://neon.tech/docs)
- [FBR Integration Guide](../../docs/FBR_INTEGRATION.md)
- [Project Plan](./plan.md)
- [Data Model](./data-model.md)
- [API Contract](./contracts/openapi.yaml)

## Support

For issues or questions:
1. Check this quickstart guide
2. Review project documentation in `specs/001-fbr-invoice-backend/`
3. Check existing issues in repository
4. Create new issue with detailed description

---

**Last Updated**: 2026-02-23
**Maintainer**: Development Team
