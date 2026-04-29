# API Contracts: Automation Database Separation

**Feature ID**: 1-automation-db-separation  
**Created**: 2026-04-24  
**Version**: 1.0  
**Base URL**: `/api/v1`

---

## Overview

This document defines the API contracts for the automation database separation feature, including new admin endpoints for transfer management and modifications to existing invoice endpoints.

---

## New Endpoints

### 1. Manual Transfer Trigger

**Endpoint**: `POST /admin/transfer/trigger`

**Description**: Manually trigger the invoice transfer job (admin only)

**Authentication**: Required (Admin role)

**Request**:
```http
POST /api/v1/admin/transfer/trigger
Content-Type: application/json
Cookie: session=<session_token>
X-CSRF-Token: <csrf_token>

{
  "dry_run": false
}
```

**Request Body**:
```typescript
{
  dry_run?: boolean  // Optional, default false. If true, simulates transfer without committing
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Transfer completed successfully",
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "invoices_transferred": 45,
    "invoices_failed": 2,
    "duration_seconds": 12.5,
    "started_at": "2026-04-24T19:00:00Z",
    "completed_at": "2026-04-24T19:00:12Z"
  },
  "failed_invoices": [
    {
      "invoice_id": "123e4567-e89b-12d3-a456-426614174000",
      "invoice_number": "INV-001",
      "error": "Duplicate invoice number for user"
    }
  ]
}
```

**Error Responses**:

403 Forbidden:
```json
{
  "detail": "Admin access required"
}
```

409 Conflict:
```json
{
  "detail": "Transfer job already running"
}
```

500 Internal Server Error:
```json
{
  "detail": "Transfer failed: Database connection error"
}
```

---

### 2. Retry Failed Transfers

**Endpoint**: `POST /admin/transfer/retry`

**Description**: Retry specific failed invoice transfers (admin only)

**Authentication**: Required (Admin role)

**Request**:
```http
POST /api/v1/admin/transfer/retry
Content-Type: application/json
Cookie: session=<session_token>
X-CSRF-Token: <csrf_token>

{
  "invoice_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "223e4567-e89b-12d3-a456-426614174001"
  ]
}
```

**Request Body**:
```typescript
{
  invoice_ids: string[]  // Array of automation invoice UUIDs to retry
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Retry completed",
  "summary": {
    "total_requested": 2,
    "successful": 1,
    "failed": 1
  },
  "results": [
    {
      "invoice_id": "123e4567-e89b-12d3-a456-426614174000",
      "invoice_number": "INV-001",
      "status": "success",
      "manual_invoice_id": "550e8400-e29b-41d4-a716-446655440000"
    },
    {
      "invoice_id": "223e4567-e89b-12d3-a456-426614174001",
      "invoice_number": "INV-002",
      "status": "failed",
      "error": "User not found in main database"
    }
  ]
}
```

**Error Responses**:

400 Bad Request:
```json
{
  "detail": "invoice_ids array is required and must not be empty"
}
```

403 Forbidden:
```json
{
  "detail": "Admin access required"
}
```

404 Not Found:
```json
{
  "detail": "One or more invoice IDs not found"
}
```

---

### 3. Get Transfer Logs

**Endpoint**: `GET /admin/transfer/logs`

**Description**: Retrieve transfer operation logs (admin only)

**Authentication**: Required (Admin role)

**Request**:
```http
GET /api/v1/admin/transfer/logs?limit=50&status=failed&from_date=2026-04-20
Cookie: session=<session_token>
```

**Query Parameters**:
```typescript
{
  limit?: number        // Max records to return (default: 50, max: 200)
  offset?: number       // Pagination offset (default: 0)
  status?: string       // Filter by status: "success", "partial_success", "failed"
  from_date?: string    // ISO date string (YYYY-MM-DD)
  to_date?: string      // ISO date string (YYYY-MM-DD)
}
```

