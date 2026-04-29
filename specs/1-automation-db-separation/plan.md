# Implementation Plan: Automation Database Separation

**Feature ID**: 1-automation-db-separation  
**Created**: 2026-04-24  
**Status**: In Planning  
**Estimated Effort**: 3-4 weeks

---

## Executive Summary

This plan outlines the implementation strategy for separating the automation system into its own isolated database with a daily data transfer mechanism. The AI agent will transfer validated invoices to the main database at 7 PM daily, where users can manually post them to FBR.

**Key Objectives**:
- Separate automation tables into dedicated Neon database
- Implement daily 7 PM transfer job using existing APScheduler
- Transform automation invoices to manual invoice format
- Remove FBR posting from AI agent (keep validation during upload)
- Implement 2-day cleanup job for automation database

---

## Technical Context

### Current Architecture

**Database**: Single PostgreSQL database (Neon)
- All tables in one database
- SQLModel/SQLAlchemy ORM
- Connection pooling configured
- SSL/TLS enforced

**Key Models**:
- `automation_invoice` - stores JSON blob in `invoice_data` field
- `invoice` (manual) - structured fields for invoice data
- `excel_upload_session` - tracks bulk uploads
- `automation_log` - audit trail
- `users` - authentication and authorization

**Scheduling Infrastructure**:
- Backend: APScheduler (AsyncIOScheduler) - runs daily FBR sync at 6 AM
- AI Agent: APScheduler (BackgroundScheduler) - processes invoices every 5 minutes

**Current Flow**:
1. User uploads Excel → validates with FBR → stores in `automation_invoice`
2. AI agent queries validated invoices every 5 minutes
3. AI agent posts to FBR at scheduled time
4. Invoice marked as SUBMITTED

### Target Architecture

**Two Databases**:
1. **Main Database** (existing Neon project)
   - `users` table
   - `invoice` table (manual invoices)
   - FBR master data tables
   - User authentication data

2. **Automation Database** (new Neon project)
   - `automation_invoice` table
   - `excel_upload_session` table
   - `automation_log` table
   - `transfer_log` table (new)

**New Flow**:
1. User uploads Excel → validates with FBR → stores in automation DB
2. Daily at 7 PM: Transfer job queries validated invoices
3. Transfer job transforms and inserts into main DB as manual invoices
4. Users see transferred invoices in history with "validated" status
5. Users manually post to FBR
6. Cleanup job deletes automation data older than 2 days

---

## Architecture Decisions

### AD-1: Database Separation Strategy

**Decision**: Use two separate Neon database projects

**Rationale**:
- Complete isolation for backup, scaling, and maintenance
- Aligns with user requirement for "separate neon database project"
- Allows independent connection pooling and resource allocation
- Clear separation of concerns

**Alternatives Considered**:
- PostgreSQL schemas (same DB, logical separation) - rejected because user specifically requested separate Neon project
- Read replicas - doesn't provide write isolation
- Table partitioning - doesn't provide database-level isolation

**Trade-offs**:
- ✅ Complete isolation
- ✅ Independent scaling
- ❌ No foreign key constraints across databases
- ❌ No atomic transactions across databases
- ❌ Application-level consistency required

### AD-2: Data Transfer Mechanism

**Decision**: Scheduled batch transfer at 7 PM daily using APScheduler

**Rationale**:
- APScheduler already running in backend
- Simple, predictable, and testable
- Aligns with user requirement for "7:00 pm everyday"
- Low complexity compared to real-time sync

**Alternatives Considered**:
- Real-time CDC (Change Data Capture) - too complex, not required
- Message queue (RabbitMQ/Kafka) - overkill for daily batch
- Manual trigger only - doesn't meet automation requirement

**Implementation**:
- Add new job to `backend/src/services/scheduler.py`
- Use CronTrigger for 19:00 PKT daily
- Query automation DB for validated invoices
- Transform and insert into main DB
- Mark as transferred in automation DB

### AD-3: Invoice Status After Transfer

**Decision**: Transferred invoices have "validated" status (ready to post)

**Rationale**:
- User selected Option B in clarification session
- Faster workflow - users can post immediately
- FBR validation already happened during upload
- Users can still edit if needed

**Implementation**:
- Set `status = 'validated'` on manual invoice creation
- Add `source = 'automation'` metadata field
- Add `transferred_at` timestamp field

### AD-4: FBR Validation Timing

**Decision**: Keep FBR validation during Excel upload (current behavior)

