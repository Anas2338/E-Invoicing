# Data Model: Automation Database Separation

**Feature ID**: 1-automation-db-separation  
**Created**: 2026-04-24  
**Version**: 1.0

---

## Overview

This document defines the data models for the automation database separation feature. The system uses two separate PostgreSQL databases with distinct entity sets.

---

## Database Architecture

### Main Database (Existing Neon Project)

**Purpose**: Stores user accounts, manual invoices, and FBR master data

**Tables**:
- `users` - User authentication and authorization
- `invoice` - Manual and transferred invoices
- FBR master data tables (provinces, UOM, HS codes, etc.)

### Automation Database (New Neon Project)

**Purpose**: Stores bulk upload data, scheduled invoices, and automation logs

**Tables**:
- `automation_invoice` - Bulk uploaded invoices awaiting transfer
- `excel_upload_session` - Tracks Excel upload sessions
- `automation_log` - Audit trail of automation operations
- `transfer_log` - Audit trail of transfer operations (NEW)

---

## Entity Definitions

### 1. Invoice (Main Database)

**Table**: `invoice`  
**Purpose**: Stores user-created and transferred invoices for manual posting to FBR

**Schema**:

```python
class Invoice(Base):
    __tablename__ = "invoice"
    
    # Primary Key
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # User Reference
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    
    # Invoice Identification
    invoice_number: str = Field(max_length=50, nullable=False, index=True)
    invoice_date: date = Field(nullable=False)
    invoice_type: str = Field(max_length=20, nullable=False)  # "sale", "purchase", etc.
    
    # Seller Information
    seller_ntn: str = Field(max_length=20, nullable=False)
    seller_name: str = Field(max_length=200, nullable=False)
    seller_address: str = Field(max_length=500, nullable=True)
    seller_province: str = Field(max_length=50, nullable=True)
    
    # Buyer Information
    buyer_ntn: str = Field(max_length=20, nullable=False)
    buyer_name: str = Field(max_length=200, nullable=False)
    buyer_address: str = Field(max_length=500, nullable=True)
    buyer_province: str = Field(max_length=50, nullable=True)
    
    # Financial Information
    total_amount: Decimal = Field(max_digits=15, decimal_places=2, nullable=False)
    tax_amount: Decimal = Field(max_digits=15, decimal_places=2, nullable=False)
    discount_amount: Decimal = Field(max_digits=15, decimal_places=2, default=0)
    
    # Invoice Items (JSON array)
    items: dict = Field(sa_column=Column(JSON), nullable=False)
    
    # Status Management
    status: str = Field(max_length=20, nullable=False, index=True)
    # Values: "draft", "validated", "posted", "failed"
    
    # Source Tracking (NEW)
    source: str = Field(max_length=20, default="manual", nullable=False, index=True)
    # Values: "manual", "automation"
    
    transferred_at: Optional[datetime] = Field(default=None, nullable=True)
    automation_invoice_id: Optional[UUID] = Field(default=None, nullable=True)
    # Reference to original automation_invoice (no FK constraint)
    
    # FBR Integration
    fbr_response: Optional[dict] = Field(sa_column=Column(JSON), nullable=True)
    fbr_reference_number: Optional[str] = Field(max_length=100, nullable=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    posted_at: Optional[datetime] = Field(default=None, nullable=True)
    
    # Relationships
    user: "User" = Relationship(back_populates="invoices")
```

**Indexes**:
- `idx_invoice_user_id` on `user_id`
- `idx_invoice_status` on `status`
- `idx_invoice_source` on `source`
- `idx_invoice_number` on `invoice_number`
- `idx_invoice_created_at` on `created_at`

**Constraints**:
- `invoice_number` must be unique per user
- `total_amount` must be >= 0
- `tax_amount` must be >= 0
- `status` must be one of: draft, validated, posted, failed
- `source` must be one of: manual, automation

**State Transitions**:
```
draft → validated → posted
draft → validated → failed
```

---

### 2. AutomationInvoice (Automation Database)

**Table**: `automation_invoice`  
**Purpose**: Stores bulk-uploaded invoices awaiting validation and transfer

**Schema**:

