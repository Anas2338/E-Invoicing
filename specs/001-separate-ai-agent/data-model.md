# Data Model: Separate AI-Agent from Main Backend

**Feature**: 001-separate-ai-agent  
**Date**: 2026-05-13

## Overview

Two databases already exist and remain unchanged. This document maps which entities belong to which database and service after separation.

---

## Main Database (Backend Service)

Tables managed by the main backend. No automation tables exist here.

| Entity | Table | Service | Notes |
|--------|-------|---------|-------|
| User | `user` | Backend | Includes `automation_enabled` flag (boolean) — enables/disables automation UI access per user |
| Invoice | `invoice` | Backend | Manual invoices only (current/past dates). Has `automation_invoice_id` (nullable UUID) for traceability to source automation invoice |
| FBRResponse | `fbr_response` | Backend | FBR API responses for manual invoice submissions |
| FBRProvince | `fbr_province` | Backend | FBR master data |
| FBRUOM | `fbr_uom` | Backend | FBR unit of measure codes |
| FBRHSCode | `fbr_hs_code` | Backend | FBR harmonized system codes |
| FBRTransactionType | `fbr_transaction_type` | Backend | FBR transaction types |
| FBRInvoiceType | `fbr_invoice_type` | Backend | FBR invoice types |
| FBRSyncLog | `fbr_sync_log` | Backend | FBR master data sync audit |
| FBRChangeNotification | `fbr_change_notification` | Backend | FBR master data change tracking |
| FBRDataSnapshot | `fbr_data_snapshot` | Backend | FBR master data snapshots |
| UserSavedProduct | `user_saved_product` | Backend | User's saved product/item library |
| IdempotencyCache | `idempotency_cache` | Backend | Prevent duplicate FBR API calls |
| PostingLog | `posting_log` | Backend | FBR posting audit trail |
| DailyPostingCounter | `daily_posting_counter` | Backend | Rate limit tracking per user |

### Invoice Model (Main DB) — Relevant Fields

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `id` | UUID | No | Primary key |
| `external_id` | str | No | Invoice number |
| `user_id` | UUID | No | Owner (indexed, no FK to automation DB) |
| `invoice_data` | JSON | Yes | Structured invoice payload |
| `status` | enum | No | DRAFT → VALIDATED → TRANSFERRED → POSTED → FAILED |
| `source` | enum | No | `manual` or `automation` |
| `automation_invoice_id` | UUID | **Yes** | Reference to original automation invoice (nullable, no FK constraint) |
| `transferred_at` | datetime | Yes | When transferred from automation |
| `environment` | enum | No | SANDBOX or PRODUCTION |

**Change**: `automation_invoice_id` becomes nullable with no cross-DB FK. The main backend no longer resolves this reference — the frontend uses it to fetch automation details from the AI-agent when needed.

---

## Automation Database (AI-Agent Service)

Tables managed exclusively by the AI-agent service.

| Entity | Table | Service | Notes |
|--------|-------|---------|-------|
| AutomationInvoice | `automation_invoice` | AI-agent | Future-date invoices from Excel upload |
| AutomationLog | `automation_log` | AI-agent | Audit trail of automation actions |
| ExcelUploadSession | `excel_upload_session` | AI-agent | Tracks bulk Excel upload processing |
| AIAgentHealthCheck | `ai_agent_health_check` | AI-agent | Periodic agent health snapshots |

### AutomationInvoice

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `id` | UUID | No | Primary key |
| `user_id` | UUID | No | Owner (indexed, no FK to main DB) |
| `invoice_number` | str | No | Unique per upload session |
| `invoice_data` | JSON | No | Full FBR invoice payload |
| `scheduled_date` | date | No | Future date for FBR submission |
| `scheduled_time` | time | Yes | Specific time for submission |
| `status` | enum | No | PENDING → VALIDATED → TRANSFERRED → TRANSFER_FAILED / FAILED / EXPIRED / BLOCKED / PAUSED |
| `source` | str | No | Source identifier (e.g., "excel_upload") |
| `retry_count` | int | No | Number of retry attempts |
| `priority` | int | Yes | Processing priority |
| `fbr_response` | JSON | Yes | FBR API response after submission |
| `transfer_error` | str | Yes | Error message if transfer failed |
| `transferred_at` | datetime | Yes | When transferred to main DB |
| `upload_session_id` | UUID | Yes | FK to ExcelUploadSession |

