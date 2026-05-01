# Quickstart Guide: Auto FBR Posting

**Feature**: 003-auto-fbr-posting  
**Date**: 2026-05-01  
**For**: Developers implementing the auto FBR posting feature

## Overview

This guide provides a quick reference for implementing the auto FBR posting feature. For detailed information, refer to the full planning documents.

---

## 🎯 What This Feature Does

Enables users to configure automatic FBR posting for validated invoices with:
- Time-based scheduling (configurable start/end times, supports midnight-spanning)
- Daily posting limits (1-1000 invoices per day)
- Environment selection (Sandbox/Production)
- Manual override capability (post anytime regardless of settings)
- Emergency pause button (immediate disable)

---

## 📋 Prerequisites

- Existing User model with FBR credentials
- Existing Invoice model with TRANSFERRED status
- Existing AI agent with APScheduler
- Existing FBRClient for posting to FBR API
- PostgreSQL database (Neon)
- **uv** package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

---

## 🚀 Quick Implementation Steps

### 0. Setup Development Environment (10 minutes)

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version

# Navigate to backend
cd backend

# Create/activate virtual environment with uv
uv venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
uv pip install -r requirements.txt

# Install development dependencies
uv pip install pytest pytest-asyncio pytest-cov alembic
```

### 1. Database Migration (30 minutes)

```bash
# Create migration
cd backend

# Ensure uv is installed
uv --version

# Activate virtual environment (if using uv venv)
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Create migration
alembic revision -m "add_auto_posting_support"

# Edit migration file (see data-model.md for complete SQL)
# Key changes:
# - Add 6 columns to users table
# - Add 3 new invoice statuses
# - Create daily_posting_counters table
# - Create posting_logs table
# - Add indexes

# Run migration
alembic upgrade head

# Verify
psql $DATABASE_URL -c "\d users"
psql $DATABASE_URL -c "\d daily_posting_counters"
```

### 2. Extend Models (20 minutes)

**Install SQLModel if needed**:
```bash
uv pip install sqlmodel
```

**backend/src/models/user.py**:
```python
# Add to UserBase class
auto_posting_enabled: bool = Field(default=False)
auto_posting_start_time: time = Field(default=time(9, 0))
auto_posting_end_time: time = Field(default=time(18, 0))
auto_posting_environment: str = Field(default="SANDBOX")
auto_posting_daily_limit: int = Field(default=100)
auto_posting_paused_until: Optional[datetime] = Field(default=None)
```

**backend/src/models/invoice.py**:
```python
# Add to InvoiceStatus enum
FBR_POSTING = "FBR_POSTING"
FBR_POSTED = "FBR_POSTED"
FBR_FAILED = "FBR_FAILED"

# Add to InvoiceBase class
fbr_posted_at: Optional[datetime] = Field(default=None)
fbr_posting_error: Optional[str] = Field(default=None)
fbr_retry_count: int = Field(default=0)
```

**Create new models**:
- `backend/src/models/daily_posting_counter.py`
- `backend/src/models/posting_log.py`

### 3. Create Service Layer (1 hour)

**Install required dependencies**:
```bash
uv pip install httpx python-dateutil
```

**backend/src/services/auto_posting_service.py**:
```python
class AutoPostingService:
    def is_within_time_window(self, user, current_time) -> bool:
        """Check if current time is within user's window."""
        # Handle midnight-spanning windows
        
    def get_daily_limit_remaining(self, user, current_date) -> int:
        """Get remaining posting capacity for today."""
        # Handle midnight-spanning window continuity
        
    async def post_invoice_to_fbr(self, invoice, user):
        """Post single invoice to FBR sequentially."""
        # Use existing FBRClient
        # Handle network failures (mark as failed, no retry)
        # Update invoice status
        # Create posting log
```

### 4. Add API Endpoints (1 hour)

**backend/src/api/v1/user_profile.py**:
```python
@router.get("/profile/auto-posting")
async def get_auto_posting_config(...):
    """Get user's auto-posting configuration."""

@router.put("/profile/auto-posting")
async def update_auto_posting_config(...):
    """Update auto-posting configuration."""
    # Validate time window
    # Validate daily limit (1-1000)
    # Validate environment
    # Require re-auth for Sandbox → Production

