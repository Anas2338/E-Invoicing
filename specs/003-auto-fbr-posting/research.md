# Research & Technical Decisions: Auto FBR Posting

**Feature**: 003-auto-fbr-posting  
**Date**: 2026-05-01  
**Status**: Complete

## Overview

This document captures all technical research and decisions made during the planning phase for the auto FBR posting feature. All decisions are based on the clarified specification and existing project architecture.

---

## Decision 1: Time Window Logic with Midnight Spanning

**Context**: Users need to configure time windows for auto-posting (e.g., 9 AM - 6 PM). Some users may have night-shift operations or international business hours that span midnight.

**Decision**: Support time windows that cross midnight (e.g., 22:00-02:00 means active from 10 PM today until 2 AM tomorrow)

**Rationale**:
- Enables night-shift operations and international business hours
- Common pattern in scheduling systems
- Implementation complexity is manageable with proper date/time handling
- Provides maximum flexibility for diverse business needs

**Alternatives Considered**:
1. **Same-day only** (end time must be after start time on same day)
   - Rejected: Too restrictive, doesn't support legitimate night operations
2. **24-hour window** (user can set 00:00-23:59 for all-day posting)
   - Rejected: Doesn't provide time control, defeats purpose of time windows

**Implementation Approach**:
```python
def is_within_time_window(current_time: time, start_time: time, end_time: time) -> bool:
    """Check if current time is within configured window, handling midnight spans."""
    if start_time <= end_time:
        # Normal case: 09:00 - 18:00
        return start_time <= current_time <= end_time
    else:
        # Midnight-spanning case: 22:00 - 02:00
        return current_time >= start_time or current_time <= end_time
```

**Testing Requirements**:
- Test normal windows (9 AM - 6 PM)
- Test midnight-spanning windows (10 PM - 2 AM)
- Test edge cases (23:59 - 00:01, 00:00 - 23:59)
- Test timezone handling (all times in PKT)

---

## Decision 2: Daily Limit Reset Behavior

**Context**: Daily posting limits reset at midnight PKT. With midnight-spanning windows, there's ambiguity about when the limit should reset during an active window.

**Decision**: For midnight-spanning windows, continue using the previous day's limit until the window ends

**Rationale**:
- Prevents mid-window limit resets that would confuse users
- Provides predictable behavior (one limit per window session)
- Aligns with how most daily quota systems work
- Users get their full daily allocation for each calendar day

**Alternatives Considered**:
1. **Reset at midnight even mid-window** (user gets fresh limit at 12:00 AM while posting)
   - Rejected: Confusing behavior, could lead to unexpected posting resumption
2. **Split limit proportionally** (partial limit before midnight, remaining after)
   - Rejected: Too complex, hard to explain to users

**Implementation Approach**:
```python
class DailyPostingCounter:
    user_id: UUID
    date: date  # The calendar date for this counter
    posted_count: int
    window_start_date: date  # Track when window started for midnight spans
    
def get_daily_limit_for_window(user, current_datetime):
    """Get the applicable daily limit, considering midnight-spanning windows."""
    if is_midnight_spanning_window(user.start_time, user.end_time):
        # Use the date when the window started
        window_start_date = get_window_start_date(current_datetime, user.start_time)
        counter = get_counter(user.id, window_start_date)
    else:
        # Use current date
        counter = get_counter(user.id, current_datetime.date())
    
    return user.daily_limit - counter.posted_count
```

