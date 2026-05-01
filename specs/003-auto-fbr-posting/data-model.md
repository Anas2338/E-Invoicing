# Data Model: Auto FBR Posting

**Feature**: 003-auto-fbr-posting  
**Date**: 2026-05-01  
**Status**: Complete

## Overview

This document defines the data model changes required for the auto FBR posting feature. All changes extend existing models or create new supporting entities without breaking existing functionality.

---

## Entity Changes

### 1. User Model Extensions

**File**: `backend/src/models/user.py`  
**Change Type**: Extend existing model

#### New Fields

```python
class UserBase(SQLModel):
    # ... existing fields ...
    
    # Auto-posting configuration
    auto_posting_enabled: bool = Field(default=False)
    auto_posting_start_time: time = Field(
        default=time(9, 0),  # 09:00 AM
        sa_column=Column(Time, nullable=False)
    )
    auto_posting_end_time: time = Field(
        default=time(18, 0),  # 06:00 PM
        sa_column=Column(Time, nullable=False)
    )
    auto_posting_environment: str = Field(
        default="SANDBOX",
        sa_column=Column(String(20), nullable=False)
    )
    auto_posting_daily_limit: int = Field(
        default=100,
        sa_column=Column(Integer, nullable=False)
    )
    auto_posting_paused_until: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )
```

#### Field Descriptions

| Field | Type | Default | Nullable | Description |
|-------|------|---------|----------|-------------|
| `auto_posting_enabled` | boolean | false | No | Master toggle for auto-posting feature |
| `auto_posting_start_time` | time | 09:00 | No | Start time of posting window (24-hour format) |
| `auto_posting_end_time` | time | 18:00 | No | End time of posting window (24-hour format) |
| `auto_posting_environment` | string | SANDBOX | No | Target FBR environment (SANDBOX/PRODUCTION) |
| `auto_posting_daily_limit` | integer | 100 | No | Maximum invoices to post per day (1-1000) |
| `auto_posting_paused_until` | datetime | null | Yes | Temporary pause until this timestamp |

#### Validation Rules

- `auto_posting_start_time` and `auto_posting_end_time`: Any valid time (supports midnight-spanning)
- `auto_posting_environment`: Must be "SANDBOX" or "PRODUCTION"
- `auto_posting_daily_limit`: Must be between 1 and 1000
- `auto_posting_paused_until`: Must be future datetime or null

#### Indexes

```sql
CREATE INDEX idx_users_auto_posting ON users(auto_posting_enabled) 
WHERE auto_posting_enabled = true;
```

---

### 2. Invoice Model Extensions

**File**: `backend/src/models/invoice.py`  
**Change Type**: Extend existing model

#### New Status Values

```python
class InvoiceStatus(str, Enum):
    # ... existing statuses ...
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    TRANSFERRED = "TRANSFERRED"  # Validated and ready for FBR posting
    POSTED = "POSTED"
    FAILED = "FAILED"
    
    # New statuses for auto-posting
    FBR_POSTING = "FBR_POSTING"  # Currently being posted to FBR
    FBR_POSTED = "FBR_POSTED"    # Successfully posted to FBR
    FBR_FAILED = "FBR_FAILED"    # Failed to post to FBR
```

#### New Fields

```python
class InvoiceBase(SQLModel):
    # ... existing fields ...
    
    # FBR posting tracking
    fbr_posted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )
    fbr_posting_error: Optional[str] = Field(
        default=None,
        sa_column=Column(String(2000), nullable=True)
    )
    fbr_retry_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False)
    )
```

#### Field Descriptions

| Field | Type | Default | Nullable | Description |
|-------|------|---------|----------|-------------|
| `fbr_posted_at` | datetime | null | Yes | Timestamp when successfully posted to FBR |
| `fbr_posting_error` | string | null | Yes | Error message if posting failed (max 2000 chars) |
| `fbr_retry_count` | integer | 0 | No | Number of retry attempts (max 3) |

#### Status Transitions

```
TRANSFERRED → FBR_POSTING → FBR_POSTED (success)
                          → FBR_FAILED (error)
                          
FBR_FAILED → FBR_POSTING (retry, max 3 times)
          → FBR_FAILED (permanent after 3 retries)
```

#### Indexes

```sql
CREATE INDEX idx_invoices_fbr_posting ON invoices(user_id, status, scheduled_date, scheduled_time)
WHERE status IN ('TRANSFERRED', 'FBR_POSTING', 'FBR_FAILED');
```

---

### 3. Daily Posting Counter (New Entity)

**File**: `backend/src/models/daily_posting_counter.py`  
**Change Type**: New model

#### Model Definition

