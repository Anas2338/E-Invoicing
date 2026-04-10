# Research: Digital FTE Invoice Automation

**Feature**: 001-invoice-automation  
**Date**: 2026-04-04  
**Purpose**: Document technology choices and implementation patterns for automation feature

## Research Summary

This document captures research findings and technology decisions for implementing the Digital FTE Invoice Automation feature. All decisions prioritize integration with existing architecture and minimal external dependencies.

---

## 1. Excel Processing Library Selection

### Decision
**pandas 2.2+ with openpyxl 3.1+**

### Rationale
- **pandas**: Industry-standard for data manipulation, excellent performance with 1,000+ rows, rich API for filtering/validation
- **openpyxl**: Native .xlsx support, can read/write Excel files with formatting, integrates seamlessly with pandas
- **Combined strength**: pandas.read_excel() and DataFrame.to_excel() provide simple API while openpyxl handles file I/O
- **Memory efficiency**: pandas uses chunked reading for large files, openpyxl streams data
- **Validation**: Easy to validate column presence, data types, and uniqueness with pandas operations

### Alternatives Considered
1. **xlrd/xlsxwriter**: Older libraries, xlrd no longer supports .xlsx in latest versions, more manual coding required
2. **pyexcel**: Higher-level abstraction but adds unnecessary complexity, less community support
3. **openpyxl alone**: Would require manual data manipulation, pandas provides better data validation APIs

### Implementation Notes
- Use `pandas.read_excel(file_path, engine='openpyxl')` for reading
- Use `df.to_excel(file_path, engine='openpyxl', index=False)` for writing
- Validate columns with `set(df.columns) == set(expected_columns)`
- Check duplicates with `df['invoice_number'].duplicated().any()`
- Handle errors with try-except around pandas operations
- Memory limit: pandas can handle 1,000 rows easily (estimated 10-20MB memory for typical invoice data)

### Integration Points
- Install via pyproject.toml: `pandas = "^2.2.0"`, `openpyxl = "^3.1.0"`
- Import in excel_service.py: `import pandas as pd`
- No conflicts with existing dependencies

---

## 2. Background Job Scheduler

### Decision
**APScheduler 3.10+ with BackgroundScheduler**

### Rationale
- **In-process**: Runs within Python process, no external message broker required (Celery needs Redis/RabbitMQ)
- **Simple deployment**: Single Python script, easy to run as systemd service
- **Cron-like syntax**: `CronTrigger('0 * * * *')` for hourly execution at minute 0
- **Persistence**: Can persist jobs to database if needed (optional for future enhancement)
- **Monitoring**: Easy to add health check endpoint, log execution times
- **Restart handling**: Systemd auto-restart ensures worker comes back up after crashes

### Alternatives Considered
1. **Celery**: Overkill for single hourly task, requires Redis/RabbitMQ infrastructure, adds deployment complexity
2. **systemd timer + cron**: Requires separate script execution, harder to share database connections, less Python-native
3. **Standalone script with while loop**: Less reliable, no built-in scheduling, manual sleep management

### Implementation Notes
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()
scheduler.add_job(
    process_pending_invoices,
    trigger=CronTrigger(minute='0'),  # Every hour at minute 0
    id='fte_worker_hourly',
    replace_existing=True
)
scheduler.start()
```

- Run as separate process: `python -m src.workers.fte_worker`
- Systemd service file: `/etc/systemd/system/fte-worker.service`
- Health check: Add HTTP endpoint to worker process (optional)
- Logging: Use Python logging to track execution times and errors

### Integration Points
- Install via pyproject.toml: `apscheduler = "^3.10.0"`
- Reuse existing database session from `src.database.session`
- Reuse existing services (FBRClient, ValidationService, AuditService)
- No conflicts with FastAPI (runs in separate process)

---

## 3. File Storage Strategy

### Decision
**In-memory parsing with BytesIO - No file storage**

### Rationale
- **Simplicity**: No filesystem management, no cleanup jobs, no storage quotas
- **Security**: No file path traversal risks, no file permission issues
- **Scalability**: Stateless architecture, easier horizontal scaling, no shared filesystem needed
- **Performance**: Direct memory access, no disk I/O overhead
- **Containerization**: Perfect for Docker/Kubernetes, no volume mounts needed
- **Data centralization**: All data in PostgreSQL, single source of truth
- **Export capability**: Generate Excel from database when needed for download

### Alternatives Considered
1. **Local filesystem storage**: Requires cleanup jobs, volume management, backup strategy, complicates deployment
2. **Cloud storage (S3/Azure Blob)**: Adds external dependency, costs, network latency, unnecessary complexity
3. **Database BLOB**: Poor performance for large files, bloats database

### Implementation Notes
```python
from io import BytesIO
import pandas as pd

