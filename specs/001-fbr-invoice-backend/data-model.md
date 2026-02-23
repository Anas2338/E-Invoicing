# Data Model Design

**Feature**: Backend System for FBR Invoice Integration Portal
**Date**: 2026-02-22
**Database**: Neon PostgreSQL (async via asyncpg)

## Overview

This document defines the database schema for the FBR Invoice Integration Backend. All models use SQLModel (SQLAlchemy 2.0 + Pydantic) with async session support.

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Invoice                              │
├─────────────────────────────────────────────────────────────┤
│ id: UUID (PK)                                               │
│ user_id: str (indexed)                                      │
│ invoice_type: str (sale/purchase)                           │
│ environment: str (sandbox/production)                       │
│ status: str (draft/validated/posted/failed)                │
│ version: int (optimistic locking)                           │
│ payload: JSONB (FBR invoice structure)                      │
│ created_at: datetime                                        │
│ updated_at: datetime                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ 1:N
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      FBRResponse                             │
├─────────────────────────────────────────────────────────────┤
│ id: UUID (PK)                                               │
│ invoice_id: UUID (FK → Invoice.id)                          │
│ response_type: str (validation/posting)                     │
│ status_code: str (FBR status code)                          │
│ fbr_reference_number: str (nullable)                        │
│ response_payload: JSONB (complete FBR response)             │
│ created_at: datetime                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       AuditLog                               │
├─────────────────────────────────────────────────────────────┤
│ id: UUID (PK)                                               │
│ invoice_id: UUID (FK → Invoice.id, nullable)                │
│ user_id: str (indexed)                                      │
│ operation: str (create/validate/post/retrieve)              │
│ endpoint: str (FBR API endpoint called)                     │
│ environment: str (sandbox/production)                       │
│ request_payload: JSONB                                      │
│ response_payload: JSONB                                     │
│ http_status_code: int                                       │
│ created_at: datetime                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    IdempotencyCache                          │
├─────────────────────────────────────────────────────────────┤
│ id: UUID (PK)                                               │
│ idempotency_key: str (unique, indexed)                      │
│ invoice_id: UUID (FK → Invoice.id)                          │
│ status_code: int                                            │
│ response_body: JSONB                                        │
│ created_at: datetime                                        │
│ expires_at: datetime (indexed for cleanup)                  │
└─────────────────────────────────────────────────────────────┘
```

## Table Definitions

### 1. Invoice

**Purpose**: Stores invoice data with metadata for filtering and state management.

**SQLModel Definition**:

```python
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

class InvoiceType(str, Enum):
    SALE = "sale"
    PURCHASE = "purchase"

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    POSTED = "posted"
    FAILED = "failed"