**Rationale**:
- User selected Option A in clarification session
- Catches errors early, provides immediate feedback
- Only validated invoices are transferred
- AI agent never posts to FBR (only validates during upload)

**Implementation**:
- Keep existing validation logic in `backend/src/api/v1/automation/excel.py`
- Remove FBR posting from `ai-agent/agent.py`
- AI agent only transfers data, never calls FBR post endpoint

### AD-5: Data Transformation Strategy

**Decision**: Transform JSON blob to structured fields during transfer

**Rationale**:
- Manual invoice model uses structured fields
- Allows proper indexing and querying in main DB
- Maintains data integrity and validation

**Implementation**:
- Parse `invoice_data` JSON from automation_invoice
- Map to manual invoice structured fields
- Validate required fields during transformation
- Log transformation errors for debugging

### AD-6: Error Handling and Recovery

**Decision**: Mark failed transfers as "transfer_failed" with manual retry

**Rationale**:
- Simple and safe - no data loss
- Admin can investigate and fix issues
- Prevents infinite retry loops
- Maintains audit trail

**Implementation**:
- Wrap each invoice transfer in try-catch
- Log errors with invoice ID and stack trace
- Update automation_invoice status to "transfer_failed"
- Provide admin endpoint to retry failed transfers

### AD-7: Cleanup Strategy

**Decision**: Daily cleanup job at 2 AM deleting data older than 2 days

**Rationale**:
- Prevents database bloat
- 2-day retention allows for recovery window
- Off-peak time (2 AM) minimizes impact
- Preserves audit logs separately

**Implementation**:
- Add cleanup job to `backend/src/services/scheduler.py`
- Delete automation_invoice records where `created_at < NOW() - INTERVAL '2 days'`
- Delete associated upload_session records
- Keep automation_log for audit (configurable retention)

---

## Implementation Phases

### Phase 0: Research & Setup (2-3 days)

**Objectives**:
- Set up second Neon database
- Configure multi-database connections
- Update Alembic for two databases

**Tasks**:
1. Create new Neon project for automation database
2. Add `AUTOMATION_DATABASE_URL` environment variable
3. Create second SQLAlchemy engine in `backend/src/database/session.py`
4. Create `get_automation_db()` dependency function
5. Configure Alembic for multi-database migrations
6. Create initial migration for automation database schema

**Deliverables**:
- New Neon project created
- Environment variables configured
- Multi-database session management working
- Alembic configured for both databases

### Phase 1: Database Migration (3-4 days)

**Objectives**:
- Move automation tables to new database
- Migrate existing data
- Update all automation endpoints

**Tasks**:
1. Create automation database schema (automation_invoice, excel_upload_session, automation_log)
2. Add new `transfer_log` table to automation database
3. Create data migration script to copy existing automation data
4. Update all automation API endpoints to use `get_automation_db()`
5. Update AI agent to connect to automation database
6. Test data migration with rollback plan

**Files to Modify**:
- `backend/src/database/session.py` - add automation DB engine
- `backend/src/models/automation_invoice.py` - update table metadata
- `backend/src/models/excel_upload_session.py` - update table metadata
- `backend/src/api/v1/automation/*.py` - use automation DB session
- `ai-agent/agent.py` - connect to automation DB

**Deliverables**:
- Automation tables in separate database
- All automation endpoints using automation DB
- Data migration script tested
- Rollback plan documented

### Phase 2: Transfer Job Implementation (4-5 days)

**Objectives**:
- Implement daily 7 PM transfer job
- Transform automation invoices to manual format
- Handle errors and logging

**Tasks**:
1. Create `TransferService` class in `backend/src/services/transfer_service.py`
2. Implement `transfer_validated_invoices()` method
3. Implement JSON to structured field transformation
4. Add transfer job to scheduler at 7 PM PKT
5. Create `transfer_log` table and logging logic
6. Implement duplicate prevention (check if already transferred)
7. Add admin endpoint to manually trigger transfer
8. Add admin endpoint to retry failed transfers

**Key Methods**:
```python
class TransferService:
    def transfer_validated_invoices(self, automation_db, main_db):
        # Query validated invoices from automation DB
        # For each invoice:
        #   - Transform JSON to structured format
        #   - Insert into main DB as manual invoice
        #   - Mark as transferred in automation DB
        #   - Log transfer
        
    def transform_invoice_data(self, automation_invoice):
        # Parse invoice_data JSON
        # Map to manual invoice fields
        # Return manual invoice object
        
    def retry_failed_transfers(self, automation_db, main_db):
        # Query transfer_failed invoices
        # Retry transfer
```

