# Data Model: Digital FTE Invoice Automation

**Feature**: 001-invoice-automation  
**Date**: 2026-04-04  
**Purpose**: Define database schema and SQLModel models for automation feature

## Overview

This document defines the data models for the Digital FTE Invoice Automation feature. All models follow existing patterns from the codebase (SQLModel with UUID primary keys, timestamps, enums for status fields).

---

## Models

### 1. AutomationInvoice

**Purpose**: Represents a single invoice from an uploaded Excel file, tracking its scheduling and processing status.

**Table Name**: `automation_invoice`

**SQLModel Definition**:

```python
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from typing import Optional, TYPE_CHECKING
from datetime import datetime, date, time
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import Index

if TYPE_CHECKING:
    from .user import User
    from .excel_upload_session import ExcelUploadSession
    from .automation_log import AutomationLog


class AutomationInvoiceStatus(str, Enum):
    """Status enum for automation invoices."""
    PENDING = "pending"
    EXPIRED = "expired"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    FAILED = "failed"


class AutomationInvoice(SQLModel, table=True):
    """
    Model for automated invoices from Excel upload.
    Tracks scheduling, processing status, and FBR submission results.
    """
    __tablename__ = "automation_invoice"
    
    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign keys
    user_id: UUID = Field(foreign_key="user.id", index=True)
    excel_upload_session_id: UUID = Field(
        foreign_key="excel_upload_session.id",
        index=True
    )
    
    # Invoice identification
    invoice_number: str = Field(max_length=100, index=True)
    
    # Invoice data (full invoice details from Excel as JSON)
    invoice_data: dict = Field(sa_column=Column(JSON))
    
    # Scheduling information
    scheduled_date: date = Field(index=True)
    scheduled_time: time = Field(index=True)
    
    # Processing status
    status: AutomationInvoiceStatus = Field(
        default=AutomationInvoiceStatus.PENDING,
        index=True
    )
    
    # Validation and submission results
    validation_errors: Optional[str] = Field(default=None, max_length=5000)
    fbr_response: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="automation_invoices")
    excel_upload_session: Optional["ExcelUploadSession"] = Relationship(
        back_populates="automation_invoices"
    )
    automation_logs: list["AutomationLog"] = Relationship(
        back_populates="automation_invoice",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    __table_args__ = (
        # Unique constraint: one invoice number per user
        Index(
            "idx_unique_invoice_per_user",
            "user_id",
            "invoice_number",
            unique=True
        ),
        # Composite index for hourly worker query
        Index(
            "idx_pending_scheduled",
            "status",
            "scheduled_date",
            "scheduled_time"
        ),
    )
```

**Key Fields**:
- `invoice_data`: JSON field containing full invoice details from Excel (customer_name, items, amount, tax, etc.)
- `status`: Tracks invoice lifecycle (pending → expired/validated → submitted/failed)
- `validation_errors`: Stores validation failure reasons
- `fbr_response`: Stores FBR API response for audit trail

**Indexes**:
- `user_id`: For user-specific queries
- `invoice_number`: For duplicate detection
- `(user_id, invoice_number)`: Unique constraint
- `(status, scheduled_date, scheduled_time)`: For FTE worker hourly query
- `excel_upload_session_id`: For session-based queries

**Constraints**:
- Unique constraint on (user_id, invoice_number) prevents duplicate invoice numbers per user
- Foreign key to User ensures data isolation
- Foreign key to ExcelUploadSession tracks which upload created this invoice

---

### 2. AutomationLog

**Purpose**: Audit trail for all automation activities (validation, submission, Excel updates, retries).

**Table Name**: `automation_log`

**SQLModel Definition**:

```python
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .automation_invoice import AutomationInvoice


class AutomationLogAction(str, Enum):
    """Action types for automation logs."""
    VALIDATE = "validate"
    SUBMIT = "submit"
    UPDATE_EXCEL = "update_excel"
    RETRY = "retry"


class AutomationLogStatus(str, Enum):
    """Status for automation log entries."""
    SUCCESS = "success"
    FAILURE = "failure"


class AutomationLog(SQLModel, table=True):
    """
    Model for automation activity logs.
    Provides complete audit trail for all automation operations.
    """
    __tablename__ = "automation_log"
    
    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign key
    automation_invoice_id: UUID = Field(
        foreign_key="automation_invoice.id",
        index=True
    )
    
    # Action details
    action: AutomationLogAction = Field(index=True)
    status: AutomationLogStatus
    
    # Action-specific details (JSON)
    details: dict = Field(sa_column=Column(JSON))
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationship
    automation_invoice: Optional["AutomationInvoice"] = Relationship(
        back_populates="automation_logs"
    )
```