class Environment(str, Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    # Primary Key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # User Context
    user_id: str = Field(index=True, nullable=False)

    # Invoice Metadata
    invoice_type: InvoiceType = Field(nullable=False)
    environment: Environment = Field(nullable=False)
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT, index=True)

    # Optimistic Locking
    version: int = Field(default=1, nullable=False)

    # Invoice Data (JSONB)
    payload: dict = Field(sa_column=Column(JSON), nullable=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    fbr_responses: list["FBRResponse"] = Relationship(back_populates="invoice")
    audit_logs: list["AuditLog"] = Relationship(back_populates="invoice")
    idempotency_caches: list["IdempotencyCache"] = Relationship(back_populates="invoice")
```

**Indexes**:
- `user_id` - For filtering by user
- `status` - For filtering by status
- `(user_id, status)` - Composite index for common query pattern
- `(user_id, created_at)` - For date-based filtering
- `(user_id, environment)` - For environment filtering

**Constraints**:
- `user_id` NOT NULL
- `invoice_type` NOT NULL
- `environment` NOT NULL
- `status` NOT NULL
- `version` NOT NULL, DEFAULT 1
- `payload` NOT NULL
- `created_at` NOT NULL
- `updated_at` NOT NULL

**Payload Structure** (JSONB):
```json
{
  "invoiceDate": "2025-04-21",
  "sellerNTNCNIC": "0786909",
  "sellerBusinessName": "Company 8",
  "sellerProvince": "Sindh",
  "sellerAddress": "Karachi",
  "buyerNTNCNIC": "1000000000000",
  "buyerBusinessName": "FERTILIZER MANUFAC IRS NEW",
  "buyerProvince": "Sindh",
  "buyerAddress": "Karachi",
  "buyerRegistrationType": "Registered",
  "invoiceRefNo": "",
  "scenarioId": "SN001",
  "items": [
    {
      "hsCode": "0101.2100",
      "productDescription": "product Description",
      "rate": "18%",
      "uoM": "Numbers, pieces, units",
      "quantity": 1.0000,
      "totalValues": 0.00,
      "valueSalesExcludingST": 1000.00,
      "fixedNotifiedValueOrRetailPrice": 0.00,
      "salesTaxApplicable": 180.00,
      "salesTaxWithheldAtSource": 0.00,
      "extraTax": 0.00,
      "furtherTax": 120.00,
      "sroScheduleNo": "",
      "fedPayable": 0.00,
      "discount": 0.00,
      "saleType": "Goods at standard rate (default)",
      "sroItemSerialNo": ""
    }
  ]
}
```

### 2. FBRResponse

**Purpose**: Stores complete FBR API responses for audit and reference.

**SQLModel Definition**:

```python
class ResponseType(str, Enum):
    VALIDATION = "validation"
    POSTING = "posting"

class FBRResponse(SQLModel, table=True):
    __tablename__ = "fbr_responses"

    # Primary Key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign Key
    invoice_id: UUID = Field(foreign_key="invoices.id", nullable=False, index=True)

    # Response Metadata
    response_type: ResponseType = Field(nullable=False)
    status_code: str = Field(nullable=False)  # FBR status code (00, 01, etc.)
    fbr_reference_number: Optional[str] = Field(default=None)  # Only for successful posting

    # Response Data (JSONB)
    response_payload: dict = Field(sa_column=Column(JSON), nullable=False)

    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    invoice: Invoice = Relationship(back_populates="fbr_responses")
```

**Indexes**:
- `invoice_id` - For retrieving responses by invoice
- `(invoice_id, response_type)` - For filtering by type

**Constraints**:
- `invoice_id` NOT NULL, FOREIGN KEY
- `response_type` NOT NULL
- `status_code` NOT NULL
- `response_payload` NOT NULL
- `created_at` NOT NULL

**Response Payload Structure** (JSONB):
```json
{
  "dated": "2025-05-13 13:13:07",
  "validationResponse": {
    "statusCode": "00",
    "status": "Valid",
    "errorCode": null,
    "error": "",
    "invoiceStatuses": [
      {
        "itemSNo": "1",
        "statusCode": "00",
        "status": "Valid",
        "errorCode": null,
        "error": ""
      }
    ]
  }
}
```

### 3. AuditLog

**Purpose**: Immutable audit trail for all FBR API interactions and invoice operations.

**SQLModel Definition**:

```python
class Operation(str, Enum):
    CREATE = "create"
    VALIDATE = "validate"
    POST = "post"
    RETRIEVE = "retrieve"
    UPDATE = "update"

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    # Primary Key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign Key (nullable for non-invoice operations)
    invoice_id: Optional[UUID] = Field(foreign_key="invoices.id", default=None, index=True)

    # User Context
    user_id: str = Field(index=True, nullable=False)

    # Operation Metadata
    operation: Operation = Field(nullable=False)
    endpoint: Optional[str] = Field(default=None)  # FBR API endpoint if applicable
    environment: Optional[Environment] = Field(default=None)

    # Request/Response Data (JSONB)
    request_payload: Optional[dict] = Field(sa_column=Column(JSON), default=None)
    response_payload: Optional[dict] = Field(sa_column=Column(JSON), default=None)
    http_status_code: Optional[int] = Field(default=None)

    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)

    # Relationships
    invoice: Optional[Invoice] = Relationship(back_populates="audit_logs")