**Files to Create**:
- `backend/src/services/transfer_service.py`
- `backend/src/models/transfer_log.py`
- `backend/src/api/v1/admin/transfer.py` (admin endpoints)

**Files to Modify**:
- `backend/src/services/scheduler.py` - add transfer job
- `backend/src/models/automation_invoice.py` - add transfer_failed status
- `backend/src/models/invoice.py` - add source and transferred_at fields

**Deliverables**:
- Transfer job running at 7 PM daily
- Invoices successfully transferred to main DB
- Error handling and logging working
- Admin endpoints for manual trigger and retry

### Phase 3: AI Agent Modifications (2-3 days)

**Objectives**:
- Remove FBR posting from AI agent
- Keep validation during upload
- Update AI agent to only monitor (no posting)

**Tasks**:
1. Remove FBR posting logic from `ai-agent/agent.py`
2. Remove or disable `FBRPosterSkill`
3. Update AI agent to log that manual posting is required
4. Keep FBR validation in Excel upload endpoint
5. Update AI agent documentation
6. Test that AI agent no longer posts to FBR

**Files to Modify**:
- `ai-agent/agent.py` - remove posting logic (lines 229-246)
- `ai-agent/skills/fbr_poster.py` - disable or remove
- `backend/src/api/v1/automation/excel.py` - keep validation logic

**Deliverables**:
- AI agent no longer posts to FBR
- FBR validation still works during upload
- AI agent logs and monitors only

### Phase 4: Cleanup Job Implementation (1-2 days)

**Objectives**:
- Implement daily cleanup job
- Delete old automation data
- Preserve audit logs

**Tasks**:
1. Create `CleanupService` class in `backend/src/services/cleanup_service.py`
2. Implement `cleanup_old_automation_data()` method
3. Add cleanup job to scheduler at 2 AM PKT
4. Configure retention periods via environment variables
5. Add logging for cleanup operations
6. Test cleanup with various data scenarios

**Key Methods**:
```python
class CleanupService:
    def cleanup_old_automation_data(self, automation_db):
        # Delete automation_invoice older than 2 days
        # Delete excel_upload_session older than 2 days
        # Keep automation_log (configurable retention)
        # Log cleanup results
```

**Files to Create**:
- `backend/src/services/cleanup_service.py`

**Files to Modify**:
- `backend/src/services/scheduler.py` - add cleanup job
- `backend/src/config/settings.py` - add retention period config

**Deliverables**:
- Cleanup job running at 2 AM daily
- Old data deleted successfully
- Audit logs preserved
- Configurable retention periods

### Phase 5: Frontend Updates (2-3 days)

**Objectives**:
- Display transferred invoices in history
- Show invoice source metadata
- Allow filtering by source

**Tasks**:
1. Update invoice history API to include source field
2. Add source filter to invoice history UI
3. Display "Transferred from Automation" badge
4. Show transfer timestamp in invoice details
5. Test invoice posting workflow for transferred invoices

**Files to Modify**:
- `frontend/src/app/(protected)/invoices/history/page.tsx` - add source filter
- `frontend/src/components/invoice-card.tsx` - show source badge
- `backend/src/api/v1/invoices.py` - include source in response

**Deliverables**:
- Users can see transferred invoices
- Source is clearly indicated
- Filtering by source works
- Posting workflow unchanged

### Phase 6: Testing & Documentation (3-4 days)

**Objectives**:
- Comprehensive testing of all components
- Document new architecture
- Create runbooks for operations

**Tasks**:
1. Write unit tests for TransferService
2. Write unit tests for CleanupService
3. Write integration tests for transfer job
4. Write integration tests for cleanup job
5. Test error scenarios and recovery
6. Load test with 1000+ invoices
7. Document multi-database setup
8. Create admin runbook for transfer failures
9. Update API documentation

**Test Scenarios**:
- Happy path: upload → validate → transfer → post
- Transfer failure: database down, network error
- Duplicate prevention: same invoice transferred twice
- Cleanup: verify old data deleted, audit logs preserved
- Load: 1000 invoices transferred in < 10 minutes
- Recovery: retry failed transfers successfully

**Deliverables**:
- Test suite with >80% coverage
- All test scenarios passing
- Documentation updated
- Runbooks created

---

## Data Model Changes

### New Fields in `invoice` (Main Database)

```python
class Invoice(Base):
    # ... existing fields ...
    
    # New fields for automation support
    source: str = Field(default="manual")  # "manual" or "automation"
    transferred_at: Optional[datetime] = Field(default=None)
    automation_invoice_id: Optional[UUID] = Field(default=None)  # Reference to original
```