**Key Fields**:
- `action`: Type of operation (validate, submit, update_excel, retry)
- `status`: Whether operation succeeded or failed
- `details`: JSON field with action-specific information (error messages, FBR response summary, etc.)

**Indexes**:
- `automation_invoice_id`: For invoice-specific log queries
- `timestamp`: For chronological queries
- `action`: For filtering by action type

**Example details JSON**:
```json
{
  "action": "validate",
  "status": "failure",
  "details": {
    "errors": ["Missing required field: customer_name", "Invalid tax rate: 25%"],
    "invoice_number": "INV-001"
  }
}

{
  "action": "submit",
  "status": "success",
  "details": {
    "fbr_invoice_id": "FBR-12345",
    "submission_time": "2026-04-04T10:00:00Z",
    "environment": "SANDBOX"
  }
}
```

---

### 3. ExcelUploadSession

**Purpose**: Tracks Excel file uploads and processing status, prevents concurrent uploads per user.

**Table Name**: `excel_upload_session`

**SQLModel Definition**:

```python
from sqlmodel import SQLModel, Field, Relationship, Index
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .user import User
    from .automation_invoice import AutomationInvoice


class ExcelUploadProcessingStatus(str, Enum):
    """Processing status for Excel upload sessions."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExcelUploadSession(SQLModel, table=True):
    """
    Model for Excel upload sessions.
    Tracks file upload and processing status, prevents concurrent uploads.
    """
    __tablename__ = "excel_upload_session"
    
    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Foreign key
    user_id: UUID = Field(foreign_key="user.id", index=True)
    
    # File information
    file_path: Optional[str] = Field(default=None, max_length=500)
    original_filename: str = Field(max_length=255)
    
    # Processing tracking
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    total_rows: int = Field(default=0)
    processed_rows: int = Field(default=0)
    processing_status: ExcelUploadProcessingStatus = Field(
        default=ExcelUploadProcessingStatus.UPLOADING,
        index=True
    )
    
    # Error tracking
    error_message: Optional[str] = Field(default=None, max_length=2000)
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="excel_upload_sessions")
    automation_invoices: list["AutomationInvoice"] = Relationship(
        back_populates="excel_upload_session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    __table_args__ = (
        # Partial unique index: only one 'processing' session per user
        Index(
            "idx_one_processing_per_user",
            "user_id",
            unique=True,
            postgresql_where=(processing_status == ExcelUploadProcessingStatus.PROCESSING)
        ),
        # Composite index for user session queries
        Index(
            "idx_user_sessions",
            "user_id",
            "processing_status",
            "upload_timestamp"
        ),
    )
```

**Key Fields**:
- `file_path`: Path to uploaded Excel file on filesystem
- `processing_status`: Tracks upload lifecycle (uploading → processing → completed/failed)
- `total_rows`: Number of invoice rows in Excel file
- `processed_rows`: Number of rows successfully parsed and stored
- `error_message`: Stores upload/processing error details

**Indexes**:
- `user_id`: For user-specific queries
- `processing_status`: For filtering by status
- `upload_timestamp`: For chronological queries
- `(user_id)` with WHERE processing_status = 'processing': Unique partial index to prevent concurrent uploads

**Status Transitions**:
```
uploading → processing → completed (success)
uploading → processing → failed (error during parsing)
uploading → failed (error during file upload)
```

---

## Relationships

### User Model Updates

Add to existing `src/models/user.py`:

```python
# Add to User model
automation_invoices: list["AutomationInvoice"] = Relationship(
    back_populates="user"
)
excel_upload_sessions: list["ExcelUploadSession"] = Relationship(
    back_populates="user"
)
```

---

## Database Migration

**Alembic Migration**: `alembic/versions/{timestamp}_add_automation_tables.py`