```python
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date, datetime
import uuid
from sqlalchemy import Column, Date, DateTime, Integer, UniqueConstraint
from sqlalchemy.types import Uuid

class DailyPostingCounter(SQLModel, table=True):
    """
    Tracks daily posting counts per user for limit enforcement.
    
    Supports midnight-spanning windows by tracking window_start_date.
    """
    __tablename__ = "daily_posting_counters"
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_user_date'),
    )
    
    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Foreign key
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True
    )
    
    # Counter fields
    date: date = Field(
        sa_column=Column(Date, nullable=False, index=True),
        description="Calendar date for this counter (PKT timezone)"
    )
    posted_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
        description="Number of invoices posted on this date"
    )
    window_start_date: date = Field(
        sa_column=Column(Date, nullable=False),
        description="Date when posting window started (for midnight-spanning windows)"
    )
    
    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
```

#### Field Descriptions

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `user_id` | UUID | No | Foreign key to users table |
| `date` | date | No | Calendar date for this counter (PKT timezone) |
| `posted_count` | integer | No | Number of invoices posted on this date |
| `window_start_date` | date | No | Date when posting window started (for midnight spans) |
| `created_at` | datetime | No | Record creation timestamp |
| `updated_at` | datetime | No | Record last update timestamp |

#### Unique Constraints

- `(user_id, date)`: One counter per user per date

#### Indexes

```sql
CREATE INDEX idx_daily_counters_user_date ON daily_posting_counters(user_id, date);
CREATE INDEX idx_daily_counters_date ON daily_posting_counters(date);
```

#### Usage Example

```python
# Get or create counter for today
counter = db.query(DailyPostingCounter).filter(
    DailyPostingCounter.user_id == user.id,
    DailyPostingCounter.date == today_pkt
).first()

if not counter:
    counter = DailyPostingCounter(
        user_id=user.id,
        date=today_pkt,
        posted_count=0,
        window_start_date=window_start_date
    )
    db.add(counter)

# Increment counter
counter.posted_count += 1
db.commit()
```

---

### 4. Posting Log (New Entity)

**File**: `backend/src/models/posting_log.py`  
**Change Type**: New model

#### Model Definition

```python
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import Column, DateTime, String, JSON
from sqlalchemy.types import Uuid

class PostingLog(SQLModel, table=True):
    """
    Audit log for all invoice posting attempts (auto and manual).
    
    Used for troubleshooting, analytics, and compliance.
    """
    __tablename__ = "posting_logs"
    
    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Foreign keys
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True
    )
    invoice_id: uuid.UUID = Field(
        foreign_key="invoices.id",
        nullable=False,
        index=True
    )
    
    # Log fields
    action: str = Field(
        sa_column=Column(String(20), nullable=False),
        description="'auto' or 'manual'"
    )
    result: str = Field(
        sa_column=Column(String(20), nullable=False),
        description="'success' or 'failure'"
    )
    environment: str = Field(
        sa_column=Column(String(20), nullable=False),
        description="'SANDBOX' or 'PRODUCTION'"
    )
    error_details: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Structured error information if failed"
    )
    agent_cycle_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50), nullable=True),
        description="Agent cycle identifier for auto posts"
    )
    
    # Timestamp
    created_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, index=True)
    )
```

#### Field Descriptions

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `user_id` | UUID | No | Foreign key to users table |
| `invoice_id` | UUID | No | Foreign key to invoices table |
| `action` | string | No | 'auto' or 'manual' |
| `result` | string | No | 'success' or 'failure' |
| `environment` | string | No | 'SANDBOX' or 'PRODUCTION' |
| `error_details` | JSON | Yes | Structured error information if failed |
| `agent_cycle_id` | string | Yes | Agent cycle identifier for auto posts |
| `created_at` | datetime | No | Log entry timestamp |

#### Indexes

```sql
CREATE INDEX idx_posting_logs_user ON posting_logs(user_id);
CREATE INDEX idx_posting_logs_invoice ON posting_logs(invoice_id);
CREATE INDEX idx_posting_logs_created ON posting_logs(created_at);
CREATE INDEX idx_posting_logs_result ON posting_logs(result) WHERE result = 'failure';
```

#### Usage Example

```python
# Log successful auto-posting
log = PostingLog(
    user_id=user.id,
    invoice_id=invoice.id,
    action="auto",
    result="success",
    environment=user.auto_posting_environment,
    agent_cycle_id=f"cycle-{datetime.utcnow().isoformat()}"
)
db.add(log)

# Log failed manual posting
log = PostingLog(
    user_id=user.id,
    invoice_id=invoice.id,
    action="manual",
    result="failure",
    environment="PRODUCTION",
    error_details={
        "error_code": "NETWORK_TIMEOUT",
        "error_message": "Connection timeout after 30 seconds",
        "fbr_response": None
    }
)
db.add(log)
```

---

## Entity Relationships

```
User (1) ──────────── (many) Invoice
  │                              │
  │                              │
  │                              │
  ├─ (1:many) ─ DailyPostingCounter
  │
  └─ (1:many) ─ PostingLog ─ (many:1) ─ Invoice
```

### Relationship Details

1. **User → Invoice**: One user has many invoices (existing)
2. **User → DailyPostingCounter**: One user has many counters (one per date)
3. **User → PostingLog**: One user has many posting logs
4. **Invoice → PostingLog**: One invoice has many posting logs (multiple attempts)