```

**Indexes**:
- `user_id` - For filtering by user
- `invoice_id` - For retrieving logs by invoice
- `created_at` - For date-based filtering
- `(user_id, created_at)` - For user-specific date filtering

**Constraints**:
- `user_id` NOT NULL
- `operation` NOT NULL
- `created_at` NOT NULL
- Immutable: No UPDATE or DELETE operations allowed (enforced at application level)

### 4. IdempotencyCache

**Purpose**: Prevents duplicate invoice posting operations.

**SQLModel Definition**:

```python
class IdempotencyCache(SQLModel, table=True):
    __tablename__ = "idempotency_cache"

    # Primary Key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Idempotency Key (unique)
    idempotency_key: str = Field(unique=True, index=True, nullable=False)

    # Foreign Key
    invoice_id: UUID = Field(foreign_key="invoices.id", nullable=False)

    # Cached Response
    status_code: int = Field(nullable=False)
    response_body: dict = Field(sa_column=Column(JSON), nullable=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    expires_at: datetime = Field(nullable=False, index=True)  # created_at + 24h

    # Relationships
    invoice: Invoice = Relationship(back_populates="idempotency_caches")
```

**Indexes**:
- `idempotency_key` - Unique index for fast lookup
- `expires_at` - For cleanup queries

**Constraints**:
- `idempotency_key` UNIQUE, NOT NULL
- `invoice_id` NOT NULL, FOREIGN KEY
- `status_code` NOT NULL
- `response_body` NOT NULL
- `created_at` NOT NULL
- `expires_at` NOT NULL

**Cleanup Strategy**:
- Scheduled job runs daily: `DELETE FROM idempotency_cache WHERE expires_at < NOW()`
- Or use PostgreSQL extension: `pg_cron` for automatic cleanup

## State Machine Implementation

### Invoice Status Transitions

**Valid Transitions**:
```python
VALID_TRANSITIONS = {
    InvoiceStatus.DRAFT: [InvoiceStatus.VALIDATED, InvoiceStatus.FAILED],
    InvoiceStatus.VALIDATED: [InvoiceStatus.POSTED, InvoiceStatus.FAILED],
    InvoiceStatus.POSTED: [],  # Terminal state
    InvoiceStatus.FAILED: []   # Terminal state
}

def validate_transition(current: InvoiceStatus, target: InvoiceStatus) -> bool:
    """Validate if transition is allowed."""
    return target in VALID_TRANSITIONS.get(current, [])
```

**Enforcement**:
- Check current status before any state change
- Raise `HTTPException(400)` if transition invalid
- Log all state transitions to audit log

## Optimistic Locking Implementation

**Update Pattern**:
```python
async def update_invoice_status(
    session: AsyncSession,
    invoice_id: UUID,
    new_status: InvoiceStatus,
    current_version: int
) -> Invoice:
    """Update invoice status with optimistic locking."""

    # Build update query with version check
    stmt = (
        update(Invoice)
        .where(Invoice.id == invoice_id)
        .where(Invoice.version == current_version)
        .values(
            status=new_status,
            version=current_version + 1,
            updated_at=datetime.utcnow()
        )
        .returning(Invoice)
    )

    result = await session.execute(stmt)
    updated_invoice = result.scalar_one_or_none()

    if not updated_invoice:
        raise HTTPException(
            status_code=409,
            detail="Invoice was modified by another request. Please retry."
        )

    await session.commit()
    return updated_invoice
```

## Query Patterns

### Common Queries

**1. List user's invoices with filters**:
```python
async def list_invoices(
    session: AsyncSession,
    user_id: str,
    status: Optional[InvoiceStatus] = None,
    environment: Optional[Environment] = None,
    limit: int = 50,
    offset: int = 0
) -> list[Invoice]:
    stmt = select(Invoice).where(Invoice.user_id == user_id)

    if status:
        stmt = stmt.where(Invoice.status == status)
    if environment:
        stmt = stmt.where(Invoice.environment == environment)

    stmt = stmt.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(stmt)
    return result.scalars().all()
```

**2. Get invoice with FBR responses**:
```python
async def get_invoice_with_responses(
    session: AsyncSession,
    invoice_id: UUID,
    user_id: str
) -> Optional[Invoice]:
    stmt = (
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .where(Invoice.user_id == user_id)
        .options(selectinload(Invoice.fbr_responses))
    )

    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

**3. Check idempotency cache**:
```python
async def get_cached_response(
    session: AsyncSession,
    idempotency_key: str
) -> Optional[IdempotencyCache]:
    stmt = (
        select(IdempotencyCache)
        .where(IdempotencyCache.idempotency_key == idempotency_key)
        .where(IdempotencyCache.expires_at > datetime.utcnow())
    )

    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

## Migration Strategy

### Initial Migration (Alembic)

```python
# alembic/versions/001_initial_schema.py

def upgrade():
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('invoice_type', sa.String(), nullable=False),
        sa.Column('environment', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoices_user_id', 'invoices', ['user_id'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])
    op.create_index('ix_invoices_user_status', 'invoices', ['user_id', 'status'])

    # Create fbr_responses table
    # ... (similar pattern)

    # Create audit_logs table
    # ... (similar pattern)

    # Create idempotency_cache table
    # ... (similar pattern)

def downgrade():
    op.drop_table('idempotency_cache')
    op.drop_table('audit_logs')
    op.drop_table('fbr_responses')
    op.drop_table('invoices')
```

## Data Validation Rules

### Invoice Payload Validation

**Required Fields** (from FBR spec):
- invoiceDate
- sellerNTNCNIC
- sellerBusinessName
- buyerNTNCNIC
- buyerBusinessName
- scenarioId
- items (array, min 1 item)

**Item Validation**:
- hsCode (format: XXXX.XXXX)
- productDescription
- rate (format: XX%)
- uoM
- quantity (decimal, > 0)
- valueSalesExcludingST (decimal, >= 0)

**Validation Implementation**:
```python
from pydantic import BaseModel, Field, validator

class InvoiceItem(BaseModel):
    hsCode: str = Field(pattern=r'^\d{4}\.\d{4}$')
    productDescription: str
    rate: str = Field(pattern=r'^\d+%$')
    uoM: str
    quantity: float = Field(gt=0)
    valueSalesExcludingST: float = Field(ge=0)
    # ... other fields

class InvoicePayload(BaseModel):
    invoiceDate: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    sellerNTNCNIC: str
    sellerBusinessName: str
    buyerNTNCNIC: str
    buyerBusinessName: str
    scenarioId: str
    items: list[InvoiceItem] = Field(min_items=1)

    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('At least one item required')
        return v
```

## Performance Considerations

### Index Strategy

**High-Priority Indexes**:
1. `invoices(user_id, status)` - Most common query pattern
2. `invoices(user_id, created_at)` - Date-based filtering
3. `idempotency_cache(idempotency_key)` - Unique constraint + fast lookup
4. `audit_logs(user_id, created_at)` - Audit retrieval

**Low-Priority Indexes** (add if needed):
- `invoices(environment)` - If environment filtering is common
- `fbr_responses(fbr_reference_number)` - If lookup by FBR ref is needed

### Query Optimization

- Use `selectinload()` for eager loading relationships
- Limit result sets (default: 50 per page)
- Use `offset` pagination for simplicity (consider cursor-based for large datasets)
- Index JSONB fields if deep queries needed: `CREATE INDEX ON invoices USING GIN (payload)`

## Security Considerations

### Row-Level Security

**Enforcement at Application Level**:
- All queries MUST filter by `user_id` from JWT
- No cross-user data access allowed
- Audit logs record `user_id` for every operation

**Example**:
```python
# CORRECT: Filtered by user_id
stmt = select(Invoice).where(Invoice.user_id == current_user.user_id)

# INCORRECT: No user_id filter (security violation)
stmt = select(Invoice)  # ❌ NEVER DO THIS
```

### Data Protection

- Sensitive fields in payload (NTN/CNIC) stored as-is (required for FBR)
- No encryption at rest (rely on database-level encryption)
- Audit logs immutable (no UPDATE/DELETE)
- Idempotency cache expires after 24h (automatic cleanup)

## Conclusion

This data model provides:
- ✅ Flexible invoice storage (JSONB)
- ✅ Efficient filtering (indexed metadata)
- ✅ Concurrency control (optimistic locking)
- ✅ Complete audit trail (immutable logs)
- ✅ Idempotency support (cache table)
- ✅ State machine enforcement (application-level)
- ✅ User data isolation (row-level filtering)

Ready for implementation in Phase 2.