```python
"""Add automation tables

Revision ID: {generated_id}
Revises: {previous_revision}
Create Date: 2026-04-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = '{generated_id}'
down_revision = '{previous_revision}'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create excel_upload_session table
    op.create_table(
        'excel_upload_session',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('upload_timestamp', sa.DateTime(), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=False, default=0),
        sa.Column('processed_rows', sa.Integer(), nullable=False, default=0),
        sa.Column('processing_status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.String(2000), nullable=True),
    )
    
    # Create indexes for excel_upload_session
    op.create_index('idx_excel_upload_user', 'excel_upload_session', ['user_id'])
    op.create_index('idx_excel_upload_status', 'excel_upload_session', ['processing_status'])
    op.create_index('idx_excel_upload_timestamp', 'excel_upload_session', ['upload_timestamp'])
    op.create_index(
        'idx_one_processing_per_user',
        'excel_upload_session',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text("processing_status = 'processing'")
    )
    
    # Create automation_invoice table
    op.create_table(
        'automation_invoice',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('excel_upload_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('excel_upload_session.id'), nullable=False),
        sa.Column('invoice_number', sa.String(100), nullable=False),
        sa.Column('invoice_data', postgresql.JSON(), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('scheduled_time', sa.Time(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('validation_errors', sa.String(5000), nullable=True),
        sa.Column('fbr_response', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
    )
    
    # Create indexes for automation_invoice
    op.create_index('idx_automation_invoice_user', 'automation_invoice', ['user_id'])
    op.create_index('idx_automation_invoice_session', 'automation_invoice', ['excel_upload_session_id'])
    op.create_index('idx_automation_invoice_number', 'automation_invoice', ['invoice_number'])
    op.create_index('idx_automation_invoice_status', 'automation_invoice', ['status'])
    op.create_index('idx_unique_invoice_per_user', 'automation_invoice', ['user_id', 'invoice_number'], unique=True)
    op.create_index('idx_pending_scheduled', 'automation_invoice', ['status', 'scheduled_date', 'scheduled_time'])
    
    # Create automation_log table
    op.create_table(
        'automation_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('automation_invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('automation_invoice.id'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('details', postgresql.JSON(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
    )
    
    # Create indexes for automation_log
    op.create_index('idx_automation_log_invoice', 'automation_log', ['automation_invoice_id'])
    op.create_index('idx_automation_log_timestamp', 'automation_log', ['timestamp'])
    op.create_index('idx_automation_log_action', 'automation_log', ['action'])


def downgrade() -> None:
    op.drop_table('automation_log')
    op.drop_table('automation_invoice')
    op.drop_table('excel_upload_session')
```

---

## Query Patterns

### Common Queries

**1. Get pending invoices for current hour (FTE worker)**:
```python
from datetime import datetime

current_hour = datetime.now().hour
current_date = datetime.now().date()

pending_invoices = db.query(AutomationInvoice).filter(
    AutomationInvoice.status == AutomationInvoiceStatus.PENDING,
    AutomationInvoice.scheduled_date == current_date,
    sa.extract('hour', AutomationInvoice.scheduled_time) == current_hour
).all()
```

**2. Check for concurrent upload**:
```python
existing_session = db.query(ExcelUploadSession).filter(
    ExcelUploadSession.user_id == user_id,
    ExcelUploadSession.processing_status == ExcelUploadProcessingStatus.PROCESSING
).first()
```

**3. Get dashboard statistics**:
```python
from sqlalchemy import func

stats = db.query(
    func.count(AutomationInvoice.id).label('total'),
    func.count(case((AutomationInvoice.status == 'pending', 1))).label('pending'),
    func.count(case((AutomationInvoice.status == 'expired', 1))).label('expired'),
    func.count(case((AutomationInvoice.status == 'submitted', 1))).label('submitted'),
    func.count(case((AutomationInvoice.status == 'failed', 1))).label('failed'),
).filter(
    AutomationInvoice.user_id == user_id
).first()
```

**4. Get user's invoices with pagination and filters**:
```python
query = db.query(AutomationInvoice).filter(
    AutomationInvoice.user_id == user_id
)

if status_filter:
    query = query.filter(AutomationInvoice.status == status_filter)

if date_from:
    query = query.filter(AutomationInvoice.scheduled_date >= date_from)

if date_to:
    query = query.filter(AutomationInvoice.scheduled_date <= date_to)

invoices = query.order_by(
    AutomationInvoice.scheduled_date.desc(),
    AutomationInvoice.scheduled_time.desc()
).offset((page - 1) * page_size).limit(page_size).all()
```

