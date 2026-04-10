# Quickstart Guide: Digital FTE Invoice Automation

**Feature**: 001-invoice-automation  
**Date**: 2026-04-04  
**Purpose**: Setup and testing instructions for automation feature

## Prerequisites

- Python 3.11+ installed
- PostgreSQL database (Neon) configured
- Existing FBR Invoice Portal backend running
- Better Auth configured for authentication

---

## Installation

### 1. Install Dependencies

Add new dependencies to backend using uv:

```bash
cd backend
uv add pandas openpyxl apscheduler
```

Or using pip (if uv not available):

```bash
pip install pandas openpyxl apscheduler
```

### 2. Run Database Migration

```bash
cd backend

# Generate migration (if not already created)
uv run alembic revision --autogenerate -m "Add automation tables"

# Apply migration
uv run alembic upgrade head
```

### 3. Verify Models Import

Ensure new models are imported in `src/database/session.py`:

```python
# Add to imports
from src.models.automation_invoice import AutomationInvoice
from src.models.automation_log import AutomationLog
from src.models.excel_upload_session import ExcelUploadSession
```

---

## Running the Application

### Backend API Server

```bash
cd backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### FTE Worker (Development)

In a separate terminal:

```bash
cd backend
uv run python -m src.workers.fte_worker
```

The worker will:
- Start APScheduler with hourly cron job
- Check for pending invoices every hour at minute 0
- Process invoices scheduled for the current hour
- Log all activities

---

## Testing the Automation Flow

### 1. Download Excel Template

```bash
curl -X GET http://localhost:8000/api/v1/automation/template/download \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o template.xlsx
```

Or use the frontend UI at `/automation/upload`

### 2. Fill Excel Template

Open `template.xlsx` and add test data:

| invoice_number | customer_name | items | amount | tax | scheduled_date | scheduled_time | status | reason |
|----------------|---------------|-------|--------|-----|----------------|----------------|--------|--------|
| INV-001 | Test Customer | Product A | 10000 | 1800 | 2026-04-04 | 10:00 | | |
| INV-002 | Another Customer | Product B | 5000 | 900 | 2026-04-04 | 10:00 | | |

**Important**: Set `scheduled_time` to the current hour for immediate testing (e.g., if it's 10:30, set time to 10:00)

### 3. Upload Excel File

```bash
curl -X POST http://localhost:8000/api/v1/automation/excel/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@template.xlsx"
```

Expected response:

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_rows": 2,
  "message": "Excel file uploaded successfully. 2 invoices scheduled for processing."
}
```

### 4. Check Upload Status

```bash
curl -X GET http://localhost:8000/api/v1/automation/excel/status/SESSION_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Wait for Hourly Processing

The FTE worker runs every hour at minute 0. For testing:

**Option A: Wait for next hour**
- Worker will automatically process invoices at the top of the hour

**Option B: Trigger manually (development only)**
- Modify `fte_worker.py` to run immediately for testing
- Or set scheduled_time to next hour and wait

### 6. Check Dashboard Statistics

```bash
curl -X GET http://localhost:8000/api/v1/automation/dashboard/stats \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Expected response:

```json
{
  "total_invoices": 2,
  "pending_count": 0,
  "expired_count": 0,
  "validated_count": 0,
  "submitted_count": 2,
  "failed_count": 0
}
```

### 7. View Invoice List

```bash
curl -X GET "http://localhost:8000/api/v1/automation/dashboard/invoices?page=1&page_size=50" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 8. Download Excel with Results

```bash
curl -X GET http://localhost:8000/api/v1/automation/dashboard/download/SESSION_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o invoices_results.xlsx
```

Open `invoices_results.xlsx` to see status and reason columns filled in. This Excel file is generated from the database records, not from stored files.

---

## FTE Worker Deployment

### Development

Run as separate Python process:

```bash
uv run python -m src.workers.fte_worker
```

### Production (systemd service)

Create `/etc/systemd/system/fte-worker.service`:

```ini
[Unit]
Description=FBR Invoice Automation FTE Worker
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/fbr-invoice-portal/backend
Environment="PATH=/var/www/fbr-invoice-portal/backend/.venv/bin"
ExecStart=/var/www/fbr-invoice-portal/backend/.venv/bin/uv run python -m src.workers.fte_worker
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fte-worker
sudo systemctl start fte-worker
sudo systemctl status fte-worker
```

View logs:

```bash
sudo journalctl -u fte-worker -f
```

---

## Environment Variables

No new environment variables required. The automation feature reuses existing configuration:

- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET`: JWT token verification
- `FBR_API_URL`: FBR portal API endpoint
- `FBR_API_KEY`: FBR API credentials

