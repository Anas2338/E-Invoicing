# Implementation Plan: Backend System for FBR Invoice Integration Portal

**Branch**: `001-fbr-invoice-backend` | **Date**: 2026-02-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-fbr-invoice-backend/spec.md`

## Summary

Build a secure FastAPI backend service that handles invoice processing, FBR API integration (validation and posting), JWT-based authentication, and comprehensive audit logging. The system enforces strict environment isolation (sandbox/production), implements optimistic locking for concurrency control, and maintains complete audit trails for compliance. All invoice data structures and validation rules are derived from the FBR technical specification.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.115+, SQLModel 0.0.24+, httpx 0.28+, pydantic 2.x, python-jose[cryptography], asyncpg
**Storage**: Neon PostgreSQL (async via asyncpg driver)
**Testing**: pytest, pytest-asyncio, httpx (for async test client), respx (for mocking httpx)
**Target Platform**: Linux server (containerized deployment)
**Project Type**: Web backend (FastAPI REST API)
**Performance Goals**: <3s response time for invoice operations, 50+ concurrent users
**Constraints**: <200ms p95 for database queries, JWT verification on every request, 100% audit coverage
**Scale/Scope**: ~10 API endpoints, 4 database tables, 2 external API integrations (FBR sandbox/production)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance-First Development ✅
- All invoice models derived from FBR technical specification
- Validation rules match FBR spec exactly
- No hardcoded field assumptions outside FBR spec

### Security by Design ✅
- JWT verification middleware on all endpoints
- Row-level data isolation (user_id filtering)
- API key authentication for FBR APIs
- No public routes allowed

### Spec-Driven Implementation ✅
- FBR spec file drives data models and validation schemas
- Generated models fail on spec mismatch
- Single source of truth for field structures

### Data Integrity and Auditability ✅
- Complete audit trail for all FBR interactions
- Invoice state transitions logged
- FBR responses stored unmodified

### Environment Isolation ✅
- Separate configuration for sandbox/production
- Explicit environment selection per invoice
- No configuration mixing

### Architectural Constraints ✅
- Backend: FastAPI only
- ORM: SQLModel only
- Database: Neon PostgreSQL only
- Authentication: Better Auth JWT only
- No business logic in frontend

### API Design Rules ✅
- RESTful conventions with /api/v1/ versioning
- Schema-based contracts (OpenAPI)
- Validation endpoint does NOT post invoices
- Posting endpoint only accepts validated invoices

### Non-Functional Standards ✅
- <3 second response time target
- Concurrent submission support
- FBR validation alignment

**Gate Status**: PASSED - All constitution requirements satisfied

## Project Structure

### Documentation (this feature)

```text
specs/001-fbr-invoice-backend/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Technology research and decisions
├── data-model.md        # Database schema design
├── quickstart.md        # Development setup guide
├── contracts/           # API contracts (OpenAPI)
│   └── openapi.yaml
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration management (Pydantic Settings)
│   ├── models/                    # SQLModel database models
│   │   ├── __init__.py
│   │   ├── invoice.py             # Invoice model with state machine
│   │   ├── fbr_response.py        # FBR API response storage
│   │   ├── audit_log.py           # Audit trail model
│   │   └── idempotency.py         # Idempotency cache model
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── invoice.py             # Invoice DTOs
│   │   ├── fbr.py                 # FBR request/response schemas
│   │   └── auth.py                # JWT token schemas
│   ├── api/                       # FastAPI routers
│   │   ├── __init__.py
│   │   ├── deps.py                # Shared dependencies (auth, db session)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── invoices.py        # Invoice CRUD endpoints
│   │       ├── validation.py      # FBR validation endpoints
│   │       ├── posting.py         # FBR posting endpoints
│   │       └── audit.py           # Audit log endpoints
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── invoice_service.py     # Invoice operations
│   │   ├── fbr_service.py         # FBR API integration
│   │   ├── auth_service.py        # JWT verification
│   │   └── audit_service.py       # Audit logging
│   ├── integrations/              # External API clients
│   │   ├── __init__.py
│   │   └── fbr_client.py          # httpx-based FBR API client
│   ├── middleware/                # FastAPI middleware
│   │   ├── __init__.py
│   │   ├── auth.py                # JWT verification middleware
│   │   └── logging.py             # Request/response logging
│   └── db/                        # Database utilities
│       ├── __init__.py
│       ├── session.py             # Async session management
│       └── migrations/            # Alembic migrations
│           └── versions/
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── unit/                      # Unit tests
│   │   ├── test_invoice_service.py
│   │   ├── test_fbr_service.py
│   │   └── test_auth_service.py
│   ├── integration/               # Integration tests
│   │   ├── test_invoice_api.py
│   │   ├── test_validation_flow.py
│   │   └── test_posting_flow.py
│   └── contract/                  # Contract tests
│       └── test_openapi_spec.py
├── alembic.ini                    # Alembic configuration
├── pyproject.toml                 # uv project configuration
├── uv.lock                        # uv lock file for reproducible builds
└── .env.example                   # Environment variables template
```

**Structure Decision**: Web application structure with clear separation of concerns. API layer (routers) handles HTTP, service layer contains business logic, integration layer manages external APIs, and data layer (models) handles persistence. This aligns with FastAPI best practices and enables independent testing of each layer.

## Complexity Tracking

No constitution violations. All architectural decisions align with project principles.

## Architecture

### 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Middleware Layer                         │  │
│  │  - JWT Verification (every request)                   │  │
│  │  - Request/Response Logging                           │  │
│  │  - CORS (if needed)                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              API Layer (Routers)                      │  │
│  │  /api/v1/invoices     - Invoice CRUD                  │  │
│  │  /api/v1/validate     - FBR validation                │  │
│  │  /api/v1/post         - FBR posting                   │  │
│  │  /api/v1/audit        - Audit logs                    │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Service Layer                            │  │
│  │  InvoiceService   - Business logic                    │  │
│  │  FBRService       - FBR integration orchestration     │  │
│  │  AuthService      - JWT verification                  │  │
│  │  AuditService     - Audit trail management           │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Integration Layer                        │  │
│  │  FBRClient        - httpx async client                │  │
│  │    - Retry logic (5xx, 429)                          │  │
│  │    - Timeout handling                                 │  │
│  │    - API key injection                                │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Data Layer (SQLModel)                    │  │
│  │  Invoice, FBRResponse, AuditLog, Idempotency         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ Neon PostgreSQL  │
                  │  - Async driver  │
                  │  - Connection    │
                  │    pooling       │
                  └──────────────────┘
```