@router.post("/profile/auto-posting/emergency-pause")
async def emergency_pause(...):
    """Disable auto-posting immediately."""
```

**backend/src/api/v1/invoices.py**:
```python
@router.post("/invoices/{invoice_id}/post-to-fbr")
async def manual_post_to_fbr(...):
    """Manually post invoice regardless of auto-posting settings."""
    # Check invoice status (must be TRANSFERRED)
    # Check daily limit (warn but allow override)
    # Post to FBR
    # Count toward daily limit

@router.get("/invoices/posting-status")
async def get_posting_status(...):
    """Get current auto-posting status and statistics."""
```

### 5. Extend AI Agent (1.5 hours)

**Install agent dependencies**:
```bash
cd ../ai-agent
uv pip install apscheduler httpx python-dotenv
```

**ai-agent/skills/fbr_poster.py** (new file):
```python
class FBRPosterSkill:
    async def post_invoices_for_user(self, user, invoices):
        """Post invoices sequentially for a user."""
        for invoice in invoices:
            await self.post_single_invoice(invoice, user)
```

**ai-agent/agent.py**:
```python
def start(self):
    # Add new job
    self.scheduler.add_job(
        func=self._post_to_fbr_job,
        trigger=IntervalTrigger(seconds=300),  # 5 minutes
        id='post_to_fbr',
        name='Auto Post to FBR',
        replace_existing=True,
        max_instances=1
    )

def _post_to_fbr_job(self):
    """5-minute FBR posting job."""
    # Get users with auto_posting_enabled=true
    # For each user:
    #   - Check time window
    #   - Check daily limit
    #   - Get up to 10 TRANSFERRED invoices
    #   - Post sequentially
    #   - Update counters and logs
```

### 6. Frontend Components (2 hours)

**frontend/src/components/profile/AutoPostingSettings.tsx**:
```typescript
export function AutoPostingSettings() {
  // Form for configuring auto-posting
  // - Enable/disable toggle
  // - Time pickers (start/end)
  // - Environment selector
  // - Daily limit input
  // - Save button
}
```

**frontend/src/components/invoices/AutoPostingStatus.tsx**:
```typescript
export function AutoPostingStatus() {
  // Display current status
  // - Status indicator (active/paused/outside hours/disabled)
  // - Today's statistics (posted/failed/remaining)
  // - Next check time
  // - Emergency pause button
  
  // Poll every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);
}
```

**frontend/src/components/invoices/ManualPostButton.tsx**:
```typescript
export function ManualPostButton({ invoiceId }) {
  // Button to manually post invoice
  // - Show loading state
  // - Handle daily limit warning
  // - Show success/error feedback
}
```

### 7. Testing (2 hours)

**Backend tests**:
```bash
# Install test dependencies with uv
cd backend
uv pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/test_auto_posting_service.py
pytest tests/test_auto_posting_api.py

# Run with coverage
pytest --cov=src tests/
```

**Frontend tests**:
```bash
npm test -- AutoPostingSettings.test.tsx
npm test -- AutoPostingStatus.test.tsx
```

**Integration tests**:
- Enable auto-posting → agent posts → verify status
- Manual posting override
- Time window enforcement (including midnight spans)
- Daily limit enforcement
- Emergency pause

---

## 🔑 Key Implementation Notes

### Time Window Logic

```python
def is_within_time_window(current_time, start_time, end_time):
    if start_time <= end_time:
        # Normal: 09:00 - 18:00
        return start_time <= current_time <= end_time
    else:
        # Midnight-spanning: 22:00 - 02:00
        return current_time >= start_time or current_time <= end_time
```

### Daily Limit with Midnight Spans

```python
def get_counter_date(user, current_datetime):
    """Get the date to use for daily counter."""
    if is_midnight_spanning(user.start_time, user.end_time):
        # Use window start date until window ends
        if current_datetime.time() <= user.end_time:
            # After midnight, still in previous day's window
            return (current_datetime - timedelta(days=1)).date()
    return current_datetime.date()
```

### Network Failure Handling

```python
try:
    response = await fbr_client.post_invoice(...)
except (httpx.TimeoutException, httpx.NetworkError):
    # Mark as failed, require manual verification
    invoice.status = InvoiceStatus.FBR_FAILED
    invoice.fbr_posting_error = (
        "Network failure. Invoice may or may not have been accepted by FBR. "
        "Please verify manually before reposting to avoid duplicates."
    )
    invoice.fbr_retry_count = 999  # Mark as non-retryable