---

## Troubleshooting

### Upload Fails with "Invalid Excel structure"

**Problem**: Missing required columns or incorrect column names

**Solution**: 
- Download fresh template from `/api/v1/automation/template/download`
- Ensure all columns are present: invoice_number, customer_name, items, amount, tax, scheduled_date, scheduled_time, status, reason
- Check column names match exactly (case-sensitive)

### Upload Fails with "Duplicate invoice numbers"

**Problem**: Excel file contains duplicate invoice_number values

**Solution**:
- Check Excel for duplicate invoice numbers
- Each invoice_number must be unique within the file
- Fix duplicates and re-upload

### Upload Fails with "Previous upload still processing"

**Problem**: Another Excel upload is currently being processed

**Solution**:
- Wait for current upload to complete (check status endpoint)
- Or check database for stuck sessions:
  ```sql
  SELECT * FROM excel_upload_session 
  WHERE user_id = 'YOUR_USER_ID' 
  AND processing_status = 'processing';
  ```
- Manually set status to 'failed' if stuck

### Worker Not Processing Invoices

**Problem**: FTE worker is running but invoices remain in 'pending' status

**Solution**:
1. Check worker logs for errors
2. Verify scheduled_time matches current hour:
   ```sql
   SELECT invoice_number, scheduled_date, scheduled_time, status
   FROM automation_invoice
   WHERE status = 'pending'
   AND scheduled_date = CURRENT_DATE;
   ```
3. Ensure worker is running: `ps aux | grep fte_worker`
4. Check worker cron schedule in logs (should show "Next run at: ...")

### FBR Submission Fails

**Problem**: Invoices marked as 'failed' with "FBR portal unreachable"

**Solution**:
1. Check FBR API credentials in environment variables
2. Verify network connectivity to FBR portal
3. Check FBR portal status (may be down)
4. Use manual retry from dashboard: `POST /api/v1/automation/invoice/{id}/retry`

### Excel File Not Updated

**Problem**: Downloaded Excel file doesn't show status updates

**Solution**:
1. Verify invoices have been processed (check processed_at timestamp)
2. Check automation_log table for processing actions
3. The download endpoint generates Excel from database on-demand - no file storage involved
4. Check worker logs for processing errors

### Large File Upload Timeout

**Problem**: Upload fails for Excel files with 500+ rows

**Solution**:
1. Increase request timeout in FastAPI:
   ```python
   app = FastAPI(timeout=300)  # 5 minutes
   ```
2. Process in smaller batches (split Excel into multiple files)
3. Monitor server resources (CPU, memory)

---

## Performance Tuning

### Database Indexes

Ensure indexes are created (should be automatic from migration):

```sql
-- Verify indexes exist
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename IN ('automation_invoice', 'excel_upload_session', 'automation_log');
```

### Worker Concurrency

For high-volume processing, consider:

1. **Batch processing**: Process invoices in chunks of 100
2. **Parallel processing**: Use ThreadPoolExecutor for FBR submissions
3. **Connection pooling**: Increase database connection pool size

### Memory Management

Monitor application memory usage during Excel parsing:

```bash
# Check Python process memory
ps aux | grep python | grep fte_worker
```

The in-memory parsing approach limits file size to 10MB (enforced by validator) to prevent memory issues.

---

## Monitoring

### Health Checks

**Backend API**:
```bash
curl http://localhost:8000/health
```

**FTE Worker** (add health endpoint):
```bash
curl http://localhost:8001/health
```

### Key Metrics to Track

1. **Upload success rate**: % of successful uploads
2. **Processing time**: Time from upload to completion
3. **FBR submission success rate**: % of successful FBR submissions
4. **Worker uptime**: % of time worker is running
5. **Hourly execution**: Verify worker runs every hour

### Logging

Worker logs include:
- Hourly execution start/end
- Number of invoices processed
- FBR submission results
- Errors and exceptions

View logs:
```bash
# Development
tail -f logs/fte_worker.log

# Production (systemd)
sudo journalctl -u fte-worker -f
```

---

## Testing Checklist

- [ ] Download Excel template successfully
- [ ] Upload valid Excel file
- [ ] Upload rejected for duplicate invoice numbers
- [ ] Upload rejected for missing columns
- [ ] Concurrent upload blocked
- [ ] Invoices with past times marked as 'expired'
- [ ] FTE worker processes pending invoices at scheduled hour
- [ ] Valid invoices submitted to FBR successfully
- [ ] Invalid invoices marked as 'failed' with error details
- [ ] Dashboard shows correct statistics
- [ ] Invoice list filters work correctly
- [ ] Invoice detail view shows complete information
- [ ] Manual retry works for failed invoices
- [ ] Download Excel generates file from database successfully
- [ ] User can only see their own invoices (data isolation)

