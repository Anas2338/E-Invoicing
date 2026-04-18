# Multi-stage build for FastAPI backend using Alpine
FROM python:3.11-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv (no cache, no dev dependencies)
RUN uv sync --no-cache --no-dev --no-install-project

# Aggressive cleanup in builder stage
RUN find /app/.venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type f -name "*.pyc" -delete && \
    find /app/.venv -type f -name "*.pyo" -delete && \
    find /app/.venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type f -name "*.md" -delete 2>/dev/null || true && \
    find /app/.venv -type f -name "*.txt" ! -name "requirements.txt" -delete 2>/dev/null || true && \
    find /app/.venv -type f -name "*.rst" -delete 2>/dev/null || true && \
    find /app/.venv -type f -name "*.pyi" -delete 2>/dev/null || true && \
    find /app/.venv -name "*.so" -exec strip --strip-unneeded {} \; 2>/dev/null || true && \
    find /app/.venv -name "*.a" -delete 2>/dev/null || true && \
    find /app/.venv -type f -name "*.c" -delete 2>/dev/null || true && \
    find /app/.venv -type f -name "*.h" -delete 2>/dev/null || true && \
    find /app/.venv -type d -name "locale" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /app/.venv/lib/python3.11/site-packages/pip* && \
    rm -rf /app/.venv/lib/python3.11/site-packages/setuptools* && \
    rm -rf /app/.venv/lib/python3.11/site-packages/wheel* && \
    rm -rf /app/.venv/lib/python3.11/site-packages/numpy/tests && \
    rm -rf /app/.venv/lib/python3.11/site-packages/pandas/tests && \
    rm -rf /app/.venv/lib/python3.11/site-packages/*/test && \
    rm -rf /app/.venv/lib/python3.11/site-packages/pygments/styles && \
    rm -rf /app/.venv/lib/python3.11/site-packages/pygments/lexers && \
    rm -rf /app/.venv/lib/python3.11/site-packages/pygments/formatters

# Production stage - minimal runtime image
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install only runtime dependencies
RUN apk add --no-cache \
    libpq \
    libffi \
    openssl \
    libmagic && \
    rm -rf /var/cache/apk/*

# Create non-root user first
RUN adduser -D -u 1000 appuser

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=2

# Copy virtual environment from builder with correct ownership
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code and migration files
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

# Run the application directly with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
