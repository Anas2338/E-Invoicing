# Multi-stage build for AI Agent
# Build context: project root (E-Invoicing/)
# Build command: docker build -f ai-agent/Dockerfile -t e-invoicing-ai-agent:v1 .

# Stage 1: Builder - Install dependencies
FROM python:3.11-alpine AS builder

# Install build dependencies and uv
RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /build

# Copy ai-agent dependency files
COPY ai-agent/pyproject.toml ai-agent/uv.lock ./

# Install dependencies to a virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Runtime - Minimal production image
FROM python:3.11-alpine

# Install runtime dependencies only
RUN apk add --no-cache libpq libstdc++ && \
    rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1000 agent && \
    adduser -D -u 1000 -G agent agent

# Set working directory to match expected structure
WORKDIR /app

# Copy uv binary for runtime execution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy virtual environment from builder
COPY --from=builder --chown=agent:agent /build/.venv /app/ai-agent/.venv

# Copy backend src directory (required for imports)
COPY --chown=agent:agent backend/src /app/backend/src

# Copy ai-agent application code
COPY --chown=agent:agent ai-agent/*.py /app/ai-agent/
COPY --chown=agent:agent ai-agent/skills /app/ai-agent/skills

# Create logs directory
RUN mkdir -p /app/ai-agent/logs && chown -R agent:agent /app/ai-agent

# Switch to non-root user
USER agent

# Set working directory to ai-agent
WORKDIR /app/ai-agent

# Environment variables
ENV PATH="/app/ai-agent/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check - verify agent heartbeat file is recent
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from pathlib import Path; import sys; from datetime import datetime, timedelta; heartbeat = Path('/tmp/agent_heartbeat.txt'); sys.exit(0 if heartbeat.exists() and (datetime.now() - datetime.fromtimestamp(heartbeat.stat().st_mtime)) < timedelta(minutes=10) else 1)"

# Run the agent with uv
CMD ["uv", "run", "python", "main.py"]