async def upload_excel(file: UploadFile, db: Session):
    # Read file into memory
    file_content = await file.read()
    file_bytes = BytesIO(file_content)
    
    # Validate file size (in-memory)
    ExcelValidator.validate_file_size(file_bytes)
    file_bytes.seek(0)  # Reset position
    
    # Validate structure (in-memory)
    is_valid, errors = ExcelValidator.validate_excel_file(file_bytes)
    file_bytes.seek(0)  # Reset position
    
    # Parse Excel (in-memory)
    invoices = excel_service.parse_excel_file(file_bytes)
    
    # Store parsed data in database
    automation_service.store_invoices_from_excel(
        user_id=user_id,
        session_id=session_id,
        invoices=invoices
    )
    
    # No file storage - data is in PostgreSQL
```

### Export Functionality
```python
def generate_excel_from_database(invoices: list) -> BytesIO:
    """Generate Excel from database records for download."""
    # Build DataFrame from invoice records
    rows = []
    for invoice in invoices:
        row = {
            "invoice_number": invoice.invoice_data['invoice_number'],
            "status": invoice.status.value,
            "reason": format_reason(invoice),
            # ... all other fields
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Generate Excel in memory
    output = BytesIO()
    df.to_excel(output, engine='openpyxl', index=False)
    output.seek(0)
    return output
```

### Integration Points
- No uploads directory needed
- No .gitignore entries for file storage
- ExcelUploadSession.file_path is optional (nullable)
- Download endpoint generates Excel from database on-demand
- Memory limit: 10MB per file (enforced by validator)

---

## 4. FBR API Integration Pattern

### Decision
**Reuse existing FBRClient and ValidationService**

### Rationale
- **DRY principle**: Avoid duplicating FBR API logic, validation rules
- **Consistency**: Same validation behavior for manual and automated invoices
- **Proven reliability**: Existing services are tested and working in production
- **Maintenance**: Single place to update FBR API changes
- **Error handling**: Existing error handling patterns already handle FBR failures

### Alternatives Considered
1. **Separate automation-specific client**: Would duplicate code, diverge over time, harder to maintain
2. **Shared base client with subclasses**: Over-engineering for current needs, adds complexity
3. **Direct API calls in automation_service**: Violates separation of concerns, harder to test

### Implementation Notes
```python
# In automation_service.py
from src.services.fbr_client import FBRClient
from src.services.validation_service import ValidationService

class AutomationService:
    def __init__(self):
        self.fbr_client = FBRClient()
        self.validation_service = ValidationService()
    
    def process_invoice(self, invoice: AutomationInvoice, db: Session):
        # Validate using existing service
        validation_result = self.validation_service.validate_invoice(
            invoice.invoice_data
        )
        
        if not validation_result.is_valid:
            invoice.status = "failed"
            invoice.validation_errors = validation_result.errors
            db.commit()
            return
        
        # Submit using existing FBR client
        try:
            response = self.fbr_client.submit_invoice(
                invoice.invoice_data,
                environment=invoice.invoice_data.get("environment", "SANDBOX")
            )
            invoice.status = "submitted"
            invoice.fbr_response = response
        except Exception as e:
            invoice.status = "failed"
            invoice.validation_errors = str(e)
        
        db.commit()
```

### Integration Points
- Import existing services: `from src.services.fbr_client import FBRClient`
- Reuse existing FBR credentials from environment variables
- Reuse existing audit logging via AuditService
- Follow existing error handling patterns

---

## 5. Concurrent Upload Prevention

### Decision
**Database flag in ExcelUploadSession.processing_status**

### Rationale
- **Reliability**: Database transactions ensure atomicity, no race conditions
- **Persistence**: Survives application restarts, worker crashes
- **No external dependencies**: No Redis, no distributed locks
- **Simple cleanup**: Set status to 'failed' on exception, 'completed' on success
- **Query efficiency**: Indexed processing_status column for fast lookups
- **Consistent with existing patterns**: Similar to Invoice.status pattern

### Alternatives Considered
1. **Redis lock**: Requires Redis infrastructure, adds external dependency, overkill for single-server deployment
2. **In-memory state**: Lost on restart, doesn't work across multiple processes
3. **File lock**: Platform-specific, harder to query, no transaction guarantees

### Implementation Notes
```python
# In excel_service.py
def check_concurrent_upload(user_id: UUID, db: Session) -> Optional[ExcelUploadSession]:
    """Check if user has an upload currently processing."""
    existing_session = db.query(ExcelUploadSession).filter(
        ExcelUploadSession.user_id == user_id,
        ExcelUploadSession.processing_status == "processing"
    ).first()
    
    return existing_session

def create_upload_session(user_id: UUID, filename: str, db: Session) -> ExcelUploadSession:
    """Create new upload session with 'processing' status."""
    # Check for concurrent upload
    existing = check_concurrent_upload(user_id, db)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Previous upload still processing. Started at {existing.upload_timestamp}"
        )
    
    session = ExcelUploadSession(
        user_id=user_id,
        original_filename=filename,
        processing_status="processing",
        upload_timestamp=datetime.now()
    )
    db.add(session)
    db.commit()
    return session
