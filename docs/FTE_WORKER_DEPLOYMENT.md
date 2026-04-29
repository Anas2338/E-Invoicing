# FTE Worker Deployment Guide

## Overview

The FTE (Full-Time Equivalent) Worker is a background service that automatically processes scheduled invoices every hour. It validates invoices, submits them to FBR, and updates their status in the database.

## Prerequisites

- Python 3.11+
- PostgreSQL database (configured and running)
- Backend dependencies installed (`uv sync`)
- Valid FBR API credentials configured in `.env`

## Configuration

### Environment Variables

Ensure the following variables are set in your `.env` file:

```bash
# Database
DATABASE_URL=postgresql://....

# FBR API
FBR_SANDBOX_URL=https://sandbox.fbr.gov.pk/api
FBR_PRODUCTION_URL=https://api.fbr.gov.pk
FBR_API_KEY=your_api_key_here

# JWT (for authentication)
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
```

## Running the Worker

### Development Mode

For testing and development, run the worker directly:

```bash
cd backend
uv run python -m src.workers.fte_worker
```

The worker will:
- Start immediately
- Run every hour at minute 0 (e.g., 1:00, 2:00, 3:00)
- Log output to console and `fte_worker.log`

### Production Deployment (Linux/systemd)

#### 1. Create systemd Service File

Create `/etc/systemd/system/fte-worker.service`:

```ini
[Unit]
Description=E-Invoicing FTE Worker
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/e-invoicing/backend
Environment="PATH=/var/www/e-invoicing/backend/.venv/bin"
ExecStart=/var/www/e-invoicing/backend/.venv/bin/python -m src.workers.fte_worker
Restart=always
RestartSec=10
StandardOutput=append:/var/log/fte-worker/output.log
StandardError=append:/var/log/fte-worker/error.log

[Install]
WantedBy=multi-user.target
```

#### 2. Create Log Directory

```bash
sudo mkdir -p /var/log/fte-worker
sudo chown www-data:www-data /var/log/fte-worker
```

#### 3. Enable and Start Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable fte-worker

# Start the service
sudo systemctl start fte-worker

# Check status
sudo systemctl status fte-worker
```

#### 4. Service Management Commands

```bash
# Stop the worker
sudo systemctl stop fte-worker

# Restart the worker
sudo systemctl restart fte-worker

# View logs
sudo journalctl -u fte-worker -f

# View recent logs
sudo journalctl -u fte-worker -n 100
```

### Production Deployment (Windows)

#### Using Task Scheduler

1. Open Task Scheduler
2. Create Basic Task:
   - Name: "E-Invoicing FTE Worker"
   - Trigger: At startup
   - Action: Start a program
   - Program: `C:\path\to\backend\.venv\Scripts\python.exe`
   - Arguments: `-m src.workers.fte_worker`
   - Start in: `C:\path\to\backend`

#### Using NSSM (Non-Sucking Service Manager)

```powershell
# Install NSSM
choco install nssm

# Install service
nssm install FTEWorker "C:\path\to\backend\.venv\Scripts\python.exe" "-m src.workers.fte_worker"
nssm set FTEWorker AppDirectory "C:\path\to\backend"
nssm set FTEWorker DisplayName "E-Invoicing FTE Worker"
nssm set FTEWorker Description "Automated invoice processing worker"
nssm set FTEWorker Start SERVICE_AUTO_START

# Start service
nssm start FTEWorker

# Check status
nssm status FTEWorker
```

## Monitoring

### Health Check Endpoint

The worker's health can be monitored via the API:

```bash
# Check worker health
curl http://localhost:8000/api/v1/automation/health/worker

# Response (healthy):
{
  "status": "healthy",
  "last_activity": "2026-04-09T14:00:00",
  "recent_activity_count_24h": 45,
  "checked_at": "2026-04-09T15:30:00"
}