### 2. Environment Separation Design

**Configuration Strategy**: Pydantic Settings with environment-specific variables

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str  # Neon PostgreSQL connection string

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "RS256"

    # FBR Sandbox
    FBR_SANDBOX_VALIDATION_URL: str
    FBR_SANDBOX_POSTING_URL: str
    FBR_SANDBOX_API_KEY: str

    # FBR Production
    FBR_PRODUCTION_VALIDATION_URL: str
    FBR_PRODUCTION_POSTING_URL: str
    FBR_PRODUCTION_API_KEY: str

    # API
    API_V1_PREFIX: str = "/api/v1"

    class Config:
        env_file = ".env"
```

**Endpoint Switching**: Runtime selection based on invoice.environment field

```python
def get_fbr_config(environment: str) -> dict:
    if environment == "sandbox":
        return {
            "validation_url": settings.FBR_SANDBOX_VALIDATION_URL,
            "posting_url": settings.FBR_SANDBOX_POSTING_URL,
            "api_key": settings.FBR_SANDBOX_API_KEY
        }
    elif environment == "production":
        return {
            "validation_url": settings.FBR_PRODUCTION_VALIDATION_URL,
            "posting_url": settings.FBR_PRODUCTION_POSTING_URL,
            "api_key": settings.FBR_PRODUCTION_API_KEY
        }
```

**Safety Measures**:
- Production API key stored separately from sandbox
- User production_access flag checked before allowing production operations
- Environment field immutable after invoice creation
- Audit logs record environment for every FBR call

### 3. Invoice Lifecycle State Machine

**States**: DRAFT → VALIDATED → POSTED / FAILED

**Allowed Transitions**:
```
DRAFT → VALIDATED      (via successful validation)
DRAFT → FAILED         (via validation error)
VALIDATED → POSTED     (via successful posting)
VALIDATED → FAILED     (via posting error)
```

**Invalid Transitions** (raise 400 Bad Request):
- POSTED → any state (immutable)
- FAILED → VALIDATED (must fix and re-validate from DRAFT)
- VALIDATED → DRAFT (cannot un-validate)

**Implementation**:
```python
class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    POSTED = "posted"
    FAILED = "failed"

VALID_TRANSITIONS = {
    InvoiceStatus.DRAFT: [InvoiceStatus.VALIDATED, InvoiceStatus.FAILED],
    InvoiceStatus.VALIDATED: [InvoiceStatus.POSTED, InvoiceStatus.FAILED],
    InvoiceStatus.POSTED: [],  # Terminal state
    InvoiceStatus.FAILED: []   # Terminal state
}

