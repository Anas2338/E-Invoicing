# Automation API Contracts (OpenAPI 3.0)

**Service**: AI-Agent  
**Base Path**: `/api/v1/automation`  
**All endpoints require**: Authentication (JWT cookie), CSRF token (for mutations), `automation_enabled` flag on user

---

## 1. Excel Template Download

```
GET /automation/template/download
```

**Response**: `200` — Binary Excel file (`.xlsx`)  
**Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

---

## 2. Excel Upload

```
POST /automation/excel/upload
```

**Request**: Multipart form-data
- `file`: Excel file (`.xlsx`, max 10MB, max 1000 rows)

**Response `200`**:
```json
{
  "session_id": "uuid",
  "total_rows": 150,
  "message": "File uploaded successfully. Validation in progress."
}
```

**Errors**: `400` (invalid file), `401` (unauthenticated), `403` (automation disabled), `429` (rate limit)

---

## 3. Upload Status Polling

```
GET /automation/excel/status/{session_id}
```

**Response `200`**:
```json
{
  "session_id": "uuid",
  "status": "processing",
  "processed_rows": 85,
  "total_rows": 150,
  "error_message": null,
  "validated_count": 60,
  "failed_count": 5,
  "expired_count": 3,
  "pending_count": 17,
  "progress_percentage": 56.7
}
```

**Errors**: `404` (session not found)

---

## 4. Dashboard Statistics

```
GET /automation/dashboard/stats
```

**Response `200`**:
```json
{
  "total_invoices": 1500,
  "pending": 200,
  "expired": 50,
  "validated": 800,
  "paused": 100,
  "transferred": 300,
  "transfer_failed": 20,
  "failed": 25,
  "blocked": 5
}
```

---

## 5. Invoice List (Paginated)

```
GET /automation/dashboard/invoices?status=validated&source=excel_upload&date_from=2026-05-01&date_to=2026-06-30&page=1&page_size=20
```

**Response `200`**:
```json
{
  "invoices": [
    {
      "id": "uuid",
      "invoice_number": "INV-001",
      "user_id": "uuid",
      "status": "validated",
      "source": "excel_upload",
      "scheduled_date": "2026-06-15",
      "scheduled_time": "09:00",
      "created_at": "2026-05-13T10:30:00Z",
      "updated_at": "2026-05-13T10:35:00Z",
      "retry_count": 0,
      "fbr_response": null,
      "transfer_error": null
    }
  ],
  "total": 1500,
  "page": 1,
  "page_size": 20,
  "total_pages": 75
}
```

---

## 6. Invoice Detail

```
GET /automation/dashboard/invoice/{invoice_id}
```

**Response `200`**:
```json
{
  "invoice": {
    "id": "uuid",
    "invoice_number": "INV-001",
    "status": "validated",
    "source": "excel_upload",
    "invoice_data": { /* full FBR invoice payload */ },
    "scheduled_date": "2026-06-15",
    "scheduled_time": "09:00",
    "retry_count": 0,
    "fbr_response": null,
    "created_at": "2026-05-13T10:30:00Z",
    "updated_at": "2026-05-13T10:35:00Z"
  },
  "logs": [
    {
      "id": "uuid",
      "action": "VALIDATE",
      "status": "SUCCESS",
      "details": {},
      "created_at": "2026-05-13T10:35:00Z"
    }
  ],
  "validation_errors": null
}
```

**Errors**: `404` (invoice not found), `403` (not owner)

---

## 7. Retry Invoice

```
POST /automation/invoice/{invoice_id}/retry
```

**Response `200`**:
```json
{
  "success": true,
  "message": "Invoice queued for retry",
  "invoice_id": "uuid",
  "new_status": "pending"
}
```

---

## 8. Upload Sessions List

```
GET /automation/upload-sessions
```