**Testing Requirements**:
- Test normal window limit reset (9 AM - 6 PM, resets at midnight)
- Test midnight-spanning window (10 PM - 2 AM, uses previous day's limit until 2 AM)
- Test limit enforcement at boundaries
- Test counter reset after window ends

---

## Decision 3: Network Failure Handling

**Context**: Network failures can occur after FBR accepts an invoice but before our system receives the confirmation response. This creates uncertainty about whether the invoice was posted.

**Decision**: Mark invoice as failed and require manual verification before reposting

**Rationale**:
- Prevents duplicate invoices in FBR system (critical for compliance)
- Safest approach when dealing with financial/legal documents
- Manual verification ensures user reviews the situation
- FBR API doesn't support idempotency keys or reliable query-by-invoice-number

**Alternatives Considered**:
1. **Retry the posting** (risk creating duplicate invoice in FBR)
   - Rejected: Could create duplicate invoices, legal/compliance risk
2. **Require FBR API to support idempotency keys**
   - Rejected: Not available in current FBR API
3. **Query FBR system for invoice existence before retry**
   - Rejected: No reliable query API available

**Implementation Approach**:
```python
async def post_invoice_to_fbr(invoice, user):
    try:
        response = await fbr_client.post_invoice(
            invoice_data=invoice.invoice_data,
            fbr_token=user.fbr_token,
            environment=user.auto_posting_environment,
            timeout=30.0
        )
        
        if response.success:
            invoice.status = InvoiceStatus.FBR_POSTED
            invoice.fbr_reference_number = response.reference_number
        else:
            invoice.status = InvoiceStatus.FBR_FAILED
            invoice.fbr_posting_error = response.error_message
            
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        # Network failure - uncertain if FBR received it
        invoice.status = InvoiceStatus.FBR_FAILED
        invoice.fbr_posting_error = (
            "Network failure during posting. Invoice may or may not have been "
            "accepted by FBR. Please verify manually before reposting to avoid duplicates."
        )
        invoice.fbr_retry_count = 999  # Mark as non-retryable
```

**Testing Requirements**:
- Test timeout scenarios
- Test network disconnection scenarios
- Test partial response scenarios
- Verify manual verification workflow

---

## Decision 4: Invoice Posting Concurrency

**Context**: The agent processes up to 10 invoices per user per cycle. Should these be posted sequentially or concurrently?

**Decision**: Sequential posting (post one invoice, wait for response, then post next)

**Rationale**:
- Simpler error handling (no race conditions)
- Respects FBR rate limits naturally
- Easier to debug and trace issues
- Predictable behavior for users
- Sufficient performance for initial implementation (can optimize later if needed)

**Alternatives Considered**:
1. **Concurrent posting** (post multiple invoices simultaneously)
   - Rejected: Complex error handling, potential race conditions, harder to debug
2. **Hybrid batching** (post 3-5 concurrently in batches)
   - Rejected: Premature optimization, adds complexity without proven need

**Implementation Approach**:
```python
async def process_user_invoices(user, invoices):
    """Process invoices sequentially for a user."""
    results = []
    
    for invoice in invoices:
        try:
            result = await post_invoice_to_fbr(invoice, user)
            results.append(result)
            
            # Stop if daily limit reached
            if len(results) >= user.auto_posting_daily_limit:
                break
                
        except Exception as e:
            logger.error(f"Failed to post invoice {invoice.id}: {e}")
            results.append({"success": False, "error": str(e)})
    
    return results
```

**Performance Analysis**:
- 10 invoices per user × 5 seconds per invoice = 50 seconds per user
- 100 users × 50 seconds = 5000 seconds if fully sequential
- With per-user parallelization: 50 seconds total (acceptable)
- Agent cycle target: < 30 seconds (achievable with optimization)

**Testing Requirements**:
- Test sequential processing order
- Test error handling doesn't block subsequent invoices
- Test daily limit enforcement mid-batch
- Performance test with 100 users

---

## Decision 5: Emergency Pause Behavior

**Context**: Users need an emergency pause button to immediately stop auto-posting. What should happen to their configuration?

**Decision**: Disable auto-posting entirely, requiring user to manually re-enable

**Rationale**:
- Safest for emergency situations (user detected an issue)
- Ensures user has resolved the issue before posting resumes
- Prevents auto-posting from resuming while problem still exists
- Clear, explicit control (no ambiguity about when it resumes)

**Alternatives Considered**:
1. **Temporary pause for 1 hour, then auto-resume**
   - Rejected: User might not have resolved issue in 1 hour
2. **Pause until end of current day, resume next day**
   - Rejected: Arbitrary timing, user might want to resume sooner or later
3. **Prompt user to choose pause duration**
   - Rejected: Adds complexity, emergency button should be one-click

**Implementation Approach**:
```python
@router.post("/invoices/emergency-pause")
async def emergency_pause_auto_posting(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """Emergency pause - disables auto-posting immediately."""
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Disable auto-posting
    user.auto_posting_enabled = False
    
    # Log the action
    log_config_change(
        user_id=user.id,
        action="emergency_pause",
        details={"timestamp": datetime.utcnow().isoformat()}
    )
    
    db.commit()
    
    return {
        "message": "Auto-posting disabled. Please re-enable in profile settings when ready.",
        "auto_posting_enabled": False
    }
```

**Testing Requirements**:
- Test emergency pause takes effect within 5 minutes (next agent cycle)
- Test user must explicitly re-enable in profile
- Test audit log captures emergency pause action

---

## Decision 6: Database Schema Strategy

**Context**: Need to store auto-posting configuration and track posting activity. Should we create new tables or extend existing ones?

**Decision**: Add columns to existing User table, extend Invoice status enum, create new tables for counters and logs

**Rationale**:
- Minimal schema changes (follows principle of smallest viable diff)
- Leverages existing infrastructure (User model, Invoice model)
- 1:1 relationship between User and auto-posting config (no need for separate table)
- New tables only for many-to-many or time-series data (counters, logs)

**Schema Changes**:

1. **User table extensions**:
   ```sql
   ALTER TABLE users ADD COLUMN auto_posting_enabled BOOLEAN DEFAULT FALSE;
   ALTER TABLE users ADD COLUMN auto_posting_start_time TIME DEFAULT '09:00:00';
   ALTER TABLE users ADD COLUMN auto_posting_end_time TIME DEFAULT '18:00:00';
   ALTER TABLE users ADD COLUMN auto_posting_environment VARCHAR(20) DEFAULT 'SANDBOX';
   ALTER TABLE users ADD COLUMN auto_posting_daily_limit INTEGER DEFAULT 100;
   ALTER TABLE users ADD COLUMN auto_posting_paused_until TIMESTAMP NULL;
   ```

2. **Invoice status enum extension**:
   ```sql
   ALTER TYPE invoice_status ADD VALUE 'FBR_POSTING';
   ALTER TYPE invoice_status ADD VALUE 'FBR_POSTED';
   ALTER TYPE invoice_status ADD VALUE 'FBR_FAILED';
   ```

3. **New table: daily_posting_counters**:
   ```sql
   CREATE TABLE daily_posting_counters (
       id UUID PRIMARY KEY,
       user_id UUID REFERENCES users(id),
       date DATE NOT NULL,
       posted_count INTEGER DEFAULT 0,
       window_start_date DATE NOT NULL,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW(),
       UNIQUE(user_id, date)
   );
   CREATE INDEX idx_daily_counters_user_date ON daily_posting_counters(user_id, date);
   ```

4. **New table: posting_logs**:
   ```sql
   CREATE TABLE posting_logs (
       id UUID PRIMARY KEY,
       user_id UUID REFERENCES users(id),
       invoice_id UUID REFERENCES invoices(id),
       action VARCHAR(20) NOT NULL,  -- 'auto' or 'manual'
       result VARCHAR(20) NOT NULL,  -- 'success' or 'failure'
       environment VARCHAR(20) NOT NULL,
       error_details JSONB NULL,
       agent_cycle_id VARCHAR(50) NULL,
       created_at TIMESTAMP DEFAULT NOW()
   );
   CREATE INDEX idx_posting_logs_user ON posting_logs(user_id);
   CREATE INDEX idx_posting_logs_invoice ON posting_logs(invoice_id);
   CREATE INDEX idx_posting_logs_created ON posting_logs(created_at);
   ```

**Alternatives Considered**:
1. **New auto_posting_config table**
   - Rejected: Overkill for 1:1 relationship, adds join complexity
2. **JSON column for all config**
   - Rejected: Harder to query, no type safety, no database constraints

**Migration Strategy**:
- Use Alembic for all schema changes
- Add columns with safe defaults (no breaking changes)
- Test migration on staging first
- Have rollback plan ready

---

## Decision 7: Agent Job Architecture

**Context**: Need to add FBR posting automation to the existing AI agent. Should we create a new agent process or extend the existing one?

**Decision**: Add new job to existing APScheduler instance in ai-agent/agent.py

**Rationale**:
- Reuses existing infrastructure (scheduler, database connections, logging)
- No new processes to manage
- Consistent with existing agent architecture
- Simpler deployment and monitoring

**Implementation Approach**:
```python
# In ai-agent/agent.py

def start(self):
    """Start the AI Agent scheduler."""
    # ... existing jobs ...
    
    # Add FBR posting job
    self.scheduler.add_job(
        func=self._post_to_fbr_job,
        trigger=IntervalTrigger(seconds=300),  # 5 minutes
        id='post_to_fbr',
        name='Auto Post to FBR',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    
def _post_to_fbr_job(self):
    """5-minute FBR posting job."""
    logger.info("Starting FBR posting cycle")
    
    with get_db_session() as db:
        # Get users with auto-posting enabled
        users = get_users_with_auto_posting_enabled(db)
        
        for user in users:
            # Check time window
            if not is_within_time_window(user):
                continue
            
            # Check daily limit
            if daily_limit_reached(user):
                continue
            
            # Get eligible invoices
            invoices = get_eligible_invoices(db, user, limit=10)
            
            # Post sequentially
            for invoice in invoices:
                post_invoice_to_fbr(invoice, user)
```

**Alternatives Considered**:
1. **Separate agent process**
   - Rejected: Unnecessary complexity, doubles infrastructure
2. **Cron job**
   - Rejected: Less flexible, harder to manage, no programmatic control

---

## Decision 8: Frontend State Management

**Context**: Frontend needs to display real-time auto-posting status and statistics. How should we handle state updates?

**Decision**: Use React hooks with API polling (30-second interval)

**Rationale**:
- Simple implementation, works with existing architecture
- No WebSocket infrastructure needed
- 30-second updates sufficient for this use case
- Easy to implement and maintain

**Implementation Approach**:
```typescript
// In AutoPostingStatus.tsx

const useAutoPostingStatus = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetchStatus = async () => {
      const data = await autoPostingApi.getStatus();
      setStatus(data);
      setLoading(false);
    };
    
    // Initial fetch
    fetchStatus();
    
    // Poll every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    
    return () => clearInterval(interval);
  }, []);
  
  return { status, loading };
};
```

**Alternatives Considered**:
1. **WebSocket for real-time updates**
   - Rejected: Overkill for 30-second updates, adds infrastructure complexity
2. **Server-Sent Events (SSE)**
   - Rejected: Adds complexity, not needed for this frequency

---

---

## Decision 9: Package Manager Selection

**Context**: Python projects require a package manager for dependency management. The project needs a fast, reliable tool for installing and managing Python packages.

**Decision**: Use `uv` as the Python package manager

**Rationale**:
- Extremely fast package installation (10-100x faster than pip)
- Written in Rust for performance and reliability
- Drop-in replacement for pip with better dependency resolution
- Supports virtual environments natively
- Modern tooling with excellent developer experience
- Growing adoption in Python community

**Alternatives Considered**:
1. **pip** (standard Python package manager)
   - Rejected: Slower installation, less reliable dependency resolution
2. **poetry** (dependency management and packaging)
   - Rejected: Slower than uv, more complex for simple dependency management
3. **pipenv** (pip + virtualenv wrapper)
   - Rejected: Slower than uv, less actively maintained

**Implementation Approach**:
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Install dependencies
uv pip install -r requirements.txt

# Add new dependency
uv pip install fastapi

# Sync dependencies
uv pip sync requirements.txt
```

**Migration from pip**:
- All existing `pip install` commands replaced with `uv pip install`
- All existing `requirements.txt` files remain compatible
- Virtual environment management simplified with `uv venv`

---

## Technology Stack Summary

### Backend
- **Framework**: FastAPI 0.104+
- **ORM**: SQLModel 0.0.14+
- **Database**: Neon PostgreSQL 15+
- **Scheduler**: APScheduler 3.10+
- **HTTP Client**: httpx 0.25+
- **Testing**: pytest 7.4+, pytest-asyncio
- **Package Manager**: uv (Rust-based, extremely fast)

### Frontend
- **Framework**: Next.js 16+
- **UI Library**: React 19
- **Language**: TypeScript 5+
- **HTTP Client**: fetch API (native)
- **Testing**: Jest 29+, React Testing Library 14+

### Infrastructure
- **Database**: Neon PostgreSQL (existing)
- **Agent**: Python 3.11 with APScheduler (existing)
- **Deployment**: Docker containers (existing)

---

## Performance Targets

1. **Agent Cycle Performance**:
   - Target: < 30 seconds for 100 concurrent users
   - Strategy: Per-user limit of 10 invoices, sequential processing
   - Monitoring: Log cycle duration, alert if > 30 seconds

2. **API Response Times**:
   - Manual posting: < 10 seconds (includes FBR API call)
   - Profile settings: < 2 seconds (database update only)
   - Status queries: < 1 second (simple SELECT)

3. **Database Query Optimization**:
   - Index on (user_id, auto_posting_enabled) for user filtering
   - Index on (user_id, status, scheduled_date) for invoice queries
   - Connection pooling (existing)

---

## Security Considerations

1. **Authentication**: All endpoints require JWT authentication
2. **Authorization**: Row-level isolation (users can only access their own data)
3. **FBR Credentials**: Validate before allowing Production posting
4. **Re-authentication**: Required when switching Sandbox → Production
5. **Audit Logging**: All configuration changes logged
6. **Input Validation**: Pydantic schemas for all API requests

---

## Monitoring & Observability

1. **Agent Metrics**:
   - Cycle duration
   - Invoices processed per cycle
   - Success/failure rates
   - FBR API response times

2. **Application Metrics**:
   - API endpoint response times
   - Database query performance
   - Error rates by endpoint

3. **Business Metrics**:
   - Daily posting volumes per user
   - Auto-posting adoption rate
   - Manual override frequency
   - Failure patterns

---

## Rollback Strategy

1. **Database**: Alembic downgrade removes new columns/tables
2. **Agent**: Disable job via config flag
3. **Frontend**: Feature flag to hide UI components
4. **API**: Endpoints return 503 if feature disabled

---

**Research Status**: ✅ Complete  
**All Decisions Documented**: Yes  
**Ready for Implementation**: Yes