---

## Data Validation Rules

1. **Invoice Number Uniqueness**: Enforced by unique index on (user_id, invoice_number)
2. **Scheduled Time Format**: Must be HH:MM in 24-hour format
3. **Scheduled Date Format**: Must be YYYY-MM-DD
4. **Status Transitions**: 
   - pending → expired (if scheduled time is in past)
   - pending → validated → submitted (success path)
   - pending → failed (validation or submission failure)
   - failed → pending (on manual retry)
5. **Processing Status Transitions**:
   - uploading → processing → completed/failed
6. **Concurrent Upload Prevention**: Enforced by partial unique index on (user_id) WHERE processing_status = 'processing'

---

## Storage Estimates

**Per Invoice**:
- AutomationInvoice row: ~2KB (including JSON data)
- AutomationLog entries (avg 3 per invoice): ~1KB
- Total per invoice: ~3KB

**Per User (1,000 invoices)**:
- AutomationInvoice: 2MB
- AutomationLog: 1MB
- ExcelUploadSession: ~10KB
- Total: ~3MB per 1,000 invoices

**Scale (1,000 users, 10,000 invoices each)**:
- Total database size: ~30GB
- Well within PostgreSQL capacity

---

## AI Agent Schema Extensions (Added 2026-04-10)

### 4. AutomationInvoice Extensions

**Purpose**: Add retry tracking and prioritization fields for AI Agent

**New Fields**:
```python
# Add to existing AutomationInvoice model
retry_count: int = Field(default=0, ge=0)
last_retry_at: Optional[datetime] = Field(default=None)
priority: int = Field(default=5, ge=1, le=10)  # 1=highest, 10=lowest
```

**Rationale**:
- `retry_count`: Track retry attempts for exponential backoff calculation
- `last_retry_at`: Track last retry timestamp for scheduling
- `priority`: Support business rule-based prioritization

**New Indexes**:
```sql
CREATE INDEX idx_retry_tracking ON automation_invoice(status, last_retry_at, retry_count);
CREATE INDEX idx_priority_processing ON automation_invoice(priority, scheduled_date, scheduled_time);
```

---

### 5. AIAgentHealthCheck (NEW)

**Purpose**: Store hourly health check results for monitoring and alerting

**Table Name**: `ai_agent_health_check`

**SQLModel Definition**:
```python
from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AIAgentHealthCheck(SQLModel, table=True):
    """
    Model for AI Agent health check results.
    Generated every hour by the agent's health check job.
    """
    __tablename__ = "ai_agent_health_check"
    
    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Health check metadata
    check_timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    overall_status: HealthStatus = Field(index=True)
    
    # Invoice statistics
    pending_invoice_count: int = Field(ge=0)
    failed_invoice_count: int = Field(ge=0)
    processing_backlog: int = Field(ge=0)
    
    # Failure analysis
    failure_patterns: dict = Field(sa_column=Column(JSON))
    common_errors: dict = Field(sa_column=Column(JSON))
    
    # External service health
    fbr_api_status: str = Field(max_length=50)
    fbr_api_latency_ms: Optional[int] = Field(default=None, ge=0)
    database_status: str = Field(max_length=50)
    database_latency_ms: Optional[int] = Field(default=None, ge=0)
    
    # System resources
    agent_cpu_percent: Optional[float] = Field(default=None, ge=0, le=100)
    agent_memory_mb: Optional[int] = Field(default=None, ge=0)
    
    # Anomalies and recommendations
    anomalies_detected: list[str] = Field(default=[], sa_column=Column(JSON))
    recommended_actions: list[str] = Field(default=[], sa_column=Column(JSON))
    
    # Agent metadata
    agent_version: str = Field(max_length=50)
    agent_uptime_seconds: int = Field(ge=0)
```

**Indexes**:
```sql
CREATE INDEX idx_health_check_timestamp ON ai_agent_health_check(check_timestamp DESC);
CREATE INDEX idx_health_check_status ON ai_agent_health_check(overall_status, check_timestamp DESC);
```