**Response** (200 OK):
```json
{
  "total": 125,
  "limit": 50,
  "offset": 0,
  "logs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "transfer_timestamp": "2026-04-24T19:00:00Z",
      "status": "partial_success",
      "invoices_transferred": 45,
      "invoices_failed": 2,
      "duration_seconds": 12.5,
      "triggered_by": "scheduled",
      "triggered_by_user_id": null,
      "error_details": null,
      "failed_invoice_ids": [
        "123e4567-e89b-12d3-a456-426614174000",
        "223e4567-e89b-12d3-a456-426614174001"
      ]
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "transfer_timestamp": "2026-04-23T19:00:00Z",
      "status": "success",
      "invoices_transferred": 38,
      "invoices_failed": 0,
      "duration_seconds": 9.2,
      "triggered_by": "scheduled",
      "triggered_by_user_id": null,
      "error_details": null,
      "failed_invoice_ids": []
    }
  ]
}
```

**Error Responses**:

403 Forbidden:
```json
{
  "detail": "Admin access required"
}
```

---

### 4. Get Transfer Statistics

**Endpoint**: `GET /admin/transfer/stats`

**Description**: Get aggregate transfer statistics (admin only)

**Authentication**: Required (Admin role)

**Request**:
```http
GET /api/v1/admin/transfer/stats?days=30
Cookie: session=<session_token>
```

**Query Parameters**:
```typescript
{
  days?: number  // Number of days to include (default: 30, max: 365)
}
```

**Response** (200 OK):
```json
{
  "period": {
    "from": "2026-03-25",
    "to": "2026-04-24",
    "days": 30
  },
  "summary": {
    "total_transfers": 30,
    "successful_transfers": 28,
    "partial_success_transfers": 1,
    "failed_transfers": 1,
    "success_rate": 93.3,
    "total_invoices_transferred": 1250,
    "total_invoices_failed": 15,
    "average_duration_seconds": 11.2,
    "average_invoices_per_transfer": 41.7
  },
  "daily_breakdown": [
    {
      "date": "2026-04-24",
      "transfers": 1,
      "invoices_transferred": 45,
      "invoices_failed": 2,
      "status": "partial_success"
    }
  ]
}
```

---

## Modified Endpoints

### 5. Get Invoice History

**Endpoint**: `GET /invoices/history`

**Description**: Retrieve user's invoice history (now includes transferred invoices)

**Authentication**: Required

**Request**:
```http
GET /api/v1/invoices/history?source=automation&limit=50&offset=0
Cookie: session=<session_token>
```

**Query Parameters** (MODIFIED):
```typescript
{
  limit?: number        // Max records (default: 50, max: 200)
  offset?: number       // Pagination offset (default: 0)
  status?: string       // Filter by status: "draft", "validated", "posted", "failed"
  source?: string       // NEW: Filter by source: "manual", "automation"
  from_date?: string    // ISO date string
  to_date?: string      // ISO date string
}
```