### New Status in `automation_invoice` (Automation Database)

```python
class AutomationInvoiceStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    TRANSFERRED = "transferred"  # New status
    TRANSFER_FAILED = "transfer_failed"  # New status
    EXPIRED = "expired"
    FAILED = "failed"
```

### New Table: `transfer_log` (Automation Database)

```python
class TransferLog(Base):
    __tablename__ = "transfer_log"
    
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transfer_timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str  # "success", "partial_success", "failed"
    invoices_transferred: int
    invoices_failed: int
    error_details: Optional[str]
    duration_seconds: float
```

---

## API Changes

### New Admin Endpoints

**POST /api/v1/admin/transfer/trigger**
- Manually trigger transfer job
- Requires admin role
- Returns transfer summary

**POST /api/v1/admin/transfer/retry**
- Retry failed transfers
- Requires admin role
- Body: `{ "invoice_ids": ["uuid1", "uuid2"] }`

**GET /api/v1/admin/transfer/logs**
- View transfer logs
- Requires admin role
- Query params: `?limit=50&status=failed`

### Modified Endpoints

**GET /api/v1/invoices/history**
- Add `source` field to response
- Add `transferred_at` field to response
- Add `?source=automation` filter

---

## Configuration Changes

### Environment Variables

```bash
# New variables
AUTOMATION_DATABASE_URL=postgresql://....
TRANSFER_SCHEDULE_HOUR=19  # 7 PM PKT
TRANSFER_SCHEDULE_MINUTE=0
CLEANUP_SCHEDULE_HOUR=2  # 2 AM PKT
CLEANUP_RETENTION_DAYS=2
AUTOMATION_LOG_RETENTION_DAYS=90

# Existing variables (no changes)
DATABASE_URL=postgresql://....
```

### Scheduler Configuration

```python
# backend/src/services/scheduler.py

# New jobs
scheduler.add_job(
    transfer_validated_invoices,
    trigger=CronTrigger(hour=19, minute=0, timezone=PAKISTAN_TZ),
    id='daily_invoice_transfer',
    name='Daily Invoice Transfer (7 PM PKT)',
    replace_existing=True,
    max_instances=1
)

scheduler.add_job(
    cleanup_old_automation_data,
    trigger=CronTrigger(hour=2, minute=0, timezone=PAKISTAN_TZ),
    id='daily_automation_cleanup',
    name='Daily Automation Data Cleanup (2 AM PKT)',
    replace_existing=True,
    max_instances=1
)
```

---

## Migration Strategy

### Step 1: Pre-Migration Preparation

1. Backup both databases
2. Create new Neon project for automation
3. Test connection to both databases
4. Verify all environment variables

### Step 2: Schema Migration

1. Run Alembic migrations on automation database
2. Verify schema matches expectations
3. Test CRUD operations on both databases

### Step 3: Data Migration

1. Copy existing automation_invoice records to automation DB
2. Copy existing excel_upload_session records to automation DB
3. Copy existing automation_log records to automation DB
4. Verify data integrity (row counts, checksums)

### Step 4: Code Deployment

1. Deploy backend changes (multi-database support)
2. Deploy AI agent changes (connect to automation DB)
3. Verify all automation endpoints work
4. Monitor for errors

### Step 5: Transfer Job Activation

1. Deploy transfer job code
2. Test manual trigger first
3. Verify invoices transferred correctly
4. Enable scheduled job

### Step 6: Cleanup Job Activation

1. Deploy cleanup job code
2. Test with short retention period first
3. Verify correct data deleted
4. Enable scheduled job with 2-day retention

### Rollback Plan

If issues occur:
1. Stop transfer and cleanup jobs
2. Revert code deployment
3. Point all automation endpoints back to main DB
4. Restore from backup if data corruption
5. Investigate and fix issues
6. Retry migration

---

## Testing Strategy

### Unit Tests

- `TransferService.transfer_validated_invoices()`
- `TransferService.transform_invoice_data()`
- `CleanupService.cleanup_old_automation_data()`
- Multi-database session management

### Integration Tests

- End-to-end transfer flow
- End-to-end cleanup flow
- Error handling and recovery
- Duplicate prevention
- Admin endpoints

### Load Tests

- Transfer 1000 invoices in < 10 minutes
- Concurrent transfers (multiple users)
- Database connection pooling under load

### Manual Tests

- Upload Excel → validate → transfer → post
- Transfer failure scenarios
- Cleanup verification
- Admin operations

---

## Monitoring & Observability