**Response `200`**:
```json
{
  "sessions": [
    {
      "id": "uuid",
      "original_filename": "bulk_invoices.xlsx",
      "total_rows": 150,
      "processed_rows": 150,
      "processing_status": "completed",
      "validated_count": 120,
      "failed_count": 10,
      "expired_count": 5,
      "pending_count": 15,
      "created_at": "2026-05-13T10:30:00Z"
    }
  ]
}
```

---

## 9. Delete Upload Session

```
DELETE /automation/upload-session/{session_id}
```

**Response `200`**: `{ "success": true, "message": "Upload session and associated invoices deleted" }`  
**Errors**: `400` (session has transferred invoices), `404`

---

## 10. Delete Excel File Only

```
DELETE /automation/upload-session/{session_id}/file
```

**Response `200`**: `{ "success": true, "message": "Excel file deleted, invoice records retained" }`

---

## 11. Block Invoice

```
POST /automation/invoice/{invoice_id}/block
```

**Request Body**:
```json
{ "reason": "Customer requested hold" }
```

**Response `200`**: `{ "success": true, "message": "Invoice blocked" }`

---

## 12. Unblock Invoice

```
POST /automation/invoice/{invoice_id}/unblock
```

**Response `200`**: `{ "success": true, "message": "Invoice unblocked" }`

---

## 13. Delete Single Invoice

```
DELETE /automation/invoice/{invoice_id}
```

**Response `200`**: `{ "success": true, "message": "Invoice deleted" }`

---

## 14. Bulk Block

```
POST /automation/invoices/bulk-block
```

**Request Body**:
```json
{ "ids": ["uuid1", "uuid2"], "reason": "Bulk hold" }
```

---

## 15. Bulk Delete

```
POST /automation/invoices/bulk-delete
```

**Request Body**:
```json
{ "ids": ["uuid1", "uuid2"] }
```

---

## 16. Bulk Retry

```
POST /automation/invoices/bulk-retry
```

**Request Body**:
```json
{ "ids": ["uuid1", "uuid2"] }
```

---

## 17. Bulk Pause

```
POST /automation/invoices/bulk-pause
```

**Request Body**:
```json
{ "ids": ["uuid1", "uuid2"] }
```

---

## 18. Bulk Resume

```
POST /automation/invoices/bulk-resume
```

**Request Body**:
```json
{ "ids": ["uuid1", "uuid2"] }
```

---

## 19. Pause Invoice

```
POST /automation/invoice/{invoice_id}/pause
```

**Response `200`**: `{ "success": true, "message": "Invoice paused" }`

---

## 20. Resume Invoice

```
POST /automation/invoice/{invoice_id}/resume
```

**Response `200`**: `{ "success": true, "message": "Invoice resumed" }`

---

## 21. Single Invoice PDF

```
GET /automation/invoices/{invoice_id}/pdf?disposition=attachment
```

**Response `200`**: Binary PDF  
**Errors**: `400` (not in transferred status, missing USIN), `404`

---

## 22. Batch PDF

```
POST /automation/invoices/batch-pdf
```

**Request Body**:
```json
{ "ids": ["uuid1", "uuid2"] }
```

**Response `200`**: Binary PDF (all invoices concatenated)

---

## 23. Agent Health Check

```
GET /automation/health
```

**Response `200`**:
```json
{
  "status": "healthy",
  "timestamp": "2026-05-13T12:00:00Z",
  "database": "connected",
  "fbr_api": "reachable"
}
```

---

## 24. Agent Status Detail

```
GET /automation/agent/status
```

**Response `200`**:
```json
{
  "overall_status": "healthy",
  "pending_count": 200,
  "failed_count": 25,
  "processing_backlog": 50,
  "fbr_api_status": "reachable",
  "fbr_api_latency_ms": 450,
  "database_status": "connected",
  "database_latency_ms": 12,
  "agent_cpu_percent": 35.2,
  "agent_memory_mb": 512,
  "anomalies": [],
  "recommended_actions": []
}
```