def validate_transition(current: InvoiceStatus, target: InvoiceStatus):
    if target not in VALID_TRANSITIONS[current]:
        raise InvalidStateTransitionError(f"Cannot transition from {current} to {target}")
```

### 4. FBR Integration Architecture

**Validation Flow**:
1. Receive validation request with invoice_id
2. Load invoice from database (check status = DRAFT)
3. Check optimistic lock (version field)
4. Transform invoice to FBR format
5. Call FBR validation API with retry logic
6. Parse response
7. Update invoice status + version (VALIDATED or FAILED)
8. Store FBR response
9. Create audit log entry
10. Return result to client

**Posting Flow**:
1. Receive posting request with invoice_id + idempotency_key
2. Check idempotency cache (return cached if exists)
3. Load invoice from database (check status = VALIDATED)
4. Check user production_access flag if environment = production
5. Check optimistic lock (version field)
6. Transform invoice to FBR format
7. Call FBR posting API with retry logic
8. Parse response
9. Update invoice status + version (POSTED or FAILED)
10. Store FBR response with reference number
11. Create audit log entry
12. Cache result with idempotency_key (24h TTL)
13. Return result to client

**Error Handling Strategy**:
- 4xx errors: Return immediately with FBR error details (no retry)
- 5xx errors: Retry up to 3 times with exponential backoff (1s, 2s, 4s)
- 429 rate limit: Retry up to 3 times with exponential backoff
- Timeout: Retry up to 3 times
- Network errors: Retry up to 3 times
- All errors logged to audit trail

**Retry & Idempotency**:
- Idempotency key required in request header: `X-Idempotency-Key`
- Cache stores: {key: (status_code, response_body, timestamp)}
- Cache TTL: 24 hours
- Cache backend: PostgreSQL table (simple, no Redis dependency)
- Retry logic in httpx transport layer

### 5. Security Architecture

**JWT Verification Flow**:
```
1. Extract Bearer token from Authorization header
2. Verify signature using JWT_SECRET_KEY
3. Check expiration (exp claim)
4. Extract user_id from sub claim
5. Extract production_access from custom claim
6. Inject user context into request.state
7. Proceed to endpoint handler
```

**User Identity Propagation**:
```python
# Dependency injection
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserContext:
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    return UserContext(
        user_id=payload["sub"],
        production_access=payload.get("production_access", False)
    )