# Response (inactive):
{
  "status": "inactive",
  "last_activity": "2026-04-09T10:00:00",
  "recent_activity_count_24h": 12,
  "checked_at": "2026-04-09T15:30:00"
}
```

### Log Files

Worker logs are written to:
- Console output (development)
- `fte_worker.log` (development)
- `/var/log/fte-worker/output.log` (production Linux)
- `/var/log/fte-worker/error.log` (production Linux)

Log format:
```
2026-04-09 14:00:00 - src.workers.fte_worker - INFO - FTE Worker: Starting hourly invoice processing job
2026-04-09 14:00:05 - src.services.fte_worker_service - INFO - Processing invoice INV-001
2026-04-09 14:00:10 - src.services.fte_worker_service - INFO - Invoice INV-001 submitted successfully
```

### Monitoring Checklist

- [ ] Worker service is running (`systemctl status fte-worker`)
- [ ] Health endpoint returns "healthy" status
- [ ] Logs show recent activity (within last 2 hours)
- [ ] No error messages in logs
- [ ] Database connection is active
- [ ] FBR API is accessible

## Troubleshooting

### Worker Not Starting

**Symptom**: Service fails to start

**Solutions**:
1. Check database connection:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

2. Verify Python environment:
   ```bash
   /path/to/.venv/bin/python --version
   ```

3. Check permissions:
   ```bash
   ls -la /var/www/e-invoicing/backend
   ```

4. Review error logs:
   ```bash
   sudo journalctl -u fte-worker -n 50
   ```

### Worker Stops Unexpectedly

**Symptom**: Service stops after running for some time

**Solutions**:
1. Check for memory issues:
   ```bash
   free -h
   ```

2. Review error logs for exceptions
3. Ensure database connection pool is configured correctly
4. Check for FBR API rate limiting

### No Invoices Being Processed

**Symptom**: Worker runs but doesn't process invoices

**Solutions**:
1. Verify invoices exist with pending status:
   ```sql
   SELECT COUNT(*) FROM automation_invoice WHERE status = 'pending';
   ```

2. Check scheduled times are in the future:
   ```sql
   SELECT * FROM automation_invoice 
   WHERE status = 'pending' 
   AND scheduled_date >= CURRENT_DATE;
   ```

3. Review worker logs for errors
4. Verify FBR API credentials are valid

### High Failure Rate

**Symptom**: Many invoices marked as "failed"

**Solutions**:
1. Check FBR API status
2. Review validation errors in database:
   ```sql
   SELECT validation_errors, COUNT(*) 
   FROM automation_invoice 
   WHERE status = 'failed' 
   GROUP BY validation_errors;
   ```

3. Verify invoice data format matches FBR requirements
4. Check for network connectivity issues

## Performance Tuning

### Database Optimization

Ensure indexes are created:
```sql
-- Check existing indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'automation_invoice';

-- Should include:
-- idx_pending_scheduled (status, scheduled_date, scheduled_time)
-- idx_unique_invoice_per_user (user_id, invoice_number)
```

### Worker Configuration

Adjust APScheduler settings in `src/workers/fte_worker.py`:

```python
# Increase max instances for parallel processing (use with caution)
scheduler.add_job(
    run_job_sync,
    trigger=CronTrigger(minute=0),
    max_instances=1  # Keep at 1 to prevent concurrent runs
)
```

### Rate Limiting

If hitting FBR API rate limits, adjust processing in `src/services/fte_worker_service.py`:

```python
# Add delay between submissions
import asyncio
await asyncio.sleep(1)  # 1 second delay between invoices
```

## Backup and Recovery

### Database Backups

Ensure regular backups of the database:
```bash
# Backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore
psql $DATABASE_URL < backup_20260409.sql
```

### Worker State Recovery

The worker is stateless and recovers automatically:
- Pending invoices remain in database
- Next scheduled run will process them
- No manual intervention needed

## Security Considerations

1. **Service User**: Run worker as dedicated user (not root)
2. **File Permissions**: Restrict access to `.env` file (600)
3. **Log Rotation**: Configure logrotate to prevent disk space issues
4. **API Keys**: Store FBR credentials securely, never commit to git
5. **Network**: Restrict outbound connections to FBR API only

## Scaling

For high-volume deployments:

1. **Horizontal Scaling**: Run multiple workers with distributed locking
2. **Database Connection Pool**: Increase pool size in settings
3. **Async Processing**: Worker already uses async for FBR calls
4. **Monitoring**: Use Prometheus/Grafana for metrics

## Support

For issues or questions:
- Check logs first: `sudo journalctl -u fte-worker -f`
- Review health endpoint: `/api/v1/automation/health/worker`
- Consult automation logs in database: `automation_log` table