```python
class AutomationInvoice(Base):
    __tablename__ = "automation_invoice"
    
    # Primary Key
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # User Reference (no FK - cross-database)
    user_id: UUID = Field(nullable=False, index=True)
    
    # Session Reference
    session_id: UUID = Field(foreign_key="excel_upload_session.id", nullable=False)
    
    # Invoice Data (JSON blob)
    invoice_data: dict = Field(sa_column=Column(JSON), nullable=False)
    invoice_number: str = Field(max_length=50, nullable=False, index=True)
    
    # Scheduling
    scheduled_date: date = Field(nullable=False, index=True)
    scheduled_time: time = Field(nullable=False, index=True)
    
    # Status Management
    status: str = Field(max_length=20, nullable=False, index=True)
    # Values: "pending", "validated", "transferred", "transfer_failed", "expired", "failed"
    
    # Validation
    validation_errors: Optional[str] = Field(sa_column=Column(Text), nullable=True)
    fbr_response: Optional[dict] = Field(sa_column=Column(JSON), nullable=True)
    
    # Transfer Tracking (NEW)
    transferred_at: Optional[datetime] = Field(default=None, nullable=True)
    transfer_error: Optional[str] = Field(sa_column=Column(Text), nullable=True)
    
    # Retry Logic
    retry_count: int = Field(default=0, nullable=False)
    last_retry_at: Optional[datetime] = Field(default=None, nullable=True)
    
    # Priority
    priority: int = Field(default=5, nullable=False)  # 1=highest, 10=lowest
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    # Relationships
    session: "ExcelUploadSession" = Relationship(back_populates="invoices")
```

**Indexes**:
- `idx_automation_invoice_user_id` on `user_id`
- `idx_automation_invoice_status` on `status`
- `idx_automation_invoice_scheduled_date` on `scheduled_date`
- `idx_automation_invoice_scheduled_time` on `scheduled_time`
- `idx_automation_invoice_created_at` on `created_at`
- Composite: `idx_automation_invoice_transfer_query` on `(status, scheduled_date, scheduled_time)`

**Constraints**:
- `priority` must be between 1 and 10
- `retry_count` must be >= 0
- `status` must be one of: pending, validated, transferred, transfer_failed, expired, failed

**State Transitions**:
```
pending → validated → transferred
pending → expired
pending → failed
validated → transfer_failed → transferred (retry)
```

---

### 3. ExcelUploadSession (Automation Database)

**Table**: `excel_upload_session`  
**Purpose**: Tracks bulk Excel upload sessions

**Schema**:

```python
class ExcelUploadSession(Base):
    __tablename__ = "excel_upload_session"
    
    # Primary Key
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # User Reference (no FK - cross-database)
    user_id: UUID = Field(nullable=False, index=True)
    
    # File Information
    original_filename: str = Field(max_length=255, nullable=False)
    file_path: Optional[str] = Field(max_length=500, nullable=True)  # Deprecated (in-memory parsing)
    
    # Processing Status
    processing_status: str = Field(max_length=20, nullable=False, index=True)
    # Values: "processing", "completed", "failed"
    
    total_rows: int = Field(nullable=False)
    processed_rows: int = Field(default=0, nullable=False)
    
    # Error Tracking
    error_message: Optional[str] = Field(sa_column=Column(Text), nullable=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    completed_at: Optional[datetime] = Field(default=None, nullable=True)
    
    # Relationships
    invoices: list["AutomationInvoice"] = Relationship(back_populates="session")
```

**Indexes**:
- `idx_excel_upload_session_user_id` on `user_id`
- `idx_excel_upload_session_status` on `processing_status`
- `idx_excel_upload_session_created_at` on `created_at`

**Constraints**:
- `total_rows` must be > 0
- `processed_rows` must be >= 0 and <= total_rows
- `processing_status` must be one of: processing, completed, failed
- Unique constraint on `(user_id, processing_status)` where status = 'processing' (prevents concurrent uploads)

---

### 4. TransferLog (Automation Database) - NEW

**Table**: `transfer_log`  
**Purpose**: Audit trail of daily transfer operations

**Schema**:

```python
class TransferLog(Base):
    __tablename__ = "transfer_log"
    
    # Primary Key
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Transfer Information
    transfer_timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
    status: str = Field(max_length=20, nullable=False)
    # Values: "success", "partial_success", "failed"
    
    # Statistics
    invoices_transferred: int = Field(default=0, nullable=False)
    invoices_failed: int = Field(default=0, nullable=False)
    duration_seconds: float = Field(nullable=False)
    
    # Error Details
    error_details: Optional[str] = Field(sa_column=Column(Text), nullable=True)
    failed_invoice_ids: Optional[list] = Field(sa_column=Column(JSON), nullable=True)
    
    # Trigger Information
    triggered_by: str = Field(max_length=20, nullable=False)
    # Values: "scheduled", "manual"
    
    triggered_by_user_id: Optional[UUID] = Field(default=None, nullable=True)
```

**Indexes**:
- `idx_transfer_log_timestamp` on `transfer_timestamp`
- `idx_transfer_log_status` on `status`