# Usage in endpoints
@router.get("/invoices")
async def list_invoices(
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Automatic user_id filtering
    query = select(Invoice).where(Invoice.user_id == user.user_id)
```

**Row-Level Data Isolation**:
- All queries filtered by user_id from JWT
- Database constraints enforce user_id on all invoice tables
- No cross-user data access possible
- Audit logs record user_id for every operation

**API Protection**:
- No public endpoints (all require JWT)
- Rate limiting via middleware (10 req/sec per user)
- Input validation via Pydantic schemas
- SQL injection prevention via SQLModel parameterized queries

## Implementation Phases

### Phase 1 — Foundation (Week 1)

**Deliverables**:
- Project structure setup
- uv dependencies installed
- Pydantic Settings configuration
- Neon PostgreSQL connection (async)
- JWT verification middleware
- Basic FastAPI app with health check

**Key Files**:
- `backend/pyproject.toml` - uv project configuration
- `backend/uv.lock` - Dependency lock file
- `backend/src/config.py` - Settings
- `backend/src/main.py` - FastAPI app
- `backend/src/middleware/auth.py` - JWT middleware
- `backend/src/db/session.py` - Database session
- `backend/.env.example` - Environment template

**Acceptance Criteria**:
- FastAPI app starts successfully
- Database connection established
- JWT middleware rejects invalid tokens
- Health check endpoint returns 200

### Phase 2 — Data Layer (Week 1-2)

**Deliverables**:
- SQLModel models (Invoice, FBRResponse, AuditLog, Idempotency)
- Alembic migrations
- Database schema created
- Async session management

**Key Files**:
- `backend/src/models/invoice.py`
- `backend/src/models/fbr_response.py`
- `backend/src/models/audit_log.py`
- `backend/src/models/idempotency.py`
- `backend/src/db/migrations/versions/001_initial.py`

**Acceptance Criteria**:
- All tables created in Neon PostgreSQL
- Relationships defined correctly
- Optimistic locking (version field) works
- Migrations run successfully

### Phase 3 — Core Invoice APIs (Week 2)

**Deliverables**:
- Create draft invoice endpoint
- List invoices endpoint (with filters)
- Get invoice details endpoint
- Pagination support

**Key Files**:
- `backend/src/api/v1/invoices.py`
- `backend/src/services/invoice_service.py`
- `backend/src/schemas/invoice.py`

**Acceptance Criteria**:
- Users can create draft invoices
- Users see only their own invoices
- Filtering by status/date/type works
- Pagination returns correct results

### Phase 4 — FBR Validation Integration (Week 3)

**Deliverables**:
- FBR client with httpx
- Validation endpoint
- Response parsing
- State transition logic
- Retry mechanism

**Key Files**:
- `backend/src/integrations/fbr_client.py`
- `backend/src/api/v1/validation.py`
- `backend/src/services/fbr_service.py`
- `backend/src/schemas/fbr.py`

**Acceptance Criteria**:
- Validation calls FBR API successfully
- Successful validation transitions to VALIDATED
- Failed validation stores error details
- Retries work for 5xx/429 errors
- Invalid state transitions rejected

### Phase 5 — FBR Posting Integration (Week 3-4)

**Deliverables**:
- Posting endpoint
- Bulk posting support
- Idempotency implementation
- Production access check
- FBR reference number storage

**Key Files**:
- `backend/src/api/v1/posting.py`
- `backend/src/services/fbr_service.py` (extended)

**Acceptance Criteria**:
- Posting calls FBR API successfully
- Idempotency prevents duplicate posts
- Production access enforced
- Bulk posting handles partial failures
- FBR reference numbers stored

### Phase 6 — Logging & Audit (Week 4)

**Deliverables**:
- Audit log creation for all FBR calls
- Audit log retrieval endpoint
- Request/response logging middleware
- Structured logging

**Key Files**:
- `backend/src/services/audit_service.py`
- `backend/src/api/v1/audit.py`
- `backend/src/middleware/logging.py`

**Acceptance Criteria**:
- All FBR calls logged with full payloads
- Audit logs retrievable by user
- Logs immutable (no updates/deletes)
- Structured JSON logging

### Phase 7 — Hardening (Week 5)

**Deliverables**:
- Rate limiting middleware
- Timeout configuration
- Retry policy tuning
- Input validation tightening
- Error handling improvements

**Key Files**:
- `backend/src/middleware/rate_limit.py`
- `backend/src/integrations/fbr_client.py` (tuned)

**Acceptance Criteria**:
- Rate limiting blocks excessive requests
- Timeouts prevent hanging requests
- All inputs validated strictly
- Error responses structured consistently

## Key Architectural Decisions

### Decision 1: JSON Storage for Invoice Payloads

**Chosen**: Store invoice payload as JSONB column + normalized metadata

**Rationale**:
- FBR spec defines complex nested structure (items array)
- Schema may evolve with FBR spec updates
- Querying primarily by metadata (status, date, user_id)
- JSONB allows flexible storage without schema migrations
- Normalized fields (status, user_id, environment) enable efficient filtering

**Alternatives Considered**:
- Fully normalized (separate items table): Rejected due to complexity and FBR spec volatility
- Pure JSON (no metadata): Rejected due to poor query performance

**Tradeoffs**:
- ✅ Flexible schema evolution
- ✅ Simple FBR spec alignment
- ❌ Cannot query deeply nested fields efficiently
- ❌ Larger storage footprint

### Decision 2: Async FBR Communication

**Chosen**: Async httpx client with FastAPI async endpoints

**Rationale**:
- FBR API calls can take 1-3 seconds
- Async allows handling multiple concurrent requests
- FastAPI natively supports async/await
- Better resource utilization under load

**Alternatives Considered**:
- Sync requests: Rejected due to blocking behavior
- Background tasks (Celery): Rejected as overkill for current scale

**Tradeoffs**:
- ✅ Non-blocking I/O
- ✅ Better concurrency
- ❌ Slightly more complex code
- ❌ Requires async database driver

### Decision 3: Optimistic Locking for Concurrency

**Chosen**: Version field on Invoice model, check-and-increment on updates

**Rationale**:
- Allows concurrent reads without locks
- Prevents lost updates from race conditions
- Simple to implement with SQLModel
- Works well with REST API pattern

**Alternatives Considered**:
- Pessimistic locking (SELECT FOR UPDATE): Rejected due to holding locks during slow FBR calls
- Distributed locks (Redis): Rejected as unnecessary complexity

**Tradeoffs**:
- ✅ No lock contention
- ✅ Simple implementation
- ❌ Clients must handle 409 Conflict retries
- ❌ Not suitable for high-contention scenarios (not expected here)

### Decision 4: PostgreSQL-Based Idempotency Cache

**Chosen**: Idempotency table in PostgreSQL with 24h TTL

**Rationale**:
- No additional infrastructure (Redis) required
- Transactional consistency with invoice updates
- Simple cleanup via scheduled job or TTL
- Sufficient performance for expected load

**Alternatives Considered**:
- Redis cache: Rejected to minimize dependencies
- In-memory cache: Rejected due to loss on restart

**Tradeoffs**:
- ✅ No Redis dependency
- ✅ Transactional consistency
- ❌ Slightly slower than Redis
- ❌ Requires cleanup job

### Decision 5: Retry Logic in httpx Transport

**Chosen**: httpx.AsyncHTTPTransport with retry configuration

**Rationale**:
- Built-in retry mechanism
- Configurable per-transport
- Handles transient failures automatically
- Exponential backoff supported

**Alternatives Considered**:
- Manual retry in service layer: Rejected as more error-prone
- tenacity library: Rejected as httpx transport sufficient

**Tradeoffs**:
- ✅ Simple configuration
- ✅ Automatic retry
- ❌ Less fine-grained control
- ❌ Retries all request types (need to filter by status code)

### Decision 6: JWT Verification via Dependency Injection

**Chosen**: FastAPI Depends() with get_current_user dependency

**Rationale**:
- FastAPI native pattern
- Automatic OpenAPI documentation
- Reusable across endpoints
- Clear separation of concerns

**Alternatives Considered**:
- Middleware-only: Rejected as less flexible for endpoint-specific logic
- Manual verification in each endpoint: Rejected as repetitive

**Tradeoffs**:
- ✅ Clean, reusable code
- ✅ Automatic docs
- ❌ Slight overhead per request
- ❌ Requires understanding FastAPI DI

## Testing & Validation Strategy

### 1. Schema Validation Tests
- Validate invoice payloads against FBR spec
- Test all required fields present
- Test field types and formats
- Test nested items array structure

### 2. State Machine Tests
- Test all valid transitions
- Test all invalid transitions (expect 400)
- Test terminal states (POSTED, FAILED)
- Test concurrent transition attempts (optimistic locking)

### 3. Security Tests
- Test missing JWT (expect 401)
- Test invalid JWT signature (expect 401)
- Test expired JWT (expect 401)
- Test cross-user data access (expect 403)
- Test production access enforcement (expect 403)

### 4. Integration Tests (Mocked FBR)
- Mock FBR validation success
- Mock FBR validation failure
- Mock FBR posting success
- Mock FBR posting failure
- Mock FBR timeout
- Mock FBR 5xx error (test retry)
- Mock FBR 429 rate limit (test retry)

### 5. Load & Concurrency Tests
- 50 concurrent invoice creations
- 50 concurrent validations
- Test optimistic locking under contention
- Test database connection pool

### 6. Idempotency Tests
- Duplicate post with same key (expect cached response)
- Duplicate post with different key (expect new post)
- Expired idempotency key (expect new post)

### 7. Audit Trail Tests
- Verify all FBR calls logged
- Verify request/response payloads stored
- Verify user context recorded
- Verify logs immutable

## Risk Analysis

### Risk 1: FBR API Instability
**Likelihood**: Medium | **Impact**: High
**Mitigation**: Retry logic, comprehensive error handling, audit logging for debugging

### Risk 2: JWT Secret Key Compromise
**Likelihood**: Low | **Impact**: Critical
**Mitigation**: Rotate keys regularly, use RS256 (asymmetric), monitor for suspicious activity

### Risk 3: Database Connection Pool Exhaustion
**Likelihood**: Medium | **Impact**: High
**Mitigation**: Configure appropriate pool size, implement connection timeout, monitor pool metrics

### Risk 4: Optimistic Locking Contention
**Likelihood**: Low | **Impact**: Medium
**Mitigation**: Client-side retry logic, exponential backoff, monitor 409 error rate

### Risk 5: Idempotency Cache Growth
**Likelihood**: Medium | **Impact**: Low
**Mitigation**: Scheduled cleanup job, index on created_at, monitor table size

## Next Steps

1. Review and approve this plan
2. Run `/sp.tasks` to generate implementation tasks
3. Begin Phase 1 implementation
4. Set up CI/CD pipeline
5. Configure Neon PostgreSQL database
6. Obtain FBR sandbox credentials

## References

- [Feature Specification](./spec.md)
- [FBR Integration Documentation](../../docs/FBR_INTEGRATION.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [httpx Documentation](https://www.python-httpx.org/)
