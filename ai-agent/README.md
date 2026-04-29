# AI Agent - Invoice Automation

Intelligent autonomous agent for validating FBR invoices during bulk upload.

## Overview

The AI Agent handles invoice validation during Excel bulk uploads:
- **Real-time validation** during upload processing
- **AI-powered error classification** (transient vs permanent)
- **Automated data quality checks**
- **Priority-based processing** (time, value, retry count)
- **Hourly health checks** with anomaly detection

**Important**: The AI Agent validates invoices but does NOT post them to FBR. Validated invoices are:
1. Stored in the automation database
2. Automatically transferred to the main database daily at 6 PM PKT
3. Manually posted by users from the main invoice system

This separation ensures better control, audit trails, and allows users to review invoices before FBR submission.

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# Required:
#   - DATABASE_URL
#   - AI_PROVIDER (claude or gemini)
#   - ANTHROPIC_API_KEY (if using Claude)
#   - GEMINI_API_KEY (if using Gemini)
```

### 3. Run the Agent

```bash
# Development
python -m main

# Production (Docker)
docker-compose up -d ai-agent
```

## Project Structure

```
ai-agent/
├── main.py                    # Entry point
├── agent.py                   # Main orchestrator
├── config.py                  # Configuration management
├── validation.py              # Environment validation
├── ai_client.py              # AI provider abstraction
├── claude_client.py          # Claude API client
├── gemini_client.py          # Gemini API client
├── fallback_classifier.py    # Rule-based fallback
├── metrics.py                # Monitoring metrics
├── database.py               # Database connection
├── skills/                   # Agent skills
│   ├── __init__.py          # Base skill class
│   ├── error_handler.py     # AI error classification
│   ├── excel_monitor.py     # Upload detection
│   ├── fbr_poster.py        # FBR submission
│   ├── invoice_validator.py # Invoice validation
│   ├── priority_scheduler.py # Priority scoring
│   └── retry_manager.py     # Retry logic
├── docs/                     # Documentation
│   ├── README.md
│   ├── README_AI_PROVIDERS.md
│   └── TEST_SUMMARY.md
├── tests/                    # Test files
│   └── README.md
├── logs/                     # Log files
├── Dockerfile               # Docker container
└── pyproject.toml          # Dependencies

```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTOMATION_DATABASE_URL` | Yes | - | PostgreSQL connection string for automation database |
| `AI_PROVIDER` | No | `gemini` | AI provider: `claude` or `gemini` |
| `ANTHROPIC_API_KEY` | If using Claude | - | Claude API key |
| `GEMINI_API_KEY` | If using Gemini | - | Gemini API key |
| `APP_ENV` | No | `development` | Environment: `development` or `production` |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `AGENT_CHECK_INTERVAL` | No | `300` | Processing interval (seconds) |

### Workflow

1. **Upload**: User uploads Excel file with invoices via backend API
2. **Validation**: AI Agent validates invoice data during upload
3. **Storage**: Validated invoices stored in automation database with status `VALIDATED`
4. **Transfer**: Daily at 6 PM PKT, validated invoices from last 24 hours are transferred to main database
5. **Manual Posting**: Users manually post transferred invoices to FBR from main system

**For safe testing during portal development:**

Set `DRY_RUN=true` in `.env` to simulate FBR responses without making real API calls:

```bash
# In .env file
DRY_RUN=true
```

**What happens in Dry Run mode:**
- Validation: 98% simulated success rate (2% random failures for testing error handling)
- FBR Posting: 95% simulated success rate (5% random failures with realistic error codes)
- Response delay: 100-500ms to simulate real API latency
- All AI agent logic runs normally (prioritization, retry, error classification)
- Database updates work as in production
- Logs show `[DRY RUN]` prefix for simulated operations

**Use cases:**
- Test AI agent without FBR credentials
- Develop and test portal features safely
- Verify error handling and retry logic
- Demo the system without real submissions

**Switch to production:**
```bash
# In .env file
DRY_RUN=false  # or remove the line entirely
```

### AI Provider Selection

**Claude (Production)**:
- More accurate error classification
- Better reasoning for complex scenarios
- Requires paid API key
- Set `AI_PROVIDER=claude`

**Gemini (Development/Free)**:
- Free tier available (15 RPM)
- Good accuracy (95%+ in tests)
- Faster response times
- Set `AI_PROVIDER=gemini`

**Fallback (Always Available)**:
- Rule-based classification
- 85-90% accuracy
- Zero API cost
- Automatic when AI fails

See `docs/README_AI_PROVIDERS.md` for detailed comparison.

## Features

### Intelligent Processing
- Detects new uploads within 1 minute (95% of time)
- Processes invoices within 5 minutes of scheduled time (90% of time)
- AI classifies errors with 95%+ accuracy
- Adaptive retry with exponential backoff

### Resilience
- Automatic fallback to rule-based logic
- Circuit breaker prevents cascade failures
- Graceful shutdown with signal handling
- Connection pooling with pre-ping

### Observability
- Structured logging with timing
- Comprehensive metrics collection
- Decision audit trail
- Health checks with anomaly detection

### Production Ready
- Docker containerized
- 24/7 continuous operation
- Environment validation on startup
- Heartbeat for health monitoring

## Monitoring

### Health Check Endpoint
```bash
curl http://localhost:8001/api/v1/automation/agent/health
```

### Decision Log
```bash
curl http://localhost:8001/api/v1/automation/agent/decisions
```

### Metrics
Check logs for metrics summary (logged every hour):
```bash
tail -f logs/agent.log | grep "METRICS SUMMARY"
```

### Docker Health
```bash
docker-compose ps
docker-compose logs -f ai-agent
```

## Troubleshooting

### Agent Won't Start
1. Check environment variables: `python -c "from validation import validate_environment; validate_environment()"`
2. Verify database connection: `psql $DATABASE_URL -c "SELECT 1"`
3. Check API keys are valid

### High Fallback Rate
1. Check AI provider API status
2. Verify API key is valid
3. Check rate limits
4. Review logs for API errors

### Invoices Not Processing
1. Check agent is running: `docker-compose ps`
2. Verify scheduled times are in future
3. Check database for pending invoices
4. Review logs for errors

### Performance Issues
1. Check database connection pool size
2. Monitor processing latency metrics
3. Verify FBR API response times
4. Check for circuit breaker activations

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black .
flake8 .
mypy .
```

### Adding New Skills
1. Create skill in `skills/` directory
2. Inherit from `BaseSkill`
3. Implement `execute()` and `validate_input()`
4. Register in agent orchestrator

## Documentation

- **Architecture**: `docs/README.md`
- **AI Providers**: `docs/README_AI_PROVIDERS.md`
- **Test Results**: `docs/TEST_SUMMARY.md`
- **Feature Spec**: `../specs/001-invoice-automation/spec.md`
- **Implementation Plan**: `../specs/001-invoice-automation/plan.md`

## Support

For issues or questions:
1. Check logs: `logs/agent.log`
2. Review documentation in `docs/`
3. Check security audit: `../SECURITY_AUDIT.md`
4. See project status: `../PROJECT_STATUS.md`

## License

Part of the FBR E-Invoicing System.
