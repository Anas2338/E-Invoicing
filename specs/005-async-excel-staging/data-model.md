# Data Model: Async Excel Staging

**Feature**: 005-async-excel-staging  
**Date**: 2026-07-27

## Entity Relationship

```
┌──────────────────────────────┐
│  users (existing)             │
│  id: UUID (PK)               │
└──────────┬───────────────────┘
           │ 1:N
           ▼
┌──────────────────────────────┐       ┌──────────────────────────────┐
│  excel_staging_session        │       │  invoices (existing)          │
│  id: UUID (PK)               │       │  id: UUID (PK)               │
│  user_id: UUID (FK→users)    │       │  ...                         │
│  original_filename: str      │       └──────────────────────────────┘
│  status: enum                │                ▲
│  total_rows: int             │                │ created at commit
│  valid_rows: int             │       ┌────────┴─────────────────────┐
│  errored_rows: int           │       │  Grouped by invoice_number     │
│  created_at: datetime        │       │  from excel_staging_row       │
│  updated_at: datetime        │       └──────────────────────────────┘
└──────────┬───────────────────┘
           │ 1:N
           ▼
┌──────────────────────────────┐
│  excel_staging_row            │
│  id: UUID (PK)               │
│  session_id: UUID (FK)       │
│  user_id: UUID (indexed)     │
│  excel_row_number: int       │
│  group_key: str              │  ← invoice_number for grouping
│  is_valid: bool              │
│  is_dirty: bool              │  ← edited since last recheck
│  field_errors: JSON          │  ← {"field_name": ["error", ...]}
│  ... 16 template fields ...  │
│  ... computed fields ...     │
│  ... seller info ...         │
└──────────────────────────────┘
```

## excel_staging_session

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Session identifier |
| `user_id` | UUID | NOT NULL, FK→users.id, INDEXED | Owning user |
| `original_filename` | VARCHAR(255) | NOT NULL | Uploaded file name for display |
| `status` | VARCHAR(20) | NOT NULL, default 'parsing' | One of: parsing, ready_for_review, rechecking, committing, cancelled |
| `total_rows` | INTEGER | NOT NULL, default 0 | Total parsed rows |
| `valid_rows` | INTEGER | NOT NULL, default 0 | Rows currently valid |
| `errored_rows` | INTEGER | NOT NULL, default 0 | Rows currently with errors |
| `created_at` | DATETIME | NOT NULL, default utcnow | When session was created |
| `updated_at` | DATETIME | NOT NULL, default utcnow | Last modification time |

**Status transitions**:
```
parsing ──► ready_for_review ──► rechecking ──► ready_for_review
                │                    │                │
                │                    │                ▼
                │                    │            committing ──► (DELETED)
                │                    │
                └────────────────────┴────────► cancelled ──► (DELETED)
```

**Indexes**: `user_id` (for session lookup), `status` (for active session queries)

**Lifecycle**: Rows are DELETED (not soft-deleted) after commit or cancel. Expired sessions (created_at > 7 days) are excluded from recovery queries.

## excel_staging_row

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Row identifier |
| `session_id` | UUID | NOT NULL, FK→excel_staging_session.id, INDEXED | Parent session |
| `user_id` | UUID | NOT NULL, INDEXED | Owning user (denormalized for query speed) |
| `excel_row_number` | INTEGER | NOT NULL | Original Excel row (1-based, e.g., row 3 = Excel row 3) |
| `group_key` | VARCHAR(50) | NOT NULL | invoice_number value, used to group rows into multi-item invoices |
| `is_valid` | BOOLEAN | NOT NULL, default True | Whether row passed last validation |
| `is_dirty` | BOOLEAN | NOT NULL, default False | Whether row was edited since last recheck/parse |
| `field_errors` | JSON | default {} | Per-field validation errors |

### Template fields (user-editable data from Excel)

