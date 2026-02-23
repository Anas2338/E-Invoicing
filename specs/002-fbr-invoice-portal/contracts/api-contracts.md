# API Contracts: Frontend to Backend

**Feature**: 002-fbr-invoice-portal
**Date**: 2026-02-23
**Version**: v1
**Base URL**: `/api/v1`

## Overview

This document defines the REST API contracts between the Next.js frontend and FastAPI backend. All endpoints require authentication unless explicitly marked as public.

**Authentication**: JWT tokens in HTTP-only cookies (managed by Better Auth)

**Content-Type**: `application/json`

**Error Format**: All errors follow consistent structure
```json
{
  "error": {
    "message": "Human-readable error message",
    "code": "ERROR_CODE",
    "status": 400,
    "details": {}
  }
}
```

---

## Authentication Endpoints

### POST /auth/signup

Create a new user account.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "businessName": "ABC Trading Co.",
  "taxId": "1234567890123"
}
```

**Response** (201 Created):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "businessName": "ABC Trading Co.",
    "taxId": "1234567890123",
    "productionApproved": false,
    "createdAt": "2026-02-23T10:00:00Z"
  },
  "message": "Account created successfully. Please verify your email."
}
```

**Errors**:
- `400`: Invalid input (email format, weak password, invalid tax ID)
- `409`: Email already exists

---

### POST /auth/login

Authenticate user and create session.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "businessName": "ABC Trading Co.",
    "productionApproved": false
  },
  "message": "Login successful"
}
```

**Side Effect**: Sets HTTP-only cookie with JWT token

**Errors**:
- `401`: Invalid credentials
- `403`: Account not verified

---

### POST /auth/logout

Terminate user session.

**Request**: Empty body

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

**Side Effect**: Clears session cookie

---

### GET /auth/session

Get current session information.

**Response** (200 OK):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "businessName": "ABC Trading Co.",
    "productionApproved": false
  }
}
```

**Errors**:
- `401`: Not authenticated

---

## Invoice Endpoints

### POST /invoices

Create a new invoice (draft).

**Request**:
```json
{
  "invoiceNumber": "INV-000001",
  "type": "sale",
  "environment": "sandbox",
  "invoiceDate": "2026-02-23",
  "dueDate": "2026-03-23",
  "customerName": "XYZ Corp",
  "customerTaxId": "9876543210987",
  "customerAddress": "123 Main St, Karachi",
  "lineItems": [
    {
      "description": "Product A",
      "quantity": 10,
      "unitPrice": 100.00,
      "taxRate": 17,
      "taxAmount": 170.00,
      "amount": 1170.00
    }
  ],
  "subtotal": 1000.00,
  "taxTotal": 170.00,
  "grandTotal": 1170.00
}
```

**Response** (201 Created):
```json
{
  "invoice": {
    "id": "uuid",
    "userId": "uuid",
    "invoiceNumber": "INV-000001",
    "type": "sale",
    "status": "draft",
    "environment": "sandbox",
    "invoiceDate": "2026-02-23",
    "dueDate": "2026-03-23",
    "customerName": "XYZ Corp",
    "customerTaxId": "9876543210987",
    "customerAddress": "123 Main St, Karachi",
    "lineItems": [...],
    "subtotal": 1000.00,
    "taxTotal": 170.00,
    "grandTotal": 1170.00,
    "createdAt": "2026-02-23T10:00:00Z",
    "updatedAt": "2026-02-23T10:00:00Z"
  },
  "message": "Invoice created successfully"
}
```

**Errors**:
- `400`: Invalid input (validation errors)
- `401`: Not authenticated
- `409`: Invoice number already exists

---

### GET /invoices

List invoices with filtering and pagination.

**Query Parameters**:
- `status`: Comma-separated list (draft,validated,posted,failed)
- `type`: Comma-separated list (sale,purchase)
- `environment`: Comma-separated list (sandbox,production)
- `dateFrom`: ISO 8601 date (YYYY-MM-DD)
- `dateTo`: ISO 8601 date (YYYY-MM-DD)
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 20, max: 100)

**Example**: `/invoices?status=validated,posted&environment=sandbox&page=1&pageSize=20`

