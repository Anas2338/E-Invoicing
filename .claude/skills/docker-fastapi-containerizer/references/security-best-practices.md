# Docker Security Best Practices for Python/FastAPI Applications

## Container Security Fundamentals

### 1. Non-Root User Execution
Always run containers as non-root users to reduce the attack surface:

```dockerfile
# Create a specific user for the application
RUN useradd --create-home --shell /bin/bash appuser

# Set the user for the container
USER appuser

# Or use numeric IDs for better security
ARG USER_ID=10001
ARG GROUP_ID=10001
RUN groupadd -g $GROUP_ID appgroup && \
    useradd -l -u $USER_ID -g appgroup appuser && \
    mkdir -p /app && \
    chown -R appuser:appgroup /app

USER appuser
```

### 2. Minimal Base Images
Use minimal base images to reduce the attack surface:

- `python:<version>-slim`: Reduced OS packages compared to full images
- `python:<version>-alpine`: Even smaller footprint, though with potential compatibility issues
- Docker Hardened Images (DHI): Security-focused images with reduced vulnerabilities

```dockerfile
# Good: Use slim variant
FROM python:3.11-slim

# Better: Use Alpine for smaller footprint
FROM python:3.11-alpine

# Best: Use Docker Hardened Images for production
FROM dhi.io/python:3.11-alpine3.17
```

### 3. Secure File Permissions
Control file permissions within the container:

```dockerfile
# Copy files with specific permissions
COPY --chown=appuser:appgroup . /app

# Set restrictive permissions
RUN chmod 755 /app/entrypoint.sh
RUN chmod 600 /app/config/secret_key
```

## Image Security

### 1. Dependency Management
Keep dependencies updated and minimize packages:

```dockerfile
# Install only production dependencies
RUN pip install --no-cache-dir --no-deps -r requirements.txt

# Clean up package manager cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Remove build dependencies after installation
RUN apt-get update && apt-get install -y build-essential && \
    pip install packages && \
    apt-get purge -y build-essential && \
    apt-get autoremove -y && \
    apt-get clean
```

### 2. Multi-Stage Builds
Separate build and runtime environments:

```dockerfile
#syntax=docker/dockerfile:1

# === Build stage: Install dependencies ===
FROM python:3.11-slim as builder

WORKDIR /app
RUN python -m venv /app/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# === Runtime stage: Minimal image ===
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /app/venv /app/venv
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Runtime Security

### 1. Docker Run Security Options
Use security options when running containers:

```bash
# Drop all capabilities and add only what's needed
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE my-app

# Run as specific user
docker run --user 1000:1000 my-app

# Read-only root filesystem
docker run --read-only my-app

# Mount tmpfs for temporary directories
docker run --tmpfs /tmp:rw,noexec,nosuid,size=100m my-app
```

### 2. Docker Compose Security Settings
Configure security in Docker Compose files:

```yaml
version: '3.8'

services:
  web:
    build: .
    user: "1000:1000"  # Run as specific user
    read_only: true    # Read-only root filesystem
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m
    cap_drop:
      - ALL           # Drop all capabilities
    cap_add:
      - NET_BIND_SERVICE  # Add specific capability if needed
    security_opt:
      - no-new-privileges:true
    sysctls:
      - net.ipv4.tcp_fin_timeout=30
    environment:
      - SECURE_SSL=true
    restart: unless-stopped
```

## Vulnerability Management

### 1. Image Scanning
Scan images for vulnerabilities before deployment:

```dockerfile
# Example with Trivy for vulnerability scanning
# In CI/CD pipeline:
# trivy image my-python-app:latest
```

### 2. Secrets Management
Never hardcode secrets in Dockerfiles:

```dockerfile
# ❌ DON'T: Hardcode secrets in Dockerfile
# ENV SECRET_KEY=super-secret-key

# ✅ DO: Use Docker secrets or environment files
CMD ["python", "app.py"]
# Secrets are mounted at runtime
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    secrets:
      - db_password
    environment:
      - DB_PASSWORD_FILE=/run/secrets/db_password
    configs:
      - source: app_config
        target: /app/config/app.yaml

secrets:
  db_password:
    file: ./secrets/db_password.txt

configs:
  app_config:
    file: ./config/app.yaml
```

## Network Security

### 1. Custom Networks
Use custom networks for service isolation:

```yaml
version: '3.8'

services:
  web:
    build: .
    networks:
      - app-network
    ports:
      - "8000:8000"

  db:
    image: postgres:15
    networks:
      - app-network
    environment:
      - POSTGRES_DB=mydb

networks:
  app-network:
    driver: bridge
    internal: true  # Internal network without external access
```

### 2. Port Exposure
Minimize exposed ports:

```dockerfile
# Only expose necessary ports
EXPOSE 8000

# Don't expose internal service ports to host
# Use internal networking instead
```

## Environment Variable Security

### 1. Secure Environment Handling
Use environment files and avoid hardcoding:

```dockerfile
# ❌ DON'T: Hardcode in Dockerfile
# ENV DATABASE_URL=postgresql://user:pass@host:5432/db

# ✅ DO: Use environment files mounted at runtime
CMD ["python", "app.py"]
# Environment variables provided at runtime
```

### 2. Environment File Example
```bash
# .env.production
DATABASE_URL=postgresql://user:pass@db:5432/mydb
SECRET_KEY=production-secret-key
DEBUG=False
ALLOWED_HOSTS=myapp.com,www.myapp.com
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    env_file:
      - .env.production
    environment:
      - ENVIRONMENT=production
```

## Complete Secure Dockerfile Example

```dockerfile
#syntax=docker/dockerfile:1

# === Build stage ===
FROM python:3.11-slim as builder

ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc musl-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /app/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# === Production stage ===
FROM python:3.11-slim

# Create unprivileged user
ARG USER_ID=10001
ARG GROUP_ID=10001
RUN groupadd -g $GROUP_ID --non-unique appgroup && \
    useradd -l -u $USER_ID -g appgroup --non-unique appuser && \
    mkdir -p /app && \
    chown -R appuser:appgroup /app

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appgroup /app/venv /app/venv

# Copy application code
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Security Checklist

Before deploying, verify:

- [ ] Containers run as non-root users
- [ ] Minimal base images used
- [ ] Multi-stage builds implemented
- [ ] Secrets are not hardcoded
- [ ] Dependencies are up to date
- [ ] Unused packages are removed
- [ ] File permissions are restrictive
- [ ] Network access is limited
- [ ] Images have been scanned for vulnerabilities
- [ ] Runtime security options are applied