**Constraints**:
- `invoices_transferred` must be >= 0
- `invoices_failed` must be >= 0
- `duration_seconds` must be > 0
- `status` must be one of: success, partial_success, failed
- `triggered_by` must be one of: scheduled, manual

---

### 5. AutomationLog (Automation Database)

**Table**: `automation_log`  
**Purpose**: Audit trail of all automation operations

**Schema**:

```python
class AutomationLog(Base):
    __tablename__ = "automation_log"
    
    # Primary Key
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Log Information
    timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
    action: str = Field(max_length=50, nullable=False, index=True)
    # Values: "VALIDATE", "TRANSFER", "RETRY", "BLOCK", "EXPIRE", "CLEANUP"
    
    # Context
    invoice_id: Optional[UUID] = Field(default=None, nullable=True, index=True)
    user_id: Optional[UUID] = Field(default=None, nullable=True)
    
    # Details
    details: dict = Field(sa_column=Column(JSON), nullable=True)
    error_message: Optional[str] = Field(sa_column=Column(Text), nullable=True)
    
    # Result
    result: str = Field(max_length=20, nullable=False)
    # Values: "success", "failure", "skipped"
```

**Indexes**:
- `idx_automation_log_timestamp` on `timestamp`
- `idx_automation_log_action` on `action`
- `idx_automation_log_invoice_id` on `invoice_id`

**Constraints**:
- `action` must be one of: VALIDATE, TRANSFER, RETRY, BLOCK, EXPIRE, CLEANUP
- `result` must be one of: success, failure, skipped

---

## Data Transformation

### Automation Invoice → Manual Invoice

When transferring from automation database to main database, the following transformation occurs:

**Source**: `automation_invoice.invoice_data` (JSON)

```json
{
  "InvoiceNumber": "INV-001",
  "InvoiceDate": "2026-04-24",
  "InvoiceType": "sale",
  "SellerNTN": "1234567",
  "SellerName": "ABC Company",
  "SellerAddress": "123 Main St",
  "SellerProvince": "Punjab",
  "BuyerNTN": "7654321",
  "BuyerName": "XYZ Corp",
  "BuyerAddress": "456 Oak Ave",
  "BuyerProvince": "Sindh",
  "TotalAmount": 10000.00,
  "TaxAmount": 1700.00,
  "DiscountAmount": 0.00,
  "Items": [
    {
      "ItemSNo": 1,
      "ItemName": "Product A",
      "Quantity": 10,
      "UnitPrice": 1000.00,
      "TaxRate": 17.0
    }
  ]
}
```

**Target**: `invoice` (structured fields)

```python
Invoice(
    id=uuid.uuid4(),
    user_id=automation_invoice.user_id,
    invoice_number="INV-001",
    invoice_date=date(2026, 4, 24),
    invoice_type="sale",
    seller_ntn="1234567",
    seller_name="ABC Company",
    seller_address="123 Main St",
    seller_province="Punjab",
    buyer_ntn="7654321",
    buyer_name="XYZ Corp",
    buyer_address="456 Oak Ave",
    buyer_province="Sindh",
    total_amount=Decimal("10000.00"),
    tax_amount=Decimal("1700.00"),
    discount_amount=Decimal("0.00"),
    items={"items": [...]},  # JSON array
    status="validated",
    source="automation",
    transferred_at=datetime.utcnow(),
    automation_invoice_id=automation_invoice.id,
    fbr_response=automation_invoice.fbr_response,
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)
```

**Transformation Rules**:
1. Parse JSON from `invoice_data`
2. Map camelCase keys to snake_case fields
3. Convert string dates to date objects
4. Convert numeric strings to Decimal
5. Set `status = "validated"`
6. Set `source = "automation"`
7. Set `transferred_at = NOW()`
8. Store original `automation_invoice.id` for reference
9. Copy `fbr_response` from automation invoice

---

## Validation Rules

### Invoice Validation

**Required Fields**:
- invoice_number
- invoice_date
- seller_ntn
- buyer_ntn
- total_amount >= 0
- tax_amount >= 0
- items (non-empty array)

**Business Rules**:
- Invoice number must be unique per user
- Invoice date cannot be in the future
- Total amount must equal sum of item amounts
- Tax amount must match calculated tax from items
- Seller and buyer NTN must be valid format (7-13 digits)

### Transfer Validation

**Pre-Transfer Checks**:
- Invoice status must be "validated"
- Invoice not already transferred (check automation_invoice_id)
- User exists in main database
- No duplicate invoice_number for user in main database

**Post-Transfer Verification**:
- Invoice successfully inserted in main database
- Automation invoice marked as "transferred"
- Transfer log entry created

---

## Query Patterns

### Transfer Job Query