---

---

## AI Agent Setup (Added 2026-04-10)

### Prerequisites

- Docker and docker-compose installed
- Claude API key (Anthropic)
- Existing backend and database running

### 1. Install AI Agent Dependencies

Create `ai-agent/requirements.txt`:

```txt
anthropic>=0.18.0
apscheduler>=3.10.0
sqlmodel>=0.0.23
httpx>=0.28.0
psycopg2-binary>=2.9.10
python-dotenv>=1.0.0
```

### 2. Run Database Migration for AI Agent

```bash
cd backend
uv run alembic upgrade head  # Applies AI Agent schema changes
```

This adds:
- `retry_count`, `last_retry_at`, `priority` fields to `automation_invoice`
- `ai_agent_health_check` table

### 3. Configure Environment Variables

Add to `.env`:

```bash
# Claude API
ANTHROPIC_API_KEY=your_claude_api_key_here

# AI Agent Configuration
AGENT_CHECK_INTERVAL=300  # 5 minutes in seconds
AGENT_VERSION=1.0.0
LOG_LEVEL=INFO
```

### 4. Build and Run with Docker Compose

Update `docker-compose.yml` to include AI Agent service:

```yaml
services:
  # ... existing db and backend services ...
  
  ai-agent:
    build:
      context: ./ai-agent
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - FBR_SANDBOX_BASE_URL=${FBR_SANDBOX_BASE_URL}
      - FBR_PRODUCTION_BASE_URL=${FBR_PRODUCTION_BASE_URL}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - AGENT_CHECK_INTERVAL=300
    depends_on:
      db:
        condition: service_healthy
      backend:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "from pathlib import Path; import sys; from datetime import datetime, timedelta; heartbeat = Path('/tmp/agent_heartbeat.txt'); sys.exit(0 if heartbeat.exists() and (datetime.now() - datetime.fromtimestamp(heartbeat.stat().st_mtime)) < timedelta(minutes=10) else 1)"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - einvoicing-network
    volumes:
      - agent_logs:/app/logs
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

volumes:
  agent_logs:
```

Start all services:

```bash
docker-compose up -d
```

### 5. Verify AI Agent is Running

Check container status:

```bash
docker-compose ps
```

Expected output:
```
NAME                STATUS              PORTS
db                  Up (healthy)        5432/tcp
backend             Up (healthy)        7860/tcp
ai-agent            Up (healthy)        
```

Check AI Agent logs:

```bash
docker-compose logs -f ai-agent
```

Expected log output:
```
AI Agent: Initializing...
AI Agent: Scheduler configured
  - 5-minute invoice processing: every 5 minutes
  - Hourly health check: every hour at minute 0
AI Agent: Starting scheduler...
AI Agent: Running hourly health check
  Pending invoices: 0
  Failed invoices: 0
  FBR API status: healthy
  Database status: healthy
```

### 6. Deprecate Old FTE Worker

The AI Agent replaces the old FTE worker. To disable the old worker:

**If running as systemd service:**
```bash
sudo systemctl stop fte-worker
sudo systemctl disable fte-worker
```

**If running manually:**
- Stop the `python -m src.workers.fte_worker` process
- Remove from startup scripts

---

## Testing AI Agent

### 1. Upload Excel File

Same as before - upload Excel with scheduled invoices:

```bash
curl -X POST http://localhost:8000/api/v1/automation/excel/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@template.xlsx"
```

### 2. Monitor AI Agent Detection

The AI Agent should detect the new upload within 1 minute. Check logs:

```bash
docker-compose logs -f ai-agent | grep "New upload detected"
```

### 3. Watch 5-Minute Processing

Unlike the old hourly worker, the AI Agent checks every 5 minutes. Set scheduled times accordingly:

- If current time is 10:32, set scheduled_time to 10:35
- Agent will process within 5 minutes (by 10:40)

### 4. Check AI Agent Health

View latest health check:

