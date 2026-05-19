# Multi-stage build for FastAPI backend using Alpine
FROM python:3.11-alpine AS builder

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
COPY pyproject.toml ./

# Install dependencies (remove stale lock, numpy<2 works on old CPUs)
RUN rm -f uv.lock && uv sync --no-cache --no-dev --no-install-project

# Cleanup
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
    rm -rf /app/.venv/lib/python3.11/site-packages/pygments/formatters && \
    find /app/.venv -type f -name "*.exe" -delete 2>/dev/null || true && \
    find /app/.venv -type f -name "*.bat" -delete 2>/dev/null || true && \
    find /app/.venv -type d -name "*.dist-info" -exec sh -c 'rm -f "$1"/RECORD "$1"/INSTALLER "$1"/direct_url.json' _ {} \; 2>/dev/null || true && \
    rm -rf /app/.venv/bin/pip* /app/.venv/bin/wheel /app/.venv/bin/easy_install* 2>/dev/null || true

# Production stage
FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache \
    libpq \
    libffi \
    openssl \
    libmagic && \
    rm -rf /var/cache/apk/*

RUN adduser -D -u 1000 appuser

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=2

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./

USER appuser
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]