```

### Integration Points
- Add unique partial index: `CREATE UNIQUE INDEX idx_one_processing_per_user ON excel_upload_session(user_id) WHERE processing_status = 'processing'`
- Handle cleanup in exception handlers
- Document status transitions in data-model.md

---

## 6. Excel Template Generation

### Decision
**Dynamic generation with pandas + openpyxl**

### Rationale
- **Flexibility**: Easy to add/remove columns, change order
- **Maintainability**: Template defined in code, version controlled
- **Data validation**: Can add Excel data validation rules (dropdowns, date formats)
- **Formatting**: Can add column widths, header styling
- **No static files**: No need to manage template.xlsx file in repository

### Alternatives Considered
1. **Pre-created static file**: Harder to maintain, requires manual updates, not version controlled
2. **Manual openpyxl construction**: More verbose code, harder to read
3. **Template engine (Jinja2)**: Overkill for simple column headers

### Implementation Notes
```python
# In excel_service.py
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill

def generate_excel_template() -> bytes:
    """Generate Excel template with predefined headers."""
    # Define columns
    columns = [
        "invoice_number",
        "customer_name", 
        "items",
        "amount",
        "tax",
        "scheduled_date",
        "scheduled_time",
        "status",
        "reason"
    ]
    
    # Create empty DataFrame with columns
    df = pd.DataFrame(columns=columns)
    
    # Save to BytesIO
    from io import BytesIO
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    
    # Add formatting with openpyxl
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active
    
    # Style header row
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    
    # Set column widths
    ws.column_dimensions['A'].width = 20  # invoice_number
    ws.column_dimensions['B'].width = 30  # customer_name
    ws.column_dimensions['C'].width = 50  # items
    ws.column_dimensions['D'].width = 15  # amount
    ws.column_dimensions['E'].width = 15  # tax
    ws.column_dimensions['F'].width = 15  # scheduled_date
    ws.column_dimensions['G'].width = 15  # scheduled_time
    ws.column_dimensions['H'].width = 15  # status
    ws.column_dimensions['I'].width = 30  # reason
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return output.getvalue()
```

### Integration Points
- Endpoint: `GET /api/v1/automation/template/download`
- Response: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Filename: `invoice_automation_template.xlsx`

---

## Summary of Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Excel Reading | pandas | 2.2+ | Data manipulation, validation |
| Excel I/O | openpyxl | 3.1+ | .xlsx file reading/writing |
| Background Jobs | APScheduler | 3.10+ | Hourly FTE worker scheduling |
| File Storage | Local filesystem | N/A | Excel file storage |
| FBR Integration | Existing FBRClient | N/A | Reuse existing service |
| Validation | Existing ValidationService | N/A | Reuse existing service |
| Concurrency Control | PostgreSQL | N/A | Database flag for upload lock |

## Dependencies to Add

```bash
# Add using uv package manager
cd backend
uv add "pandas>=2.2.0" "openpyxl>=3.1.0" "apscheduler>=3.10.0"
```

This will automatically update `pyproject.toml` and `uv.lock`.

---

## 7. AI Agent Architecture (Added 2026-04-10)

### Decision
**Orchestrator-Skills Pattern with Claude API Integration**

### Rationale
- **Modularity**: Skills are Python classes with clear interfaces, easy to test and maintain
- **Intelligence**: Claude API provides decision-making for error classification, retry strategies, prioritization
- **Reusability**: Skills orchestrate existing services (FBRClient, ValidationService) without modification
- **Auditability**: All AI decisions logged with rationale to automation_log table
- **Scalability**: Stateless orchestrator, state stored in database

### Architecture
```
AI Agent Orchestrator
├── Claude API Decision Engine (error classification, retry strategy, prioritization)
├── Skills Registry (manages skill discovery and execution)
└── Skills (Python modules)
    ├── excel_monitor (detect new uploads)
    ├── invoice_validator (validate invoice data)
    ├── fbr_poster (submit to FBR)
    ├── error_handler (classify errors)
    ├── retry_manager (intelligent retry strategies)
    └── priority_scheduler (prioritize processing)