### AutomationLog

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `id` | UUID | No | Primary key |
| `automation_invoice_id` | UUID | No | FK to AutomationInvoice |
| `action` | enum | No | VALIDATE, SUBMIT, RETRY, BLOCK, UNBLOCK, PAUSE, RESUME, DELETE, TRANSFER |
| `status` | enum | No | SUCCESS, FAILURE, IN_PROGRESS |
| `details` | JSON | Yes | Action-specific metadata |
| `created_at` | datetime | No | Timestamp |

### ExcelUploadSession

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `id` | UUID | No | Primary key |
| `user_id` | UUID | No | Uploader |
| `original_filename` | str | No | Original Excel filename |
| `file_path` | str | Yes | Storage path (if persisting file) |
| `total_rows` | int | No | Total rows in Excel |
| `processed_rows` | int | No | Rows processed so far |
| `processing_status` | enum | No | PENDING → PROCESSING → COMPLETED → FAILED |
| `error_message` | str | Yes | Failure reason |
| `created_at` | datetime | No | Upload timestamp |

### AIAgentHealthCheck

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `id` | UUID | No | Primary key |
| `check_timestamp` | datetime | No | When check was performed |
| `overall_status` | str | No | HEALTHY / DEGRADED / UNHEALTHY |
| `pending_invoice_count` | int | No | Invoices awaiting processing |
| `failed_invoice_count` | int | No | Failed invoice count |
| `processing_backlog` | int | No | Backlog depth |
| `fbr_api_status` | str | Yes | FBR API reachability |
| `fbr_api_latency_ms` | float | Yes | FBR API response time |
| `database_status` | str | Yes | DB connectivity |
| `database_latency_ms` | float | Yes | DB response time |
| `agent_cpu_percent` | float | Yes | CPU usage |
| `agent_memory_mb` | float | Yes | Memory usage |
| `anomalies` | JSON | Yes | Detected anomalies |
| `recommended_actions` | JSON | Yes | Suggested remediation |

## Cross-Database References

- `Invoice.automation_invoice_id` → `AutomationInvoice.id`: Logical reference only (no FK). The main backend does NOT join across databases. The frontend resolves this by calling the AI-agent's invoice detail endpoint.
- `AutomationInvoice.user_id` → `User.id`: Logical reference (no FK since User table is in main DB). The AI-agent uses user_id for ownership checks but does not query User data.

## State Transitions

### AutomationInvoice Status Flow

```
PENDING ──→ VALIDATED ──→ TRANSFERRED
   │            │               │
   ├─→ EXPIRED  ├─→ PAUSED      └─→ (manual Invoice created in main DB)
   │            │     │
   └─→ FAILED   └─→ RESUME → VALIDATED
                     │
                     └─→ BLOCKED → (end)
```

- **PENDING**: Just uploaded, awaiting background validation
- **EXPIRED**: Scheduled date has passed without validation
- **FAILED**: Validation failed (errors stored)
- **VALIDATED**: Passed local + FBR validation
- **PAUSED**: User paused processing (can resume)
- **BLOCKED**: User explicitly blocked from FBR submission
- **TRANSFERRED**: Successfully moved to main database as an Invoice record
- **TRANSFER_FAILED**: Transfer to main DB failed

### Invoice (Manual) Status Flow (unchanged)

```
DRAFT → VALIDATED → TRANSFERRED → POSTED
                          └─→ FAILED
```