```bash
curl -X GET http://localhost:8000/api/v1/automation/agent/health \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Expected response:
```json
{
  "check_timestamp": "2026-04-10T10:00:00Z",
  "overall_status": "healthy",
  "pending_invoice_count": 5,
  "failed_invoice_count": 0,
  "processing_backlog": 0,
  "fbr_api_status": "healthy",
  "database_status": "healthy",
  "anomalies_detected": [],
  "agent_uptime_seconds": 3600
}
```

### 5. View AI Decisions

Check automation logs for AI decisions:

```bash
curl -X GET http://localhost:8000/api/v1/automation/invoice/INVOICE_ID/logs \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Look for `ai_decision` in the `details` field:
```json
{
  "action": "retry",
  "status": "success",
  "details": {
    "ai_decision": {
      "classification": "TRANSIENT",
      "confidence": 0.95,
      "retry_delay_seconds": 60,
      "rationale": "Network timeout indicates temporary issue..."
    }
  }
}
```

---

## AI Agent Troubleshooting

### Agent Container Not Starting

**Problem**: `docker-compose ps` shows ai-agent as unhealthy or exited

**Solution**:
1. Check logs: `docker-compose logs ai-agent`
2. Verify environment variables (especially `ANTHROPIC_API_KEY`)
3. Check database connectivity: `docker-compose exec ai-agent python -c "from agent.database import test_db_connection; print(test_db_connection())"`
4. Verify Claude API key: `docker-compose exec ai-agent python -c "from anthropic import Anthropic; client = Anthropic(); print('API key valid')"`

### Agent Not Processing Invoices

**Problem**: Invoices remain in PENDING status despite scheduled time passing

**Solution**:
1. Check agent is running: `docker-compose ps ai-agent`
2. Verify 5-minute scheduler is active: `docker-compose logs ai-agent | grep "5-minute"`
3. Check invoice scheduled times: 
   ```sql
   SELECT invoice_number, scheduled_date, scheduled_time, status, priority
   FROM automation_invoice
   WHERE status = 'pending'
   ORDER BY priority, scheduled_date, scheduled_time;
   ```
4. Verify agent can access database: Check for connection errors in logs

### Claude API Rate Limiting

**Problem**: Logs show "Rate limit exceeded" errors

**Solution**:
1. Check rate limiter configuration (default: 50 req/min)
2. Reduce decision frequency (batch decisions when possible)
3. Increase rate limit if using paid Claude API tier
4. Monitor cost tracker: `docker-compose logs ai-agent | grep "Cost tracker"`

### Health Check Failing

**Problem**: Docker health check shows unhealthy status

**Solution**:
1. Check heartbeat file: `docker-compose exec ai-agent ls -la /tmp/agent_heartbeat.txt`
2. Verify agent is updating heartbeat (should update every 5 minutes)
3. Check for agent crashes: `docker-compose logs ai-agent | grep "error"`
4. Restart agent: `docker-compose restart ai-agent`

### High Memory Usage

**Problem**: Agent container using >512MB memory

**Solution**:
1. Check for memory leaks: `docker stats ai-agent`
2. Reduce connection pool size in `agent/database.py`
3. Increase memory limit in docker-compose.yml
4. Monitor Claude API response sizes (large responses consume memory)

---

## Monitoring AI Agent

### Key Metrics

1. **Detection Latency**: Time from upload to detection (target: <1 minute)
2. **Processing Precision**: Time from scheduled time to processing (target: <5 minutes)
3. **Error Classification Accuracy**: % of correctly classified errors (target: >95%)
4. **Retry Success Rate**: % of retries that succeed (target: >70%)
5. **Health Check Duration**: Time to complete health check (target: <30 seconds)

### Logs to Monitor

```bash
# All agent activity
docker-compose logs -f ai-agent

# Only errors
docker-compose logs ai-agent | grep ERROR

# AI decisions
docker-compose logs ai-agent | grep "AI Decision"

# Health checks
docker-compose logs ai-agent | grep "Health check"
```

### Alerting

Set up alerts for:
- Agent container down (health check failing)
- High failure rate (>20% in 1 hour)
- Processing backlog (>500 pending invoices)
- FBR API down (3 consecutive failures)
- Database connectivity issues

---

## Performance Comparison

### Old FTE Worker vs AI Agent

| Metric | FTE Worker (Hourly) | AI Agent (5-min) |
|--------|---------------------|------------------|
| Detection latency | Up to 60 minutes | <1 minute |
| Processing precision | 60-minute window | 5-minute window |
| Error handling | Manual retry only | Intelligent auto-retry |
| Prioritization | FIFO only | Business rule-based |
| Monitoring | Basic logs | Health checks + anomaly detection |
| Decision logging | None | Full AI rationale |

---

## Next Steps

1. ✅ AI Agent deployed and running
2. Test end-to-end with real invoices
3. Monitor for 24 hours to verify stability
4. Set up alerting for production
5. Document operational runbooks
6. Train team on AI Agent monitoring