```sql
SELECT *
FROM automation_invoice
WHERE status = 'validated'
  AND scheduled_date <= CURRENT_DATE
  AND (
    scheduled_date < CURRENT_DATE
    OR scheduled_time <= CURRENT_TIME
  )
ORDER BY scheduled_date, scheduled_time, priority
LIMIT 1000;
```

### Cleanup Job Query

```sql
DELETE FROM automation_invoice
WHERE created_at < NOW() - INTERVAL '2 days'
  AND status IN ('transferred', 'expired', 'failed');

DELETE FROM excel_upload_session
WHERE created_at < NOW() - INTERVAL '2 days';
```

### User Invoice History Query

```sql
SELECT *
FROM invoice
WHERE user_id = :user_id
  AND (:source IS NULL OR source = :source)
ORDER BY created_at DESC
LIMIT 50 OFFSET :offset;
```

---

## Migration Scripts

### Add New Fields to Invoice Table

```sql
-- Add source tracking fields
ALTER TABLE invoice
ADD COLUMN source VARCHAR(20) DEFAULT 'manual' NOT NULL,
ADD COLUMN transferred_at TIMESTAMP NULL,
ADD COLUMN automation_invoice_id UUID NULL;

-- Create index on source
CREATE INDEX idx_invoice_source ON invoice(source);

-- Update existing records
UPDATE invoice SET source = 'manual' WHERE source IS NULL;
```

### Create Transfer Log Table

```sql
CREATE TABLE transfer_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL,
    invoices_transferred INTEGER NOT NULL DEFAULT 0,
    invoices_failed INTEGER NOT NULL DEFAULT 0,
    duration_seconds FLOAT NOT NULL,
    error_details TEXT NULL,
    failed_invoice_ids JSON NULL,
    triggered_by VARCHAR(20) NOT NULL,
    triggered_by_user_id UUID NULL
);

CREATE INDEX idx_transfer_log_timestamp ON transfer_log(transfer_timestamp);
CREATE INDEX idx_transfer_log_status ON transfer_log(status);
```

### Add Transfer Status to Automation Invoice

```sql
-- Add new status values
ALTER TABLE automation_invoice
ADD COLUMN transferred_at TIMESTAMP NULL,
ADD COLUMN transfer_error TEXT NULL;

-- Update status enum (if using enum type)
-- ALTER TYPE automation_invoice_status ADD VALUE 'transferred';
-- ALTER TYPE automation_invoice_status ADD VALUE 'transfer_failed';
```

---

## Data Retention Policy

### Automation Database

| Table | Retention Period | Cleanup Method |
|-------|------------------|----------------|
| automation_invoice | 2 days | Daily cleanup job |
| excel_upload_session | 2 days | Daily cleanup job |
| automation_log | 90 days | Daily cleanup job |
| transfer_log | Indefinite | Manual archive |

### Main Database

| Table | Retention Period | Cleanup Method |
|-------|------------------|----------------|
| invoice | Indefinite | Manual archive |
| users | Indefinite | Manual deletion |

---

## Backup Strategy

### Automation Database

- **Frequency**: Daily at 1 AM PKT
- **Retention**: 7 days
- **Method**: Neon automatic backups
- **Recovery**: Point-in-time recovery available

### Main Database

- **Frequency**: Daily at 1 AM PKT
- **Retention**: 30 days
- **Method**: Neon automatic backups
- **Recovery**: Point-in-time recovery available

---

## Appendix

### Entity Relationship Diagram

```
Main Database:
┌─────────┐       ┌──────────┐
│  User   │──────<│ Invoice  │
└─────────┘       └──────────┘
                       │
                       │ (reference only, no FK)
                       │
Automation Database:   ▼
┌──────────────────┐  ┌────────────────────┐
│ ExcelUploadSession│─<│ AutomationInvoice │
└──────────────────┘  └────────────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │ AutomationLog│
                      └──────────────┘
                              
                      ┌─────────────┐
                      │ TransferLog │
                      └─────────────┘
```

### Field Mapping Reference

| Automation Invoice (JSON) | Manual Invoice (Field) |
|---------------------------|------------------------|
| InvoiceNumber | invoice_number |
| InvoiceDate | invoice_date |
| InvoiceType | invoice_type |
| SellerNTN | seller_ntn |
| SellerName | seller_name |
| SellerAddress | seller_address |
| SellerProvince | seller_province |
| BuyerNTN | buyer_ntn |
| BuyerName | buyer_name |
| BuyerAddress | buyer_address |
| BuyerProvince | buyer_province |
| TotalAmount | total_amount |
| TaxAmount | tax_amount |
| DiscountAmount | discount_amount |
| Items | items (JSON) |
