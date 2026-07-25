# Data Model: Non-blocking Bulk Invoice Operations

**Feature**: 004-async-bulk-operations
**Date**: 2026-07-25

## Entity: BulkOperationTask

A temporary record representing a single bulk operation (validate or post). Tracks progress during processing and is auto-deleted after completion.

### Table: `bulk_operation_task`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | UUID | PK, default `uuid.uuid4` | Unique task identifier |
| `user_id` | UUID | FK → `users.id`, NOT NULL, INDEX | Owner of the operation |
| `operation_type` | VARCHAR(20) | NOT NULL, CHECK (`'bulk_validate'` OR `'bulk_post'`) | What kind of operation |
| `invoice_ids` | JSON | NOT NULL | List of invoice UUIDs in the batch |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT `'processing'` | Current state |
| `total_count` | INTEGER | NOT NULL | Total invoices in batch |
| `processed_count` | INTEGER | NOT NULL, DEFAULT 0 | How many processed so far |
| `success_count` | INTEGER | NOT NULL, DEFAULT 0 | Successfully validated/posted |
| `failure_count` | INTEGER | NOT NULL, DEFAULT 0 | Failed |
| `errors` | JSON | DEFAULT `[]` | Per-invoice error details |
| `environment` | VARCHAR(10) | NULLABLE | FBR environment (for posting only) |
| `created_at` | DATETIME | NOT NULL, DEFAULT NOW | When started |
| `updated_at` | DATETIME | NOT NULL, DEFAULT NOW, ON UPDATE NOW | Last progress update |
| `completed_at` | DATETIME | NULLABLE | When finished |

### State Transitions

```
                    ┌─────────────┐
                    │ processing  │  (initial state on creation)
                    └──┬──┬──┬───┘
                       │  │  │
          ┌────────────┘  │  └────────────┐
          ▼               ▼               ▼
   ┌──────────┐   ┌──────────────┐   ┌────────┐
   │completed │   │partially_    │   │ failed │
   │          │   │completed     │   │        │
   └────┬─────┘   └──────┬───────┘   └───┬────┘
        │                │               │
        └────────────────┼───────────────┘
                         │
                         ▼
                  ┌──────────┐
                  │ DELETED  │  (cleanup job: >5 min after completed_at)
                  └──────────┘
```

- **processing** → **completed**: All invoices processed, all succeeded
- **processing** → **partially_completed**: All invoices processed, some failed
- **processing** → **failed**: Background task itself crashed (unhandled exception)

### Errors JSON Structure

```json
[
  {
    "invoice_id": "uuid-string",
    "invoice_number": "INV-00123",
    "error": "FBR validation failed: Invalid HS Code"
  }
]
```

### Lifecycle

1. **Created** when user initiates bulk operation (POST endpoint returns `task_id`)
2. **Updated** after each invoice is processed (increment counters, append errors)
3. **Completed** when all invoices processed or task crashes
4. **Retrieved** by frontend polling (`GET /bulk-task/{task_id}`)
5. **Recovered** after navigation via `GET /bulk-tasks/active` (user_id filter, status='processing')
6. **Cleaned up** by scheduler job: `DELETE WHERE status IN ('completed','failed','partially_completed') AND completed_at < NOW() - 5 minutes`

### Relationships

- **User** (`users.id`): Each task belongs to one user. No back-reference from User model (additive only — User model unchanged).

### SQLModel Definition

```python
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
from enum import Enum
from sqlalchemy import Column, String, JSON, DateTime, Integer
from sqlalchemy.types import Uuid
from .base import Base


class BulkOperationType(str, Enum):
    BULK_VALIDATE = "bulk_validate"
    BULK_POST = "bulk_post"


class BulkOperationStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"


class BulkOperationTask(Base, table=True):
    __tablename__ = "bulk_operation_task"

    user_id: uuid.UUID = Field(
        sa_column=Column(Uuid, nullable=False, index=True)
    )
    operation_type: BulkOperationType = Field(
        sa_column=Column(String(20), nullable=False)
    )
    invoice_ids: List[str] = Field(
        sa_column=Column(JSON, nullable=False)
    )
    status: BulkOperationStatus = Field(
        sa_column=Column(String(20), nullable=False, default=BulkOperationStatus.PROCESSING)
    )
    total_count: int = Field(
        sa_column=Column(Integer, nullable=False)
    )
    processed_count: int = Field(
        sa_column=Column(Integer, nullable=False, default=0)
    )
    success_count: int = Field(
        sa_column=Column(Integer, nullable=False, default=0)
    )
    failure_count: int = Field(
        sa_column=Column(Integer, nullable=False, default=0)
    )
    errors: List[dict] = Field(
        sa_column=Column(JSON, default=[])
    )
    environment: Optional[str] = Field(
        sa_column=Column(String(10), nullable=True)
    )
    completed_at: Optional[datetime] = Field(
        sa_column=Column(DateTime, nullable=True)
    )
```

### Pydantic Schemas (separate from model)

```python
# backend/src/schemas/bulk_operation.py

class BulkValidateRequest(BaseModel):
    invoice_ids: List[uuid.UUID]

class BulkPostRequest(BaseModel):
    invoice_ids: List[uuid.UUID]
    environment: str

class BulkOperationResponse(BaseModel):
    task_id: uuid.UUID
    message: str

class BulkOperationError(BaseModel):
    invoice_id: str
    invoice_number: str
    error: str

class BulkOperationStatusResponse(BaseModel):
    task_id: uuid.UUID
    operation_type: str
    status: str
    total_count: int
    processed_count: int
    success_count: int
    failure_count: int
    errors: List[BulkOperationError]
    progress_percentage: float
    created_at: datetime
    completed_at: Optional[datetime]

class ActiveBulkTasksResponse(BaseModel):
    tasks: List[BulkOperationStatusResponse]
```
