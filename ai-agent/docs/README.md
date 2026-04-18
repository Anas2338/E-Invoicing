# AI Agent Documentation

This directory contains documentation for the AI Agent invoice automation system.

## Documents

### Architecture & Design
- **README_AI_PROVIDERS.md** - AI provider configuration (Claude vs Gemini)
- **TEST_SUMMARY.md** - Test results and validation summary

### Additional Documentation
See also:
- `../README.md` - Main AI Agent README
- `../../specs/001-invoice-automation/` - Feature specifications
- `../../SECURITY_AUDIT.md` - Security audit report
- `../../PHASE_8_COMPLETION.md` - Implementation completion report

## Quick Links

### Setup & Configuration
- Environment variables: `../.env`
- Dependencies: `../pyproject.toml`
- Docker: `../Dockerfile`

### Code Documentation
- Main entry point: `../main.py`
- Agent orchestrator: `../agent.py`
- Configuration: `../config.py`
- Skills: `../skills/`

## Architecture Overview

```
AI Agent
├── Main Orchestrator (agent.py)
│   ├── APScheduler (5-min processing, hourly health checks)
│   └── Signal handling (graceful shutdown)
├── Skills (modular components)
│   ├── Excel Monitor
│   ├── Invoice Validator
│   ├── FBR Poster
│   ├── Error Handler (AI-powered)
│   ├── Retry Manager
│   └── Priority Scheduler
├── AI Client (ai_client.py)
│   ├── Claude API (production)
│   ├── Gemini API (development/free)
│   └── Fallback Classifier (rule-based)
└── Support Systems
    ├── Database (connection pooling)
    ├── Metrics (operational monitoring)
    └── Validation (environment checks)
```

## Key Features

1. **Continuous Monitoring**: Detects uploads within 1 minute
2. **5-Minute Precision**: Processes invoices every 5 minutes
3. **Intelligent Error Handling**: AI classifies errors as transient/permanent
4. **Adaptive Retry**: Exponential backoff with circuit breaker
5. **Priority Processing**: Multi-factor scoring (time, value, retry count)
6. **Fallback Logic**: Rule-based classification when AI unavailable
7. **Health Checks**: Hourly monitoring with anomaly detection
8. **Comprehensive Logging**: Structured logs with timing
9. **Metrics Collection**: Processing latency, accuracy, fallback rate
10. **Production Ready**: Docker containerized, 24/7 operation