```

### Alternatives Considered
1. **Monolithic agent**: Rejected - harder to test, maintain, and extend
2. **Microservices per skill**: Rejected - too complex for this scale, adds network overhead
3. **Rule-based only (no AI)**: Rejected - lacks flexibility for edge cases, can't adapt to new error patterns

### Implementation Notes
- Skills inherit from `AgentSkill` base class with `execute()` and `can_handle()` methods
- Orchestrator uses Claude API for high-level decisions (classification, strategy selection)
- Skills execute concrete actions using existing services
- All decisions logged to `automation_log.details` field as JSON

---

## 8. Docker Deployment Strategy (Added 2026-04-10)

### Decision
**Separate Docker container for AI Agent, managed via docker-compose**

### Rationale
- **Isolation**: Agent lifecycle independent of web server, can restart without affecting API
- **Resource management**: Separate CPU/memory limits for agent
- **Monitoring**: Separate health checks and logs
- **Deployment**: Can scale agent independently if needed
- **Simplicity**: docker-compose manages all services (db, backend, ai-agent)

### Configuration
```yaml
ai-agent:
  build: ./ai-agent
  depends_on:
    db: {condition: service_healthy}
    backend: {condition: service_healthy}
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "python", "-c", "check_heartbeat()"]
    interval: 60s
  deploy:
    resources:
      limits: {cpus: '0.5', memory: 512M}
```

### Alternatives Considered
1. **Integrated into FastAPI backend**: Rejected - couples lifecycles, harder to monitor separately
2. **Separate VM/server**: Rejected - overkill for this scale, adds deployment complexity
3. **Kubernetes**: Rejected - too complex for current needs, docker-compose sufficient

---

## 9. Scheduling Strategy (Added 2026-04-10)

### Decision
**APScheduler BackgroundScheduler with dual intervals**

### Rationale
- **5-minute precision**: IntervalTrigger(minutes=5) for invoice processing
- **Hourly health checks**: CronTrigger(minute=0) for system health monitoring
- **Non-blocking**: BackgroundScheduler runs in separate thread, doesn't block main loop
- **Job management**: max_instances=1 prevents overlapping runs
- **Proven**: Already used in existing FTE worker, familiar to team

### "Ralph Loop" Clarification
- **Finding**: "Ralph Loop" is NOT a real tool/library
- **Reality**: Conceptual name in spec for hourly orchestration
- **Implementation**: Use APScheduler CronTrigger for hourly health checks

### Configuration
```python
# 5-minute invoice processing
scheduler.add_job(
    process_invoices,
    trigger=IntervalTrigger(minutes=5),
    max_instances=1,
    misfire_grace_time=60
)