```

### Sequential Posting

```python
async def process_user_invoices(user, invoices):
    """Post invoices one at a time."""
    for invoice in invoices:
        await post_invoice_to_fbr(invoice, user)
        # Wait for response before next invoice
```

---

## 📊 Database Schema Quick Reference

### Users Table (extended)
```sql
auto_posting_enabled BOOLEAN DEFAULT FALSE
auto_posting_start_time TIME DEFAULT '09:00:00'
auto_posting_end_time TIME DEFAULT '18:00:00'
auto_posting_environment VARCHAR(20) DEFAULT 'SANDBOX'
auto_posting_daily_limit INTEGER DEFAULT 100
auto_posting_paused_until TIMESTAMP NULL
```

### Invoices Table (extended)
```sql
status ENUM(..., 'FBR_POSTING', 'FBR_POSTED', 'FBR_FAILED')
fbr_posted_at TIMESTAMP NULL
fbr_posting_error VARCHAR(2000) NULL
fbr_retry_count INTEGER DEFAULT 0
```

### New Tables
- `daily_posting_counters`: Track daily counts per user
- `posting_logs`: Audit log for all posting attempts

---

## 🔗 API Endpoints Quick Reference

### Configuration
- `GET /api/v1/profile/auto-posting` - Get config
- `PUT /api/v1/profile/auto-posting` - Update config
- `POST /api/v1/profile/auto-posting/emergency-pause` - Emergency pause

### Manual Posting
- `POST /api/v1/invoices/{id}/post-to-fbr` - Manual post
- `POST /api/v1/invoices/{id}/post-to-fbr/override-limit` - Post with limit override

### Status
- `GET /api/v1/invoices/posting-status` - Get current status
- `GET /api/v1/invoices/posting-history` - Get posting history

---

## 🐛 Common Issues & Solutions

### Issue: Agent not posting invoices
**Check**:
1. Is `auto_posting_enabled = true`?
2. Is current time within window?
3. Is daily limit reached?
4. Are invoices in TRANSFERRED status?
5. Is agent running? Check logs.

### Issue: Midnight-spanning window not working
**Check**:
1. Verify time comparison logic handles `start_time > end_time`
2. Check daily counter uses correct date (window start date)

### Issue: Network failure creates duplicates
**Check**:
1. Verify network failures are marked as non-retryable (`retry_count = 999`)
2. Verify error message instructs manual verification

### Issue: Daily limit not resetting
**Check**:
1. Verify counter reset logic runs at midnight PKT
2. For midnight-spanning windows, verify counter uses window start date

---

## 📚 Reference Documents

- **[plan.md](./plan.md)** - Complete implementation plan
- **[research.md](./research.md)** - Technical decisions and rationale
- **[data-model.md](./data-model.md)** - Database schema details
- **[spec.md](./spec.md)** - Feature specification
- **[contracts/](./contracts/)** - API contracts (OpenAPI)

---

## ⏱️ Estimated Timeline

| Stage | Duration | Description |
|-------|----------|-------------|
| Database & Models | 1 hour | Migration + model extensions |
| Backend Services | 2 hours | Service layer + API endpoints |
| AI Agent | 1.5 hours | New job + FBR posting skill |
| Frontend | 2 hours | Components + API client |
| Testing | 2 hours | Unit + integration tests |
| **Total** | **8.5 hours** | For experienced developer |

---

## ✅ Definition of Done

- [ ] Database migration runs successfully
- [ ] All models extended with new fields
- [ ] Service layer implements time window and limit logic
- [ ] API endpoints return correct responses
- [ ] AI agent posts invoices during configured windows
- [ ] Frontend displays status and allows configuration
- [ ] Manual posting works regardless of auto-posting state
- [ ] Emergency pause disables posting immediately
- [ ] All tests pass (unit + integration)
- [ ] No duplicate invoices in FBR system
- [ ] Daily limits enforced correctly
- [ ] Midnight-spanning windows work correctly
- [ ] Network failures handled safely

---

**Quickstart Status**: ✅ Complete  
**Ready for Implementation**: Yes  
**Next Step**: Run `/sp.tasks` to generate detailed task breakdown