### Metrics to Track

- Transfer job success rate
- Transfer job duration
- Number of invoices transferred per day
- Number of failed transfers
- Cleanup job success rate
- Automation database size
- Main database size

### Alerts

- Transfer job failure
- Transfer job duration > 15 minutes
- Failed transfer count > 10
- Cleanup job failure
- Automation database size > threshold

### Logging

- All transfer operations (success and failure)
- All cleanup operations
- Database connection errors
- Transformation errors
- Admin actions (manual trigger, retry)

---

## Security Considerations

### Database Access

- Separate credentials for each database
- Least privilege principle (read/write only where needed)
- SSL/TLS enforced for all connections
- Connection strings in environment variables (not code)

### User Isolation

- Users can only access their own invoices in both databases
- Admin-only endpoints for transfer operations
- Audit trail for all admin actions

### Data Protection

- No sensitive data in logs
- Encryption at rest (Neon default)
- Encryption in transit (SSL/TLS)
- Regular backups of both databases

---

## Performance Considerations

### Database Queries

- Index on `automation_invoice.status` for transfer queries
- Index on `automation_invoice.scheduled_date` for transfer queries
- Index on `automation_invoice.created_at` for cleanup queries
- Index on `invoice.source` for filtering

### Connection Pooling

- Separate connection pools for each database
- Pool size: 5 ready + 10 overflow per database
- Connection recycling every 5 minutes

### Transfer Optimization

- Batch insert into main database (100 invoices at a time)
- Parallel processing (5 workers)
- Transaction per invoice (atomic)
- Progress logging every 100 invoices

---

## Risks & Mitigation

### Risk 1: Transfer Job Failure

**Impact**: Users don't see their invoices  
**Probability**: Medium  
**Mitigation**:
- Comprehensive error handling
- Automatic retry for transient errors
- Admin alert on failure
- Manual trigger endpoint for recovery

### Risk 2: Data Inconsistency

**Impact**: Invoices in wrong state  
**Probability**: Low  
**Mitigation**:
- Atomic transactions per invoice
- Duplicate prevention checks
- Audit trail for all operations
- Rollback capability

### Risk 3: Performance Degradation

**Impact**: Slow transfer, timeout  
**Probability**: Low  
**Mitigation**:
- Load testing before deployment
- Batch processing
- Connection pooling
- Monitoring and alerts

### Risk 4: Database Connection Issues

**Impact**: Transfer fails, data not accessible  
**Probability**: Low  
**Mitigation**:
- Connection retry logic
- Health checks
- Fallback to manual trigger
- Monitoring and alerts

---

## Success Criteria

### Functional

- ✅ Automation tables in separate database
- ✅ Transfer job runs at 7 PM daily
- ✅ Invoices transferred with "validated" status
- ✅ Users can post transferred invoices manually
- ✅ Cleanup job deletes data older than 2 days
- ✅ AI agent does not post to FBR
- ✅ FBR validation works during upload

### Non-Functional

- ✅ Transfer of 1000 invoices completes in < 10 minutes
- ✅ Transfer success rate > 99.9%
- ✅ Automation database size remains stable
- ✅ No data loss during transfer
- ✅ Failed transfers can be recovered within 1 hour

### User Experience

- ✅ Users see transferred invoices in history
- ✅ Users can filter by source
- ✅ Users can post transferred invoices
- ✅ Users can edit transferred invoices before posting

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 0: Research & Setup | 2-3 days | None |
| Phase 1: Database Migration | 3-4 days | Phase 0 |
| Phase 2: Transfer Job | 4-5 days | Phase 1 |
| Phase 3: AI Agent Modifications | 2-3 days | Phase 1 |
| Phase 4: Cleanup Job | 1-2 days | Phase 1 |
| Phase 5: Frontend Updates | 2-3 days | Phase 2 |
| Phase 6: Testing & Documentation | 3-4 days | All phases |

**Total Estimated Duration**: 17-24 days (3-4 weeks)

---

## Next Steps

1. Review and approve this plan
2. Create new Neon project for automation database
3. Set up development environment with two databases
4. Begin Phase 0: Research & Setup
5. Create detailed tasks in `/sp.tasks`

---

## Appendix

### Related Documents

- [Feature Specification](./spec.md)
- [Requirements Checklist](./checklists/requirements.md)
- [Data Model](./data-model.md) (to be created)
- [API Contracts](./contracts/) (to be created)

### References

- [Neon Multi-Database Documentation](https://neon.tech/docs)
- [SQLAlchemy Multi-Database Patterns](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