**Data Retention**: 30 days (automated cleanup job)

---

### 6. AutomationLog Extensions (No Schema Change)

**Purpose**: Store AI Agent decisions in existing `details` JSON field

**AI Decision Format**:
```json
{
  "decision_type": "error_classification",
  "input_context": {
    "invoice_id": "uuid",
    "error_message": "...",
    "retry_history": [...]
  },
  "ai_decision": {
    "classification": "TRANSIENT",
    "confidence": 0.95,
    "recommended_action": "retry_with_backoff",
    "retry_delay_seconds": 60,
    "max_attempts": 5
  },
  "rationale": "Error indicates temporary network issue...",
  "model_used": "claude-3-5-sonnet-20241022",
  "timestamp": "2026-04-10T10:30:00Z"
}
```

---

## AI Agent Migration

**Alembic Migration**: `alembic/versions/{timestamp}_add_ai_agent_support.py`

```python
"""Add AI Agent support

Revision ID: {generated_id}
Revises: {previous_revision}
Create Date: 2026-04-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Extend automation_invoice table
    op.add_column('automation_invoice', 
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('automation_invoice', 
        sa.Column('last_retry_at', sa.DateTime(), nullable=True))
    op.add_column('automation_invoice', 
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'))
    
    # Add check constraint for priority
    op.create_check_constraint(
        'ck_automation_invoice_priority',
        'automation_invoice',
        'priority >= 1 AND priority <= 10'
    )
    
    # Add indexes
    op.create_index(
        'idx_retry_tracking',
        'automation_invoice',
        ['status', 'last_retry_at', 'retry_count']
    )
    op.create_index(
        'idx_priority_processing',
        'automation_invoice',
        ['priority', 'scheduled_date', 'scheduled_time']
    )
    
    # Create ai_agent_health_check table
    op.create_table(
        'ai_agent_health_check',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('check_timestamp', sa.DateTime(), nullable=False, index=True),
        sa.Column('overall_status', sa.String(20), nullable=False, index=True),
        sa.Column('pending_invoice_count', sa.Integer(), nullable=False),
        sa.Column('failed_invoice_count', sa.Integer(), nullable=False),
        sa.Column('processing_backlog', sa.Integer(), nullable=False),
        sa.Column('failure_patterns', postgresql.JSON(), nullable=False),
        sa.Column('common_errors', postgresql.JSON(), nullable=False),
        sa.Column('fbr_api_status', sa.String(50), nullable=False),
        sa.Column('fbr_api_latency_ms', sa.Integer(), nullable=True),
        sa.Column('database_status', sa.String(50), nullable=False),
        sa.Column('database_latency_ms', sa.Integer(), nullable=True),
        sa.Column('agent_cpu_percent', sa.Float(), nullable=True),
        sa.Column('agent_memory_mb', sa.Integer(), nullable=True),
        sa.Column('anomalies_detected', postgresql.JSON(), nullable=False),
        sa.Column('recommended_actions', postgresql.JSON(), nullable=False),
        sa.Column('agent_version', sa.String(50), nullable=False),
        sa.Column('agent_uptime_seconds', sa.Integer(), nullable=False)
    )

def downgrade():
    op.drop_table('ai_agent_health_check')
    op.drop_index('idx_priority_processing', 'automation_invoice')
    op.drop_index('idx_retry_tracking', 'automation_invoice')
    op.drop_constraint('ck_automation_invoice_priority', 'automation_invoice')
    op.drop_column('automation_invoice', 'priority')
    op.drop_column('automation_invoice', 'last_retry_at')
    op.drop_column('automation_invoice', 'retry_count')
```

---

## Summary of All Schema Changes

**Original Tables** (2026-04-04):
1. ✅ ExcelUploadSession
2. ✅ AutomationInvoice
3. ✅ AutomationLog

**AI Agent Extensions** (2026-04-10):
4. ✅ AutomationInvoice: +3 fields (retry_count, last_retry_at, priority)
5. ✅ AIAgentHealthCheck: NEW table (18 fields)
6. ✅ AutomationLog: Reuse existing (AI decisions in details JSON)

**Total Indexes**: 15 (original) + 4 (AI Agent) = 19 indexes