---

## Database Migration

### Migration File Structure

```python
# alembic/versions/YYYYMMDD_add_auto_posting.py

def upgrade():
    # 1. Add columns to users table
    op.add_column('users', sa.Column('auto_posting_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('auto_posting_start_time', sa.Time(), nullable=False, server_default='09:00:00'))
    op.add_column('users', sa.Column('auto_posting_end_time', sa.Time(), nullable=False, server_default='18:00:00'))
    op.add_column('users', sa.Column('auto_posting_environment', sa.String(20), nullable=False, server_default='SANDBOX'))
    op.add_column('users', sa.Column('auto_posting_daily_limit', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('users', sa.Column('auto_posting_paused_until', sa.DateTime(), nullable=True))
    
    # 2. Add new invoice statuses
    op.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'FBR_POSTING'")
    op.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'FBR_POSTED'")
    op.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'FBR_FAILED'")
    
    # 3. Add columns to invoices table
    op.add_column('invoices', sa.Column('fbr_posted_at', sa.DateTime(), nullable=True))
    op.add_column('invoices', sa.Column('fbr_posting_error', sa.String(2000), nullable=True))
    op.add_column('invoices', sa.Column('fbr_retry_count', sa.Integer(), nullable=False, server_default='0'))
    
    # 4. Create daily_posting_counters table
    op.create_table(
        'daily_posting_counters',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('posted_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('window_start_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_date')
    )
    
    # 5. Create posting_logs table
    op.create_table(
        'posting_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('invoice_id', sa.Uuid(), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('result', sa.String(20), nullable=False),
        sa.Column('environment', sa.String(20), nullable=False),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('agent_cycle_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 6. Create indexes
    op.create_index('idx_users_auto_posting', 'users', ['auto_posting_enabled'], postgresql_where=sa.text('auto_posting_enabled = true'))
    op.create_index('idx_invoices_fbr_posting', 'invoices', ['user_id', 'status', 'scheduled_date', 'scheduled_time'])
    op.create_index('idx_daily_counters_user_date', 'daily_posting_counters', ['user_id', 'date'])
    op.create_index('idx_daily_counters_date', 'daily_posting_counters', ['date'])
    op.create_index('idx_posting_logs_user', 'posting_logs', ['user_id'])
    op.create_index('idx_posting_logs_invoice', 'posting_logs', ['invoice_id'])
    op.create_index('idx_posting_logs_created', 'posting_logs', ['created_at'])
    op.create_index('idx_posting_logs_result', 'posting_logs', ['result'], postgresql_where=sa.text("result = 'failure'"))

def downgrade():
    # Drop in reverse order
    op.drop_index('idx_posting_logs_result')
    op.drop_index('idx_posting_logs_created')
    op.drop_index('idx_posting_logs_invoice')
    op.drop_index('idx_posting_logs_user')
    op.drop_index('idx_daily_counters_date')
    op.drop_index('idx_daily_counters_user_date')
    op.drop_index('idx_invoices_fbr_posting')
    op.drop_index('idx_users_auto_posting')
    
    op.drop_table('posting_logs')
    op.drop_table('daily_posting_counters')
    
    op.drop_column('invoices', 'fbr_retry_count')
    op.drop_column('invoices', 'fbr_posting_error')
    op.drop_column('invoices', 'fbr_posted_at')
    
    # Note: Cannot remove enum values in PostgreSQL, would require recreating the type
    
    op.drop_column('users', 'auto_posting_paused_until')
    op.drop_column('users', 'auto_posting_daily_limit')
    op.drop_column('users', 'auto_posting_environment')
    op.drop_column('users', 'auto_posting_end_time')
    op.drop_column('users', 'auto_posting_start_time')
    op.drop_column('users', 'auto_posting_enabled')
```

---

## Data Integrity Rules

1. **User Configuration**:
   - `auto_posting_daily_limit` must be between 1 and 1000
   - `auto_posting_environment` must be "SANDBOX" or "PRODUCTION"
   - `auto_posting_paused_until` must be future datetime or null

2. **Invoice Status Transitions**:
   - Can only transition to FBR_POSTING from TRANSFERRED or FBR_FAILED
   - Can only transition to FBR_POSTED from FBR_POSTING
   - Can only transition to FBR_FAILED from FBR_POSTING
   - `fbr_retry_count` cannot exceed 3

3. **Daily Posting Counter**:
   - One counter per (user_id, date) combination
   - `posted_count` cannot be negative
   - `window_start_date` must be <= `date`

4. **Posting Log**:
   - `action` must be "auto" or "manual"
   - `result` must be "success" or "failure"
   - `environment` must be "SANDBOX" or "PRODUCTION"
   - `error_details` required if `result` is "failure"

---

**Data Model Status**: ✅ Complete  
**Migration Ready**: Yes  
**Backward Compatible**: Yes