**Response** (200 OK) - MODIFIED:
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "invoices": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "invoice_number": "INV-001",
      "invoice_date": "2026-04-24",
      "invoice_type": "sale",
      "seller_name": "ABC Company",
      "buyer_name": "XYZ Corp",
      "total_amount": 10000.00,
      "tax_amount": 1700.00,
      "status": "validated",
      "source": "automation",
      "transferred_at": "2026-04-24T19:00:12Z",
      "created_at": "2026-04-24T19:00:12Z",
      "posted_at": null
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "invoice_number": "INV-002",
      "invoice_date": "2026-04-23",
      "invoice_type": "sale",
      "seller_name": "ABC Company",
      "buyer_name": "DEF Inc",
      "total_amount": 5000.00,
      "tax_amount": 850.00,
      "status": "posted",
      "source": "manual",
      "transferred_at": null,
      "created_at": "2026-04-23T10:30:00Z",
      "posted_at": "2026-04-23T11:00:00Z"
    }
  ]
}
```

**Changes**:
- Added `source` field to response (values: "manual", "automation")
- Added `transferred_at` field to response (null for manual invoices)
- Added `source` query parameter for filtering

---

### 6. Get Invoice Details

**Endpoint**: `GET /invoices/{invoice_id}`

**Description**: Get detailed invoice information

**Authentication**: Required

**Request**:
```http
GET /api/v1/invoices/550e8400-e29b-41d4-a716-446655440000
Cookie: session=<session_token>
```

**Response** (200 OK) - MODIFIED:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "invoice_number": "INV-001",
  "invoice_date": "2026-04-24",
  "invoice_type": "sale",
  "seller_ntn": "1234567",
  "seller_name": "ABC Company",
  "seller_address": "123 Main St",
  "seller_province": "Punjab",
  "buyer_ntn": "7654321",
  "buyer_name": "XYZ Corp",
  "buyer_address": "456 Oak Ave",
  "buyer_province": "Sindh",
  "total_amount": 10000.00,
  "tax_amount": 1700.00,
  "discount_amount": 0.00,
  "items": [
    {
      "item_sno": 1,
      "item_name": "Product A",
      "quantity": 10,
      "unit_price": 1000.00,
      "tax_rate": 17.0,
      "total": 11700.00
    }
  ],
  "status": "validated",
  "source": "automation",
  "transferred_at": "2026-04-24T19:00:12Z",
  "automation_invoice_id": "123e4567-e89b-12d3-a456-426614174000",
  "fbr_response": {
    "statusCode": "00",
    "status": "Valid"
  },
  "fbr_reference_number": null,
  "created_at": "2026-04-24T19:00:12Z",
  "updated_at": "2026-04-24T19:00:12Z",
  "posted_at": null
}
```

**Changes**:
- Added `source` field
- Added `transferred_at` field
- Added `automation_invoice_id` field (reference to original automation invoice)

---

## Unchanged Endpoints

The following endpoints remain unchanged but will work with transferred invoices:

### 7. Post Invoice to FBR

**Endpoint**: `POST /invoices/{invoice_id}/post`

**Description**: Post invoice to FBR (works for both manual and transferred invoices)

**Authentication**: Required

**Behavior**: No changes - works identically for manual and automation-sourced invoices

---

### 8. Update Invoice

**Endpoint**: `PUT /invoices/{invoice_id}`

**Description**: Update invoice details (works for both manual and transferred invoices)

**Authentication**: Required

**Behavior**: No changes - users can edit transferred invoices before posting

---

### 9. Delete Invoice

**Endpoint**: `DELETE /invoices/{invoice_id}`

**Description**: Delete invoice (works for both manual and transferred invoices)

**Authentication**: Required

**Behavior**: No changes - users can delete transferred invoices

---

## Data Types

### TransferStatus

```typescript
type TransferStatus = "success" | "partial_success" | "failed";
```

### InvoiceSource

```typescript
type InvoiceSource = "manual" | "automation";
```

### InvoiceStatus

```typescript
type InvoiceStatus = "draft" | "validated" | "posted" | "failed";
```

### TransferLog

```typescript
interface TransferLog {
  id: string;                          // UUID
  transfer_timestamp: string;          // ISO 8601 datetime
  status: TransferStatus;
  invoices_transferred: number;
  invoices_failed: number;
  duration_seconds: number;
  triggered_by: "scheduled" | "manual";
  triggered_by_user_id: string | null; // UUID or null
  error_details: string | null;
  failed_invoice_ids: string[];        // Array of UUIDs
}
```

### Invoice (Extended)

```typescript
interface Invoice {
  id: string;                          // UUID
  invoice_number: string;
  invoice_date: string;                // ISO date (YYYY-MM-DD)
  invoice_type: string;
  seller_ntn: string;
  seller_name: string;
  seller_address: string | null;
  seller_province: string | null;
  buyer_ntn: string;
  buyer_name: string;
  buyer_address: string | null;
  buyer_province: string | null;
  total_amount: number;
  tax_amount: number;
  discount_amount: number;
  items: InvoiceItem[];
  status: InvoiceStatus;
  source: InvoiceSource;               // NEW
  transferred_at: string | null;       // NEW - ISO 8601 datetime
  automation_invoice_id: string | null; // NEW - UUID
  fbr_response: object | null;
  fbr_reference_number: string | null;
  created_at: string;                  // ISO 8601 datetime
  updated_at: string;                  // ISO 8601 datetime
  posted_at: string | null;            // ISO 8601 datetime
}
```