| Column | Type | Default | Validation |
|--------|------|---------|------------|
| `invoice_number` | VARCHAR(50) | NOT NULL | Required, unique within session |
| `invoice_type` | VARCHAR(50) | 'Sale Invoice' | Must be valid invoice type |
| `invoice_date` | VARCHAR(20) | NOT NULL | YYYY-MM-DD format, not in future |
| `buyer_ntn_cnic` | VARCHAR(20) | '' | Required if buyer_registration_type = 'Registered' |
| `buyer_business_name` | VARCHAR(255) | NOT NULL | Required |
| `buyer_province` | VARCHAR(50) | NOT NULL | Must be valid province |
| `buyer_address` | VARCHAR(500) | NOT NULL | Required |
| `buyer_registration_type` | VARCHAR(20) | 'Registered' | One of: Registered, Unregistered, Final Consumer |
| `saved_item_code` | VARCHAR(50) | NOT NULL | Must exist in user's saved items |
| `quantity` | NUMERIC(12,2) | 0 | Must be > 0 |
| `value_sales_excluding_st` | NUMERIC(14,2) | 0 | Must be > 0 |
| `fixed_notified_value_or_retail_price` | NUMERIC(14,2) | 0 | Must be >= value_sales_excluding_st if 3rd Schedule Goods |
| `further_tax` | NUMERIC(12,2) | 0 | Required if buyer is Unregistered |
| `discount` | NUMERIC(12,2) | 0 | Must be <= value_sales_excluding_st |
| `income_tax` | VARCHAR(10) | '236G' | Must be 236G or 236H |
| `withholding_tax_amount` | NUMERIC(12,2) | NULL | Auto-calculated if omitted |

### Computed fields (resolved from saved item at parse/recheck time)

| Column | Type | Source |
|--------|------|--------|
| `hs_code` | VARCHAR(50) | From saved item |
| `product_description` | VARCHAR(500) | From saved item |
| `rate` | VARCHAR(10) | From saved item (e.g., "18") |
| `uom` | VARCHAR(10) | From saved item |
| `total_values` | NUMERIC(14,2) | Calculated |
| `sales_tax_applicable` | NUMERIC(14,2) | Calculated |
| `sale_type` | VARCHAR(10) | From saved item transaction_type |
| `transaction_type_id` | VARCHAR(10) | From saved item |

### Seller fields (captured from user profile at parse time)

| Column | Type | Source |
|--------|------|--------|
| `seller_ntn_cnic` | VARCHAR(20) | User.fbr_seller_ntn |
| `seller_business_name` | VARCHAR(255) | User.fbr_business_name |
| `seller_province` | VARCHAR(50) | User.fbr_seller_province |
| `seller_address` | VARCHAR(500) | User.fbr_seller_address |

### Other computed fields

| Column | Type | Default |
|--------|------|---------|
| `sales_tax_withheld_at_source` | NUMERIC(12,2) | 0 |
| `extra_tax` | NUMERIC(12,2) | 0 |
| `fed_payable` | NUMERIC(12,2) | 0 |
| `sro_schedule_no` | VARCHAR(50) | NULL |
| `sro_item_serial_no` | VARCHAR(50) | NULL |
| `item_rate` | NUMERIC(12,2) | NULL |

**Indexes**: `session_id` (for child row lookups), `user_id` (for ownership queries)

## field_errors JSON structure

```json
{
  "buyer_business_name": ["buyer business name is required"],
  "quantity": ["quantity must be greater than 0"],
  "invoice_date": ["invoice_date is in the future"],
  "saved_item_code": ["'CODE-X' not found in your saved items"]
}
```

- Keys are field names matching the column names
- Values are arrays of error strings (usually one, but can be multiple)
- Empty dict `{}` means no errors → `is_valid = True`
- On cell edit → `field_errors` for that field is set to `{}`, `is_dirty = True`

## State Machine for Row Lifecycle

```
Excel Parse:
  [raw Excel cell values] ──► excel_staging_row (is_valid=true/false, is_dirty=false, field_errors populated)

User Edit:
  excel_staging_row ──► cell value updated ──► field_errors[field]={}, is_dirty=true

Recheck:
  is_dirty=true rows ──► re-validated ──► field_errors repopulated, is_dirty=false, is_valid updated

Commit:
  is_valid=true rows ──► grouped by group_key ──► InvoiceCreate ──► Invoice (DRAFT)
  All rows + session DELETED

Cancel:
  All rows + session DELETED
```