**Response** (200 OK):
```json
{
  "invoices": [
    {
      "id": "uuid",
      "invoiceNumber": "INV-000001",
      "type": "sale",
      "status": "validated",
      "environment": "sandbox",
      "customerName": "XYZ Corp",
      "grandTotal": 1170.00,
      "createdAt": "2026-02-23T10:00:00Z",
      "validatedAt": "2026-02-23T10:05:00Z"
    }
  ],
  "pagination": {
    "total": 45,
    "page": 1,
    "pageSize": 20,
    "totalPages": 3,
    "hasMore": true
  }
}
```

**Errors**:
- `401`: Not authenticated
- `400`: Invalid query parameters

---

### GET /invoices/{id}

Get invoice details by ID.

**Response** (200 OK):
```json
{
  "invoice": {
    "id": "uuid",
    "userId": "uuid",
    "invoiceNumber": "INV-000001",
    "type": "sale",
    "status": "posted",
    "environment": "sandbox",
    "invoiceDate": "2026-02-23",
    "dueDate": "2026-03-23",
    "customerName": "XYZ Corp",
    "customerTaxId": "9876543210987",
    "lineItems": [...],
    "subtotal": 1000.00,
    "taxTotal": 170.00,
    "grandTotal": 1170.00,
    "fbrReference": "FBR-REF-12345",
    "fbrResponse": {
      "success": true,
      "reference": "FBR-REF-12345",
      "timestamp": "2026-02-23T10:10:00Z",
      "rawResponse": {...}
    },
    "createdAt": "2026-02-23T10:00:00Z",
    "updatedAt": "2026-02-23T10:10:00Z",
    "validatedAt": "2026-02-23T10:05:00Z",
    "postedAt": "2026-02-23T10:10:00Z"
  }
}
```

**Errors**:
- `401`: Not authenticated
- `403`: Not authorized (invoice belongs to another user)
- `404`: Invoice not found

---

### PUT /invoices/{id}

Update a draft invoice.

**Request**: Same as POST /invoices (full invoice object)

**Response** (200 OK):
```json
{
  "invoice": {...},
  "message": "Invoice updated successfully"
}
```

**Errors**:
- `400`: Invalid input
- `401`: Not authenticated
- `403`: Not authorized or invoice not in draft status
- `404`: Invoice not found

---

### DELETE /invoices/{id}

Delete a draft invoice.

**Response** (200 OK):
```json
{
  "message": "Invoice deleted successfully"
}
```

**Errors**:
- `401`: Not authenticated
- `403`: Not authorized or invoice not in draft status
- `404`: Invoice not found

---

### POST /invoices/{id}/validate

Validate invoice with FBR.

**Request**: Empty body

**Response** (200 OK):
```json
{
  "success": true,
  "invoice": {
    "id": "uuid",
    "status": "validated",
    "fbrReference": "FBR-VAL-12345",
    "fbrResponse": {
      "success": true,
      "reference": "FBR-VAL-12345",
      "timestamp": "2026-02-23T10:05:00Z",
      "rawResponse": {...}
    },
    "validatedAt": "2026-02-23T10:05:00Z"
  },
  "message": "Invoice validated successfully"
}
```

**Response** (400 Bad Request - Validation Failed):
```json
{
  "success": false,
  "invoice": {
    "id": "uuid",
    "status": "failed",
    "fbrResponse": {
      "success": false,
      "timestamp": "2026-02-23T10:05:00Z",
      "errors": [
        {
          "code": "INVALID_TAX_ID",
          "message": "Customer tax ID is invalid",
          "field": "customerTaxId"
        }
      ],
      "rawResponse": {...}
    }
  },
  "message": "Invoice validation failed"
}
```

**Errors**:
- `401`: Not authenticated
- `403`: Not authorized or invoice not in draft status
- `404`: Invoice not found
- `503`: FBR service unavailable

---

### POST /invoices/post

Post validated invoices to FBR (bulk operation).

**Request**:
```json
{
  "invoiceIds": ["uuid1", "uuid2", "uuid3"]
}
```

**Response** (200 OK):
```json
{
  "results": [
    {
      "invoiceId": "uuid1",
      "success": true,
      "invoice": {
        "id": "uuid1",
        "status": "posted",
        "fbrReference": "FBR-POST-12345",
        "postedAt": "2026-02-23T10:10:00Z"
      }
    },
    {
      "invoiceId": "uuid2",
      "success": false,
      "error": "Invoice already posted",
      "invoice": {
        "id": "uuid2",
        "status": "failed"
      }
    }
  ],
  "summary": {
    "total": 2,
    "successful": 1,
    "failed": 1
  }
}
```

