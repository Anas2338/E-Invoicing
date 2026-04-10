# E-Invoicing System Troubleshooting Guide

## Table of Contents

1. [Backend Issues](#backend-issues)
2. [Frontend Issues](#frontend-issues)
3. [Database Issues](#database-issues)
4. [FTE Worker Issues](#fte-worker-issues)
5. [FBR API Issues](#fbr-api-issues)
6. [Excel Upload Issues](#excel-upload-issues)
7. [Authentication Issues](#authentication-issues)
8. [Performance Issues](#performance-issues)

---

## Backend Issues

### Issue: Backend Server Won't Start

**Symptoms**:
- `uvicorn` command fails
- Port already in use error
- Import errors

**Solutions**:

1. **Check if port is already in use**:
   ```bash
   # Linux/Mac
   lsof -i :8000
   
   # Windows
   netstat -ano | findstr :8000
   ```
   Kill the process or use a different port:
   ```bash
   uvicorn src.main:app --port 8001
   ```

2. **Verify Python version**:
   ```bash
   python --version  # Should be 3.11+
   ```

3. **Check dependencies are installed**:
   ```bash
   cd backend
   uv sync
   # or
   pip install -r requirements.txt
   ```

4. **Verify environment variables**:
   ```bash
   cat .env
   # Ensure DATABASE_URL, JWT_SECRET_KEY, etc. are set
   ```

5. **Check for import errors**:
   ```bash
   python -c "from src.main import app"
   ```

### Issue: 500 Internal Server Error

**Symptoms**:
- API returns 500 status code
- Generic error message

**Solutions**:

1. **Check backend logs**:
   ```bash
   # Look for stack traces in console output
   ```

2. **Enable debug mode** (development only):
   ```python
   # In src/main.py
   app = FastAPI(debug=True)
   ```

3. **Check database connection**:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

4. **Review recent code changes**:
   - Check git diff for syntax errors
   - Verify all imports are correct

---

## Frontend Issues

### Issue: Frontend Won't Start

**Symptoms**:
- `npm run dev` fails
- Module not found errors
- Port conflict

**Solutions**:

1. **Reinstall dependencies**:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Check Node.js version**:
   ```bash
   node --version  # Should be 18+
   ```

3. **Clear Next.js cache**:
   ```bash
   rm -rf .next
   npm run dev
   ```

4. **Check for port conflicts**:
   ```bash
   # Change port in package.json or use:
   PORT=3001 npm run dev
   ```

### Issue: API Calls Failing (CORS/Network Errors)

**Symptoms**:
- Network errors in browser console
- CORS policy errors
- 404 on API endpoints

**Solutions**:

1. **Verify API URL in environment**:
   ```bash
   # frontend/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. **Check backend CORS configuration**:
   ```python
   # In src/main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **Verify backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```

---

## Database Issues

### Issue: Database Connection Failed

**Symptoms**:
- "could not connect to server" error
- "password authentication failed" error
- Connection timeout

**Solutions**:

1. **Check PostgreSQL is running**:
   ```bash
   # Linux
   sudo systemctl status postgresql
   
   # Mac
   brew services list
   
   # Windows
   sc query postgresql
   ```

2. **Verify connection string**:
   ```bash
   # Format: postgresql://user:password@host:port/database
   echo $DATABASE_URL
   ```

3. **Test connection manually**:
   ```bash
   psql $DATABASE_URL -c "SELECT version()"
   ```

4. **Check firewall/network**:
   ```bash
   telnet localhost 5432
   ```

5. **Verify database exists**:
   ```bash
   psql -U postgres -c "\l"
   ```

### Issue: Migration Fails

**Symptoms**:
- `alembic upgrade head` fails
- "relation already exists" error
- "column does not exist" error

**Solutions**:

1. **Check current migration version**:
   ```bash
   alembic current
   ```

2. **View migration history**:
   ```bash
   alembic history
   ```

3. **Rollback and retry**:
   ```bash
   alembic downgrade -1
   alembic upgrade head
   ```

4. **Reset database** (development only):
   ```bash
   # Drop and recreate database
   dropdb einvoicing
   createdb einvoicing
   alembic upgrade head
   ```

5. **Check for conflicting migrations**:
   ```bash
   ls backend/alembic/versions/
   # Ensure no duplicate revision IDs
   ```

---

## FTE Worker Issues

### Issue: Worker Not Starting

**Symptoms**:
- Service fails to start
- Immediate exit after start
- Permission denied errors

**Solutions**:

1. **Check service status**:
   ```bash
   sudo systemctl status fte-worker
   ```

2. **View detailed logs**:
   ```bash
   sudo journalctl -u fte-worker -n 100 --no-pager
   ```

3. **Test worker manually**:
   ```bash
   cd backend
   python -m src.workers.fte_worker
   ```

4. **Check file permissions**:
   ```bash
   ls -la /var/www/e-invoicing/backend
   sudo chown -R www-data:www-data /var/www/e-invoicing
   ```

5. **Verify environment file**:
   ```bash
   cat /var/www/e-invoicing/backend/.env
   # Ensure all required variables are set
   ```

6. **Check Python path**:
   ```bash
   /var/www/e-invoicing/backend/.venv/bin/python --version
   ```

### Issue: Worker Running But Not Processing Invoices

**Symptoms**:
- Worker logs show it's running
- No invoices being processed
- Health check shows "inactive"

**Solutions**:

1. **Check for pending invoices**:
   ```sql
   SELECT COUNT(*) FROM automation_invoice 
   WHERE status = 'pending' 
   AND scheduled_date >= CURRENT_DATE;
   ```

2. **Verify scheduled times are in future**:
   ```sql
   SELECT invoice_number, scheduled_date, scheduled_time, status
   FROM automation_invoice
   WHERE status = 'pending'
   ORDER BY scheduled_date, scheduled_time
   LIMIT 10;
   ```

3. **Check worker logs for errors**:
   ```bash
   tail -f /var/log/fte-worker/output.log
   tail -f /var/log/fte-worker/error.log
   ```

4. **Verify database connection**:
   ```bash
   # From worker environment
   psql $DATABASE_URL -c "SELECT 1"
   ```

5. **Check FBR API connectivity**:
   ```bash
   curl -I https://sandbox.fbr.gov.pk/api
   ```

6. **Review automation logs**:
   ```sql
   SELECT * FROM automation_log
   ORDER BY timestamp DESC
   LIMIT 20;
   ```

### Issue: Worker Crashes or Stops Unexpectedly

**Symptoms**:
- Service stops after running
- Out of memory errors
- Database connection errors

**Solutions**:

1. **Check system resources**:
   ```bash
   free -h  # Memory
   df -h    # Disk space
   top      # CPU usage
   ```

2. **Review error logs**:
   ```bash
   sudo journalctl -u fte-worker -p err -n 50
   ```

3. **Increase memory limit** (if needed):
   ```bash
   # Edit /etc/systemd/system/fte-worker.service
   MemoryLimit=2G
   sudo systemctl daemon-reload
   sudo systemctl restart fte-worker
   ```

4. **Check database connection pool**:
   ```python
   # In src/config/settings.py
   DATABASE_POOL_SIZE = 10
   DATABASE_MAX_OVERFLOW = 20
   ```

---

## FBR API Issues

### Issue: FBR API Returns Errors

**Symptoms**:
- 401 Unauthorized
- 403 Forbidden
- 500 Internal Server Error from FBR

**Solutions**:

1. **Verify API credentials**:
   ```bash
   echo $FBR_API_KEY
   # Ensure key is valid and not expired
   ```

2. **Check environment URL**:
   ```bash
   # Sandbox
   echo $FBR_SANDBOX_URL
   
   # Production
   echo $FBR_PRODUCTION_URL
   ```

3. **Test API connectivity**:
   ```bash
   curl -H "Authorization: Bearer $FBR_API_KEY" \
        https://sandbox.fbr.gov.pk/api/health
   ```

4. **Review FBR API status**:
   - Check FBR's official status page
   - Contact FBR support if persistent issues

5. **Check rate limiting**:
   ```sql
   SELECT COUNT(*) FROM automation_log
   WHERE action = 'SUBMIT'
   AND timestamp > NOW() - INTERVAL '1 hour';
   ```

### Issue: Invoice Validation Fails

**Symptoms**:
- Invoices marked as "failed"
- Validation error messages
- Schema mismatch errors

**Solutions**:

1. **Review validation errors**:
   ```sql
   SELECT invoice_number, validation_errors
   FROM automation_invoice
   WHERE status = 'failed'
   ORDER BY created_at DESC
   LIMIT 10;
   ```

2. **Check invoice data format**:
   ```sql
   SELECT invoice_data FROM automation_invoice
   WHERE id = '<invoice_id>';
   ```

3. **Verify required fields**:
   - All mandatory FBR fields present
   - Correct data types
   - Valid enum values

4. **Test with FBR validator**:
   - Use FBR's online validation tool
   - Compare with working invoice

---

## Excel Upload Issues

### Issue: Upload Fails with Validation Error

**Symptoms**:
- 400 Bad Request
- "Invalid Excel file" error
- "Missing columns" error

**Solutions**:

1. **Verify file format**:
   - Must be `.xlsx` (not `.xls` or `.csv`)
   - File size < 10 MB
   - Not corrupted

2. **Check column names**:
   ```bash
   # Column names are case-sensitive and must match exactly
   # See docs/EXCEL_TEMPLATE_SPECS.md for full list
   ```

3. **Download fresh template**:
   ```bash
   curl -O http://localhost:8000/api/v1/automation/template/download
   ```

4. **Validate data formats**:
   - Dates: YYYY-MM-DD
   - Times: HH:MM (24-hour)
   - Numbers: No currency symbols or commas

5. **Check for duplicate invoice numbers**:
   - Within the file
   - Against existing database records

### Issue: Concurrent Upload Blocked

**Symptoms**:
- 409 Conflict error
- "Previous upload still processing" message

**Solutions**:

1. **Check upload status**:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
        http://localhost:8000/api/v1/automation/excel/status/{session_id}
   ```

2. **Wait for previous upload to complete**:
   - Check dashboard for processing status
   - Typically completes within 1-2 minutes

3. **If stuck, check database**:
   ```sql
   SELECT * FROM excel_upload_session
   WHERE user_id = '<user_id>'
   AND processing_status = 'processing'
   ORDER BY created_at DESC;
   ```

4. **Manually mark as completed** (if truly stuck):
   ```sql
   UPDATE excel_upload_session
   SET processing_status = 'completed'
   WHERE id = '<session_id>';
   ```

### Issue: Rate Limit Exceeded

**Symptoms**:
- 429 Too Many Requests
- "Rate limit exceeded" message

**Solutions**:

1. **Wait before retrying**:
   - Upload endpoint: 5 requests per hour per IP
   - Wait 60 minutes or use different IP

2. **Check rate limit headers**:
   ```bash
   curl -I -H "Authorization: Bearer $TOKEN" \
        http://localhost:8000/api/v1/automation/excel/upload
   ```

3. **Contact admin to adjust limits** (if needed):
   ```python
   # In src/api/v1/automation/excel.py
   @limiter.limit("10/hour")  # Increase limit
   ```

---

## Authentication Issues

### Issue: Login Fails

**Symptoms**:
- 401 Unauthorized
- "Invalid credentials" error
- Token expired

**Solutions**:

1. **Verify credentials**:
   - Check username/email
   - Verify password

2. **Check user exists in database**:
   ```sql
   SELECT id, email, is_active FROM users
   WHERE email = 'user@example.com';
   ```

3. **Verify JWT configuration**:
   ```bash
   echo $JWT_SECRET_KEY
   echo $JWT_ALGORITHM
   ```

4. **Check token expiration**:
   ```python
   # In src/config/settings.py
   JWT_EXPIRATION_MINUTES = 60  # Adjust if needed
   ```

### Issue: Token Expired

**Symptoms**:
- 401 Unauthorized on API calls
- "Token expired" message

**Solutions**:

1. **Login again to get new token**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"user@example.com","password":"password"}'
   ```

2. **Implement token refresh** (if available):
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/refresh \
        -H "Authorization: Bearer $OLD_TOKEN"
   ```

---

## Performance Issues

### Issue: Slow API Responses

**Symptoms**:
- Requests take > 5 seconds
- Timeout errors
- High CPU/memory usage

**Solutions**:

1. **Check database query performance**:
   ```sql
   -- Enable query logging
   ALTER DATABASE einvoicing SET log_statement = 'all';
   
   -- Check slow queries
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;
   ```

2. **Verify indexes exist**:
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename IN ('automation_invoice', 'excel_upload_session')
   ORDER BY tablename, indexname;
   ```

3. **Check connection pool**:
   ```python
   # In src/database/session.py
   engine = create_engine(
       DATABASE_URL,
       pool_size=20,
       max_overflow=40
   )
   ```

4. **Monitor system resources**:
   ```bash
   htop  # CPU and memory
   iotop # Disk I/O
   ```

5. **Enable caching** (if applicable):
   - Redis for session storage
   - CDN for static assets

### Issue: Dashboard Slow with Many Invoices

**Symptoms**:
- Dashboard takes > 10 seconds to load
- Pagination slow
- Filters timeout

**Solutions**:

1. **Verify pagination is used**:
   ```bash
   # Always use page_size parameter
   curl "http://localhost:8000/api/v1/automation/dashboard/invoices?page=1&page_size=20"
   ```

2. **Check query optimization**:
   - Composite indexes on filtered columns
   - Avoid SELECT * queries
   - Use COUNT optimization

3. **Archive old data**:
   ```sql
   -- Move old invoices to archive table
   CREATE TABLE automation_invoice_archive AS
   SELECT * FROM automation_invoice
   WHERE created_at < NOW() - INTERVAL '1 year';
   
   DELETE FROM automation_invoice
   WHERE created_at < NOW() - INTERVAL '1 year';
   ```

---

## Getting Help

If issues persist after trying these solutions:

1. **Collect diagnostic information**:
   ```bash
   # System info
   uname -a
   python --version
   node --version
   psql --version
   
   # Service status
   systemctl status fte-worker
   
   # Recent logs
   journalctl -u fte-worker -n 100 > worker-logs.txt
   
   # Database stats
   psql $DATABASE_URL -c "\dt+"
   ```

2. **Check health endpoints**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/api/v1/automation/health/worker
   curl http://localhost:8000/api/v1/automation/health/status
   ```

3. **Review documentation**:
   - README.md
   - docs/FTE_WORKER_DEPLOYMENT.md
   - docs/EXCEL_TEMPLATE_SPECS.md

4. **Contact support** with:
   - Error messages (full stack trace)
   - Steps to reproduce
   - System information
   - Relevant log files
