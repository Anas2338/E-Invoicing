# API Contracts: Async Excel Staging

**Feature**: 005-async-excel-staging  
**Base URL**: `/api/v1/invoices/excel/staging`

## Endpoints Overview

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/upload` | Required | Upload Excel file, parse, create staging session |
| GET | `/active` | Required | Get user's active (non-terminal) staging session |
| GET | `/{session_id}` | Required | Get full session with all rows |
| PUT | `/{session_id}/rows/{row_id}` | Required | Update a single cell on a row |
| POST | `/{session_id}/recheck` | Required | Re-validate dirty rows |
| POST | `/{session_id}/commit` | Required | Commit all valid rows as DRAFT invoices |
| DELETE | `/{session_id}` | Required | Cancel and delete staging session |

---

## POST /upload

Upload an Excel file for parsing and staging.

**Request**: `multipart/form-data`
```
file: <binary .xlsx file>
```

**Response** `201 Created`:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready_for_review",
  "original_filename": "bulk_invoices.xlsx",
  "total_rows": 10,
  "valid_rows": 7,
  "errored_rows": 3
}
```

**Errors**:
- `400` — File too large (>10MB), invalid format, not .xlsx, structural validation failed
- `400` — "No invoice data found in file" (only sample row or empty)
- `429` — Rate limit exceeded (5/hour)

---

## GET /active

Get the user's currently active staging session.

**Response** `200 OK`:
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ready_for_review",
      "original_filename": "bulk_invoices.xlsx",
      "total_rows": 10,
      "valid_rows": 7,
      "errored_rows": 3,
      "created_at": "2026-07-27T10:30:00Z",
      "updated_at": "2026-07-27T10:30:05Z"
    }
  ]
}
```

**Response** `200 OK` (no active session):
```json
{ "sessions": [] }
```

---

## GET /{session_id}

Get full session details with all rows.

**Response** `200 OK`:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready_for_review",
  "original_filename": "bulk_invoices.xlsx",
  "total_rows": 10,
  "valid_rows": 7,
  "errored_rows": 3,
  "created_at": "2026-07-27T10:30:00Z",
  "updated_at": "2026-07-27T10:30:05Z",
  "rows": [
    {
      "id": "row-uuid-1",
      "excel_row_number": 3,
      "group_key": "INV-001",
      "is_valid": true,
      "is_dirty": false,
      "field_errors": {},
      "invoice_number": "INV-001",
      "invoice_type": "Sale Invoice",
      "invoice_date": "2026-07-27",
      "buyer_ntn_cnic": "1234567",
      "buyer_business_name": "ABC Corporation",
      "buyer_province": "PUNJAB",
      "buyer_address": "123 Main Street, Lahore",
      "buyer_registration_type": "Registered",
      "saved_item_code": "ITEM001",
      "quantity": 2.00,
      "value_sales_excluding_st": 50000.00,
      "fixed_notified_value_or_retail_price": 50000.00,
      "further_tax": 0.00,
      "discount": 0.00,
      "income_tax": "236G",
      "withholding_tax_amount": 50.00,
      "product_description": "Laptop Computer",
      "rate": "18",
      "uom": "NOS",
      "total_values": 59000.00,
      "sales_tax_applicable": 9000.00
    },
    {
      "id": "row-uuid-2",
      "excel_row_number": 4,
      "group_key": "INV-001",
      "is_valid": true,
      "is_dirty": false,
      "field_errors": {},
      "invoice_number": "INV-001",
      "invoice_type": "Sale Invoice",
      "invoice_date": "2026-07-27",
      "buyer_ntn_cnic": "1234567",
      "buyer_business_name": "ABC Corporation",
      "buyer_province": "PUNJAB",
      "buyer_address": "123 Main Street, Lahore",
      "buyer_registration_type": "Registered",
      "saved_item_code": "ITEM002",
      "quantity": 1.00,
      "value_sales_excluding_st": 30000.00,
      "fixed_notified_value_or_retail_price": 30000.00,
      "further_tax": 0.00,
      "discount": 0.00,
      "income_tax": "236G",
      "withholding_tax_amount": 30.00,
      "product_description": "Monitor Screen",
      "rate": "18",
      "uom": "NOS",
      "total_values": 35400.00,
      "sales_tax_applicable": 5400.00
    },
    {
      "id": "row-uuid-3",
      "excel_row_number": 5,
      "group_key": "INV-002",
      "is_valid": false,
      "is_dirty": true,
      "field_errors": {
        "buyer_business_name": ["buyer business name is required"],
        "quantity": ["quantity must be greater than 0"]
      },
      "invoice_number": "INV-002",
      "invoice_type": "Sale Invoice",
      "invoice_date": "2026-07-26",
      "buyer_ntn_cnic": "",
      "buyer_business_name": "",
      "buyer_province": "SINDH",
      "buyer_address": "456 Karachi Road",
      "buyer_registration_type": "Unregistered",
      "saved_item_code": "ITEM001",
      "quantity": -1.00,
      "value_sales_excluding_st": 25000.00,
      "fixed_notified_value_or_retail_price": 25000.00,
      "further_tax": 1000.00,
      "discount": 0.00,
      "income_tax": "236H",
      "withholding_tax_amount": 125.00,
      "product_description": "Laptop Computer",
      "rate": "18",
      "uom": "NOS",
      "total_values": 30500.00,
      "sales_tax_applicable": 4500.00
    }
  ]
}
```