**Errors**:
- `400`: Invalid input (empty array, invalid IDs)
- `401`: Not authenticated
- `403`: Not authorized (one or more invoices not owned by user)
- `503`: FBR service unavailable

---

### GET /invoices/{id}/pdf

Download invoice PDF.

**Response** (200 OK):
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="INV-000001.pdf"`
- Body: PDF binary data

**Errors**:
- `401`: Not authenticated
- `403`: Not authorized
- `404`: Invoice not found
- `500`: PDF generation failed

---

## Dashboard Endpoints

### GET /dashboard/stats

Get dashboard statistics.

**Response** (200 OK):
```json
{
  "stats": {
    "draftCount": 5,
    "validatedCount": 3,
    "postedCount": 42,
    "failedCount": 2
  },
  "recentInvoices": [
    {
      "id": "uuid",
      "invoiceNumber": "INV-000042",
      "status": "posted",
      "grandTotal": 5000.00,
      "createdAt": "2026-02-23T09:00:00Z"
    }
  ]
}
```

**Errors**:
- `401`: Not authenticated

---

## User Endpoints

### GET /users/me

Get current user profile.

**Response** (200 OK):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "businessName": "ABC Trading Co.",
    "taxId": "1234567890123",
    "productionApproved": false,
    "createdAt": "2026-02-23T10:00:00Z",
    "updatedAt": "2026-02-23T10:00:00Z"
  }
}
```

**Errors**:
- `401`: Not authenticated

---

### PUT /users/me

Update user profile.

**Request**:
```json
{
  "businessName": "ABC Trading Co. Ltd.",
  "email": "newemail@example.com"
}
```

**Response** (200 OK):
```json
{
  "user": {...},
  "message": "Profile updated successfully"
}
```

**Errors**:
- `400`: Invalid input
- `401`: Not authenticated
- `409`: Email already exists

---

## Error Codes

### Authentication Errors
- `AUTH_REQUIRED`: Authentication required
- `AUTH_INVALID`: Invalid credentials
- `AUTH_EXPIRED`: Session expired
- `AUTH_FORBIDDEN`: Not authorized

### Validation Errors
- `VALIDATION_ERROR`: Input validation failed
- `INVALID_FORMAT`: Invalid data format
- `REQUIRED_FIELD`: Required field missing
- `DUPLICATE_ENTRY`: Duplicate entry exists

### Invoice Errors
- `INVOICE_NOT_FOUND`: Invoice not found
- `INVOICE_INVALID_STATUS`: Invalid invoice status for operation
- `INVOICE_ALREADY_POSTED`: Invoice already posted
- `INVOICE_VALIDATION_FAILED`: FBR validation failed

### FBR Errors
- `FBR_SERVICE_UNAVAILABLE`: FBR service unavailable
- `FBR_TIMEOUT`: FBR request timeout
- `FBR_INVALID_RESPONSE`: Invalid FBR response

### System Errors
- `INTERNAL_ERROR`: Internal server error
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable

---

## Rate Limiting

**Limits**:
- Authentication endpoints: 5 requests per minute
- Invoice creation: 10 requests per minute
- Invoice validation: 20 requests per minute
- Invoice posting: 10 requests per minute
- Other endpoints: 60 requests per minute

**Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1614556800
```

**Error Response** (429 Too Many Requests):
```json
{
  "error": {
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "code": "RATE_LIMIT_EXCEEDED",
    "status": 429,
    "details": {
      "retryAfter": 30
    }
  }
}
```

---

## Idempotency

**POST /invoices/{id}/validate** and **POST /invoices/post** support idempotency.

**Header**: `Idempotency-Key: <unique-key>`

If the same idempotency key is used within 24 hours, the original response is returned without re-executing the operation.

---

## Versioning

API version is specified in the URL path: `/api/v1/`

Breaking changes will result in a new version: `/api/v2/`

---

## CORS

**Allowed Origins**: Same origin only (Next.js frontend)

**Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS

**Allowed Headers**: Content-Type, Authorization

**Credentials**: Included (for cookies)

---

## Notes

1. All timestamps are in ISO 8601 format (UTC)
2. All monetary values are in PKR (Pakistani Rupee)
3. All IDs are UUIDs
4. Pagination uses 1-based indexing
5. Date filters are inclusive (dateFrom <= date <= dateTo)
6. Empty arrays are valid responses (not null)
7. Null values are used for optional fields that are not set
8. Boolean flags default to false if not specified
