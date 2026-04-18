# Invoice Status Flow - Complete Implementation

## Status Definitions

### PENDING
- **Set when**: Validation fails during Excel upload
- **Meaning**: Invoice has validation errors, user can retry
- **User action**: Click retry button to re-validate
- **AI agent**: Ignores (doesn't process)

### VALIDATED  
- **Set when**: Validation passes (upload or retry)
- **Meaning**: Invoice is valid and ready for FBR submission
- **User action**: Wait for AI agent (processes every 5 minutes)
- **AI agent**: Picks up and submits to FBR

### FAILED
- **Set when**: FBR submission fails (after validation passed)
- **Meaning**: Invoice was valid but FBR rejected it during submission
- **User action**: Cannot retry (submission error, not validation error)
- **AI agent**: No longer processes (final failure state)

### SUBMITTED
- **Set when**: FBR submission succeeds
- **Meaning**: Invoice successfully posted to FBR
- **User action**: None (final success state)
- **AI agent**: No longer processes (final success state)

### EXPIRED
- **Set when**: Scheduled time is in the past
- **Meaning**: Invoice missed its submission window
- **User action**: Cannot retry (too late)
- **AI agent**: Ignores (doesn't process)

## Complete Flow

### Scenario 1: Upload with 1 Valid + 1 Invalid Invoice

```
User uploads Excel with 2 invoices
↓
Backend validates each invoice
↓
Invoice 1: Validation passes
  → Status = VALIDATED ✅
  → Dashboard shows: "1 Validated"
  
Invoice 2: Validation fails
  → Status = PENDING ⏳
  → Dashboard shows: "1 Pending" with retry button
```

### Scenario 2: User Retries Pending Invoice

```
User clicks retry on Pending invoice
↓
Backend re-validates immediately
↓
Case A: Validation passes
  → Status = PENDING → VALIDATED ✅
  → Dashboard shows: "2 Validated"
  → AI agent will submit both in next cycle
  
Case B: Validation still fails
  → Status = PENDING (stays) ⏳
  → Error message updated
  → Dashboard shows: "1 Validated, 1 Pending"
  → User can retry again
```

### Scenario 3: AI Agent Processes Validated Invoices

```
AI Agent runs (every 5 minutes)
↓
Finds 2 VALIDATED invoices
↓
For each invoice:
  1. Get user's FBR token
  2. Submit to FBR API
  ↓
  Case A: Submission succeeds
    → Status = VALIDATED → SUBMITTED ✅
    → Dashboard shows: "1 Submitted"
    
  Case B: Submission fails (transient error)
    → Status = VALIDATED (stays) ⏳
    → Retry count incremented
    → AI agent will retry in next cycle
    
  Case C: Submission fails (permanent error or max retries)
    → Status = VALIDATED → FAILED ❌
    → Dashboard shows: "1 Failed"
    → User CANNOT retry (submission error, not validation)
```

## Status Transition Diagram

```
Excel Upload
    ↓
[Validation]
    ↓
    ├─ Valid → VALIDATED ──────────┐
    │                              ↓
    └─ Invalid → PENDING ─→ [Retry] ─→ Valid → VALIDATED
                    ↑                              ↓
                    └─ Invalid ←──────────────────┘
                                                   ↓
                                            [AI Agent Submit]
                                                   ↓
                                    ├─ Success → SUBMITTED ✅
                                    │
                                    ├─ Transient Error → VALIDATED (retry)
                                    │
                                    └─ Permanent Error → FAILED ❌
```

## Dashboard Display

| Status | Count Label | Color | Action Button |
|--------|-------------|-------|---------------|
| PENDING | "X Pending" | Yellow | Retry ↻ |
| VALIDATED | "X Validated" | Blue | None (wait) |
| SUBMITTED | "X Submitted" | Green | None (done) |
| FAILED | "X Failed" | Red | None (cannot retry) |
| EXPIRED | "X Expired" | Gray | None (too late) |

## Key Changes Made

### 1. Excel Upload (`excel.py`)
**Before**: Validation failure → FAILED
**After**: Validation failure → PENDING

### 2. Retry Endpoint (`retry.py`)
**Before**: Accepts FAILED status
**After**: Accepts PENDING status

### 3. Retry Service (`automation_service.py`)
**Before**: Changes FAILED → PENDING
**After**: Changes PENDING → VALIDATED (if valid) or stays PENDING (if invalid)

### 4. AI Agent (`agent.py`)
**No changes needed** - Already only processes VALIDATED and only sets FAILED for submission failures

## Testing Checklist

- [ ] Upload Excel with valid invoice → Shows as VALIDATED
- [ ] Upload Excel with invalid invoice → Shows as PENDING with retry button
- [ ] Click retry on PENDING (still invalid) → Stays PENDING with updated error
- [ ] Click retry on PENDING (now valid) → Changes to VALIDATED
- [ ] Wait 5 minutes → AI agent submits VALIDATED invoices
- [ ] Submission succeeds → Shows as SUBMITTED
- [ ] Submission fails → Shows as FAILED (no retry button)
- [ ] Dashboard counts are correct for each status

## Benefits

✅ **Clear separation**: Validation errors (PENDING) vs Submission errors (FAILED)
✅ **User control**: Can retry validation errors, cannot retry submission errors
✅ **Immediate feedback**: Retry validates immediately, user knows if it will work
✅ **AI agent simplicity**: Only processes VALIDATED, only sets FAILED for submission
✅ **Consistent flow**: All VALIDATED invoices are truly validated and ready