# Hourly health check (replaces "Ralph Loop" concept)
scheduler.add_job(
    health_check,
    trigger=CronTrigger(minute=0),
    max_instances=1
)
```

### Alternatives Considered
1. **Celery**: Rejected - requires Redis/RabbitMQ, too heavyweight
2. **asyncio.sleep() loop**: Rejected - less robust, no job management
3. **Separate cron jobs**: Rejected - agent needs internal scheduling for 5-min precision

---

## 10. Database Connection Management (Added 2026-04-10)

### Decision
**Connection pool with pre-ping and hourly recycling**

### Rationale
- **Long-running process**: Agent runs 24/7, needs connection recycling to prevent stale connections
- **Pre-ping**: Validates connections before use, prevents "server closed connection" errors
- **Pool size**: 10 connections sufficient for agent workload (5-min polling + concurrent operations)
- **Burst capacity**: max_overflow=20 handles spikes during batch processing

### Configuration
```python
engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle every hour
    pool_timeout=30,
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"
    }
)
```

### Alternatives Considered
1. **NullPool**: Rejected - creates new connection per query, inefficient
2. **Larger pool_size**: Rejected - 10 connections sufficient, more wastes resources
3. **No recycling**: Rejected - long-running processes need connection recycling

---

## 11. Claude API Integration (Added 2026-04-10)

### Decision
**Prompt-based decision making with caching and rate limiting**

### Rationale
- **Classification**: Claude excels at error classification (transient vs permanent vs rate limit)
- **Strategy selection**: Claude determines optimal retry strategies based on context
- **Prioritization**: Claude orders invoices by business impact
- **Cost optimization**: Prompt caching saves ~90% on repeated system prompts
- **Rate limiting**: 50 requests/minute prevents API exhaustion

### Use Cases
1. **Error Classification**: Analyze error message, FBR response, retry history → classify as TRANSIENT/PERMANENT/RATE_LIMIT/SYSTEM
2. **Retry Strategy**: Determine backoff delay, max attempts, priority adjustment based on error type and business context
3. **Prioritization**: Order invoices by scheduled time proximity, invoice value, retry count, customer priority

### Cost Optimization
- System prompts cached (ephemeral cache control)
- Rate limiter: AsyncLimiter(max_rate=50, time_period=60)
- Cost tracker monitors token usage
- Batch decisions when possible

### Alternatives Considered
1. **Rule-based classification**: Rejected - lacks flexibility for edge cases, can't adapt to new patterns
2. **ML model**: Rejected - requires training data, more complex to maintain
3. **OpenAI API**: Rejected - Claude better for reasoning and classification tasks

---

## 12. Error Handling & Retry Logic (Added 2026-04-10)

### Decision
**Exponential backoff with jitter + circuit breaker**

### Rationale
- **Exponential backoff**: Prevents overwhelming failed services, adapts to error severity
- **Jitter**: Prevents thundering herd problem (multiple agents retrying simultaneously)
- **Circuit breaker**: Protects against cascading failures, opens after 5 consecutive failures
- **Error-specific strategies**: Different backoff for transient (2^attempt) vs rate limit (3^attempt) errors

### Retry Strategies
```python
# Transient errors: Standard exponential backoff
delay = base_delay * (2 ** attempt) + jitter

# Rate limit errors: Longer backoff
delay = base_delay * (3 ** attempt) + jitter

# Permanent errors: No retry
# System errors: Circuit breaker opens
```

### Circuit Breaker
- Opens after 5 consecutive failures
- Half-open after 60 seconds
- Prevents wasted retries when service is down

### Alternatives Considered
1. **Fixed delay**: Rejected - doesn't adapt to error severity
2. **Linear backoff**: Rejected - too aggressive for rate limits
3. **No circuit breaker**: Rejected - wastes resources on dead services

---

## Summary of AI Agent Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Container | Docker (Alpine) | Latest | Isolated agent runtime |
| Orchestration | docker-compose | 3.8+ | Multi-service management |
| Scheduling | APScheduler | 3.10+ | 5-min + hourly intervals |
| AI Decision Engine | Claude API (Anthropic) | Latest | Error classification, retry strategy, prioritization |
| Database Pool | SQLAlchemy | Latest | Connection management with pre-ping |
| Skills | Python modules | 3.11+ | Modular agent capabilities |
| Retry Logic | Custom | N/A | Exponential backoff + circuit breaker |

## Dependencies to Add for AI Agent

```bash
# AI Agent uses separate requirements.txt (not managed by uv)
# Create ai-agent/requirements.txt with:
anthropic>=0.18.0
apscheduler>=3.10.0
sqlmodel>=0.0.23
httpx>=0.28.0
psycopg2-binary>=2.9.10
python-dotenv>=1.0.0

# Install in AI Agent container via Dockerfile:
# RUN pip install --no-cache-dir -r requirements.txt
```

## Next Steps

1. ✅ Research complete - all technology decisions documented (original + AI Agent)
2. Create data-model.md with database schema changes for AI Agent
3. Create quickstart.md with AI Agent setup instructions
4. Create contracts/ directory if API contracts needed
5. Update agent context with new technologies
6. Generate tasks with /sp.tasks command