**Errors**:
- `404` — Session not found or not owned by user

---

## PUT /{session_id}/rows/{row_id}

Update one or more fields on a staging row.

**Request** `application/json`:
```json
{
  "buyer_business_name": "XYZ Traders",
  "quantity": 5
}
```

All fields are optional — only send the ones being changed.

**Response** `200 OK`:
```json
{
  "id": "row-uuid-3",
  "is_valid": true,
  "is_dirty": true,
  "field_errors": {},
  "invoice_number": "INV-002",
  "invoice_type": "Sale Invoice",
  "buyer_business_name": "XYZ Traders",
  "quantity": 5.00
}
```

**Errors**:
- `404` — Session or row not found
- `400` — Session not in editable state (parsing, committing, cancelled)

---

## POST /{session_id}/recheck

Re-validate all rows marked as dirty (edited since last recheck/parse).

**Request**: Empty body

**Response** `200 OK`:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "errored_rows_before": 3,
  "errored_rows_after": 1,
  "all_clear": false,
  "rows": [
    {
      "id": "row-uuid-3",
      "is_valid": false,
      "is_dirty": false,
      "field_errors": {
        "buyer_business_name": ["buyer business name is required"]
      }
    }
  ]
}
```

**Errors**:
- `404` — Session not found
- `400` — Session not in recheckable state

---

## POST /{session_id}/commit

Create DRAFT invoices from all valid rows. Deletes session and rows on success.

**Request**: Empty body

**Response** `200 OK`:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_committed": 9,
  "total_failed": 1,
  "invoices": [
    {
      "id": "inv-uuid-1",
      "external_id": "INV-001",
      "invoice_type": "Sale Invoice",
      "status": "DRAFT"
    },
    {
      "id": "inv-uuid-2",
      "external_id": "INV-002",
      "invoice_type": "Sale Invoice",
      "status": "DRAFT"
    }
  ],
  "errors": [
    {
      "invoice_number": "INV-010",
      "error": "Invoice number already exists in your history"
    }
  ]
}
```

**Errors**:
- `404` — Session not found
- `400` — Session has errored rows (must recheck first), or session not in committable state

---

## DELETE /{session_id}

Cancel and delete a staging session and all its rows.

**Response** `200 OK`:
```json
{
  "message": "Upload cancelled. Staging session deleted."
}
```

**Errors**:
- `404` — Session not found or not owned by user