---

## Error Codes

### Standard HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict (e.g., duplicate, concurrent operation) |
| 500 | Internal Server Error | Server-side error |

### Custom Error Codes

All error responses follow this format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "CUSTOM_ERROR_CODE",
  "context": {
    "field": "additional context"
  }
}
```

**Transfer-Specific Error Codes**:

| Error Code | Description |
|------------|-------------|
| TRANSFER_IN_PROGRESS | Another transfer job is currently running |
| TRANSFER_FAILED | Transfer job failed completely |
| INVOICE_ALREADY_TRANSFERRED | Invoice has already been transferred |
| DUPLICATE_INVOICE_NUMBER | Invoice number already exists for user |
| USER_NOT_FOUND | User not found in main database |
| TRANSFORMATION_ERROR | Failed to transform invoice data |

---

## Rate Limiting

### Admin Endpoints

- **Manual Transfer Trigger**: 10 requests per hour per admin
- **Retry Failed Transfers**: 20 requests per hour per admin
- **Get Transfer Logs**: 100 requests per hour per admin
- **Get Transfer Statistics**: 100 requests per hour per admin

### User Endpoints

- **Get Invoice History**: 100 requests per hour per user
- **Get Invoice Details**: 200 requests per hour per user

---

## Authentication

All endpoints require authentication via session cookie:

```http
Cookie: session=<session_token>
```

State-changing endpoints (POST, PUT, DELETE) also require CSRF token:

```http
X-CSRF-Token: <csrf_token>
```

Admin endpoints additionally require the user to have `role = "admin"`.

---

## Versioning

API Version: `v1`

All endpoints are prefixed with `/api/v1/`

Future breaking changes will increment the version number (v2, v3, etc.)

---

## Pagination

Endpoints that return lists support pagination:

**Query Parameters**:
- `limit`: Number of records to return (default: 50, max: 200)
- `offset`: Number of records to skip (default: 0)

**Response Format**:
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "items": [...]
}
```

---

## Filtering

Endpoints support filtering via query parameters:

**Date Filtering**:
- `from_date`: ISO date string (YYYY-MM-DD)
- `to_date`: ISO date string (YYYY-MM-DD)

**Status Filtering**:
- `status`: Exact match on status field

**Source Filtering** (NEW):
- `source`: Filter by invoice source ("manual" or "automation")

---

## Sorting

Default sorting is by `created_at DESC` (newest first)

Future versions may support custom sorting via `sort` and `order` query parameters.

---

## Examples

### Example 1: Manually Trigger Transfer

```bash
curl -X POST https://api.example.com/api/v1/admin/transfer/trigger \
  -H "Content-Type: application/json" \
  -H "Cookie: session=abc123" \
  -H "X-CSRF-Token: xyz789" \
  -d '{"dry_run": false}'
```

### Example 2: Get Automation Invoices Only

```bash
curl -X GET "https://api.example.com/api/v1/invoices/history?source=automation&limit=20" \
  -H "Cookie: session=abc123"
```

### Example 3: Retry Failed Transfers

```bash
curl -X POST https://api.example.com/api/v1/admin/transfer/retry \
  -H "Content-Type: application/json" \
  -H "Cookie: session=abc123" \
  -H "X-CSRF-Token: xyz789" \
  -d '{
    "invoice_ids": [
      "123e4567-e89b-12d3-a456-426614174000",
      "223e4567-e89b-12d3-a456-426614174001"
    ]
  }'
```

### Example 4: Get Transfer Logs for Failed Transfers

```bash
curl -X GET "https://api.example.com/api/v1/admin/transfer/logs?status=failed&limit=10" \
  -H "Cookie: session=abc123"
```

---

## Testing

### Postman Collection

A Postman collection with all endpoints is available at:
`specs/1-automation-db-separation/contracts/postman_collection.json`

### OpenAPI Specification

Full OpenAPI 3.0 specification available at:
`specs/1-automation-db-separation/contracts/openapi.yaml`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-24 | Initial API contracts for automation database separation |
