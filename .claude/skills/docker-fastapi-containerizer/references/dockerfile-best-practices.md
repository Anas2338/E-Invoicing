# Dockerfile Best Practices for Python/FastAPI Applications

## Multi-Stage Builds

Multi-stage builds allow you to separate build-time dependencies from runtime image, significantly reducing image size and improving security:

```dockerfile
#syntax=docker/dockerfile:1

# === Build stage: Install dependencies and create virtual environment ===
FROM python:3.11-slim as builder

ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# === Final stage: Create minimal runtime image ===
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

COPY app.py ./
COPY --from=builder /app/venv /app/venv

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/venv/bin/python", "app.py"]
```

## Security Best Practices

### Non-Root Users
Always run containers as non-root users to reduce attack surface:

```dockerfile
# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Switch to the non-root user
USER appuser

# Or use numeric IDs for better security
ARG USER_ID=10001
RUN useradd --home-dir /app --shell /bin/bash --uid ${USER_ID} appuser
USER appuser
```

### Environment Variables
Set proper environment variables for security and performance:

```dockerfile
# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Set locale
ENV LANG=C.UTF-8
```

## Base Image Selection

### Standard Python Images
- `python:<version>-slim`: Reduced attack surface, includes only essential OS packages
- `python:<version>-alpine`: Even smaller, but potential compatibility issues with some packages

### Docker Hardened Images (DHI)
For production applications, consider Docker Hardened Images:

```dockerfile
# Example with DHI (Docker Hardened Images)
FROM dhi.io/python:3.11-alpine3.17
```

## Layer Caching Optimization

Order Dockerfile instructions to leverage layer caching effectively:

```dockerfile
# Copy requirements first to leverage caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code last (changes most frequently)
COPY . .
```

## Production Optimizations

### Package Installation
```dockerfile
# Install only production dependencies
RUN pip install --no-cache-dir --no-deps -r requirements.txt

# Or use --user to install to user directory
RUN pip install --user --no-cache-dir -r requirements.txt
ENV PATH=/root/.local/bin:$PATH
```

### Cleanup
```dockerfile
# Clean up package manager cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Remove build dependencies after installation
RUN apt-get update && apt-get install -y build-essential && \
    pip install packages && \
    apt-get purge -y build-essential && \
    apt-get autoremove -y && \
    apt-get clean
```

## FastAPI Specific Configurations

### Uvicorn Configuration
```dockerfile
# Use uvicorn for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Or with additional options for production
CMD ["uvicorn", "main:app",
     "--host", "0.0.0.0",
     "--port", "8000",
     "--workers", "4",
     "--log-level", "info",
     "--timeout-keep-alive", "30"]
```

### Health Checks
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

## Complete Production Example

```dockerfile
#syntax=docker/dockerfile:1

# === Build stage: Install dependencies and create virtual environment ===
FROM python:3.11-slim as builder

ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /app/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# === Final stage: Create minimal runtime image ===
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

# Create non-root user
ARG USER_ID=10001
ARG GROUP_ID=10001
RUN groupadd -g $GROUP_ID appgroup && \
    useradd -l -u $USER_ID -g appgroup appuser && \
    mkdir -p /app && \
    chown -R appuser:appgroup /app

COPY --from=builder /app/venv /app/venv
COPY . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```