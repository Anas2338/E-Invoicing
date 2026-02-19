# Docker Troubleshooting Guide for FastAPI Applications

## Permission and Ownership Issues

### Problem: Permission Denied on Volume Mounts

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/app/logs/app.log'
```

**Cause:** Container user ID doesn't match host user ID, or files are owned by root.

**Solution 1: Match User IDs**
```dockerfile
# In Dockerfile, use host user ID
ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd -g $GROUP_ID appgroup && \
    useradd -l -u $USER_ID -g appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser
```

```bash
# Build with your user ID
docker build --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) -t myapp .
```

**Solution 2: Fix Ownership in Entrypoint**
```dockerfile
# Create entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
#!/bin/bash
# entrypoint.sh
chown -R appuser:appgroup /app/logs
exec "$@"
```

**Solution 3: Use Docker Compose User Directive**
```yaml
services:
  web:
    build: .
    user: "${UID}:${GID}"
    volumes:
      - .:/app
```

```bash
# Run with your user ID
UID=$(id -u) GID=$(id -g) docker-compose up
```

### Problem: Cannot Write to Volume-Mounted Directories

**Symptom:**
```
OSError: [Errno 30] Read-only file system: '/app/data'
```

**Cause:** Volume mounted as read-only or incorrect permissions.

**Solution:**
```yaml
# docker-compose.yml
services:
  web:
    volumes:
      - ./data:/app/data:rw  # Explicitly set read-write
      - ./logs:/app/logs:rw
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m  # Writable temp directory
```

## Module and Import Issues

### Problem: ModuleNotFoundError in Container

**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Cause:** Dependencies not installed, wrong Python path, or virtual environment not activated.

**Solution 1: Verify Requirements Installation**
```dockerfile
# Ensure requirements are installed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify installation
RUN python -c "import fastapi; print(fastapi.__version__)"
```

**Solution 2: Check Virtual Environment Path**
```dockerfile
# Ensure venv is in PATH
ENV PATH="/app/venv/bin:$PATH"

# Or use absolute path in CMD
CMD ["/app/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0"]
```

**Solution 3: Fix PYTHONPATH for Custom Modules**
```dockerfile
# Add app directory to Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Or in docker-compose
services:
  web:
    environment:
      - PYTHONPATH=/app
```

### Problem: Import Works Locally but Fails in Container

**Symptom:**
```
ImportError: attempted relative import with no known parent package
```

**Cause:** Different working directory or package structure not recognized.

**Solution:**
```dockerfile
# Ensure correct working directory
WORKDIR /app

# Copy entire package structure
COPY app/ ./app/
COPY main.py .

# Run from correct location
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

```python
# Use absolute imports in FastAPI
from app.routers import users  # Good
from .routers import users     # Avoid in main.py
```

## Database Connection Issues

### Problem: Cannot Connect to Database from Container

**Symptom:**
```
sqlalchemy.exc.OperationalError: could not connect to server: Connection refused
```

**Cause:** Using localhost instead of service name, or database not ready.

**Solution 1: Use Service Names in Docker Compose**
```yaml
# docker-compose.yml
services:
  web:
    environment:
      # Use service name, not localhost
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mydb"]
      interval: 5s
      timeout: 5s
      retries: 5
```

**Solution 2: Use host.docker.internal for Host Database**
```yaml
# Connect to database running on host machine
services:
  web:
    environment:
      - DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/mydb
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

**Solution 3: Add Connection Retry Logic**
```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import time

def create_db_engine(database_url: str, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            engine = create_engine(database_url)
            # Test connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return engine
        except OperationalError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Database connection failed. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

### Problem: Database Connection Pool Exhausted

**Symptom:**
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Cause:** Too many concurrent connections, connections not being closed.

**Solution:**
```python
# app/database.py
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # Increase pool size
    max_overflow=20,        # Allow overflow connections
    pool_pre_ping=True,     # Verify connections before use
    pool_recycle=3600,      # Recycle connections after 1 hour
)
```

```yaml
# docker-compose.yml - Increase database max connections
services:
  db:
    image: postgres:15
    command: postgres -c max_connections=200
```

## Port Binding and Network Issues

### Problem: Port Already in Use

**Symptom:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use
```

**Cause:** Another process using the port, or previous container not stopped.

**Solution 1: Find and Stop Conflicting Process**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Stop previous containers
docker-compose down
docker ps -a | grep myapp | awk '{print $1}' | xargs docker rm -f
```

**Solution 2: Use Different Host Port**
```yaml
# docker-compose.yml
services:
  web:
    ports:
      - "8001:8000"  # Map to different host port
```

**Solution 3: Use Dynamic Port Assignment**
```yaml
services:
  web:
    ports:
      - "8000"  # Docker assigns random host port
```

### Problem: Cannot Access Container from Host

**Symptom:** `curl http://localhost:8000` times out or connection refused.

**Cause:** Container listening on 127.0.0.1 instead of 0.0.0.0, or firewall blocking.

**Solution:**
```dockerfile
# Ensure binding to all interfaces
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# Verify port mapping
services:
  web:
    ports:
      - "8000:8000"  # host:container
```

```bash
# Test from inside container
docker exec -it myapp_web_1 curl http://localhost:8000/health

# Check if port is exposed
docker port myapp_web_1
```

## Build and Cache Issues

### Problem: Build Fails with Cached Layer

**Symptom:** Build succeeds with `--no-cache` but fails with cache.

**Cause:** Stale cached layer with outdated dependencies or files.

**Solution 1: Rebuild Without Cache**
```bash
# Force rebuild without cache
docker-compose build --no-cache

# Or for specific service
docker-compose build --no-cache web
```

**Solution 2: Use BuildKit Cache Mounts**
```dockerfile
#syntax=docker/dockerfile:1

# Enable BuildKit
FROM python:3.11-slim

# Use cache mount for pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1
docker-compose build
```

**Solution 3: Invalidate Cache at Specific Layer**
```dockerfile
# Add ARG to invalidate cache from this point
ARG CACHEBUST=1

# Everything after this will rebuild
COPY . .
```

```bash
# Rebuild with new cache bust value
docker build --build-arg CACHEBUST=$(date +%s) -t myapp .
```

### Problem: Large Image Size

**Symptom:** Image is several GB when it should be hundreds of MB.

**Cause:** Not using multi-stage builds, including unnecessary files, or not cleaning up.

**Solution:**
```dockerfile
# Use multi-stage build
FROM python:3.11-slim as builder
WORKDIR /app
RUN python -m venv /app/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/venv /app/venv
COPY app/ ./app/
COPY main.py .
ENV PATH="/app/venv/bin:$PATH"
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

```
# .dockerignore
**/.git
**/__pycache__
**/.pytest_cache
**/.venv
**/venv
**/*.pyc
**/node_modules
**/tests
**/docs
**/.env
```

## Hot Reload and Development Issues

### Problem: Hot Reload Not Working

**Symptom:** Code changes don't trigger uvicorn reload in development.

**Cause:** Volume mount issues, wrong reload configuration, or file system events not propagating.

**Solution 1: Verify Volume Mount**
```yaml
# docker-compose.dev.yml
services:
  web:
    volumes:
      - .:/app
      - /app/__pycache__  # Exclude cache
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Solution 2: Use Polling for File Changes**
```yaml
services:
  web:
    command: uvicorn main:app --reload --reload-delay 2 --host 0.0.0.0
    environment:
      - WATCHFILES_FORCE_POLLING=true  # For network mounts
```

**Solution 3: Check File Permissions**
```bash
# Ensure files are readable by container user
chmod -R 755 app/
```

### Problem: Debugger Not Attaching

**Symptom:** Cannot connect debugger to containerized FastAPI app.

**Cause:** Debug port not exposed, or debugger not configured correctly.

**Solution:**
```python
# main.py - Add debugpy support
if os.getenv("DEBUG") == "true":
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("Debugger listening on port 5678")
    # debugpy.wait_for_client()  # Uncomment to wait for debugger
```

```yaml
# docker-compose.dev.yml
services:
  web:
    ports:
      - "8000:8000"
      - "5678:5678"  # Debug port
    environment:
      - DEBUG=true
```

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Remote Attach",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/app"
        }
      ]
    }
  ]
}
```

## Memory and Resource Issues

### Problem: Container Killed (OOM)

**Symptom:**
```
Killed
```

**Cause:** Container exceeded memory limit.

**Solution 1: Increase Memory Limit**
```yaml
# docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

**Solution 2: Optimize Application Memory Usage**
```python
# Use connection pooling
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=5,        # Reduce pool size
    max_overflow=10,
    pool_pre_ping=True
)

# Limit worker processes
# CMD ["uvicorn", "main:app", "--workers", "2"]  # Reduce workers
```

**Solution 3: Monitor Memory Usage**
```bash
# Check container memory usage
docker stats myapp_web_1

# Check memory limit
docker inspect myapp_web_1 | grep -i memory
```

### Problem: Slow Container Startup

**Symptom:** Container takes minutes to start.

**Cause:** Large image, slow dependency installation, or database migrations.

**Solution:**
```dockerfile
# Optimize layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy code last (changes most frequently)
COPY . .

# Use slim base image
FROM python:3.11-slim  # Not python:3.11 (full)
```

```python
# Run migrations asynchronously
import asyncio
from alembic import command
from alembic.config import Config

async def run_migrations():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: command.upgrade(alembic_cfg, "head"))
```

## Environment Variable Issues

### Problem: Environment Variables Not Loading

**Symptom:** `KeyError: 'DATABASE_URL'` or variables have default values.

**Cause:** .env file not loaded, or variables not passed to container.

**Solution 1: Use env_file in Docker Compose**
```yaml
# docker-compose.yml
services:
  web:
    env_file:
      - .env
      - .env.local  # Override with local values
```

**Solution 2: Explicitly Pass Variables**
```yaml
services:
  web:
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
```

**Solution 3: Load .env in Application**
```python
# main.py
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")
```

### Problem: Secrets Exposed in Logs

**Symptom:** Sensitive data visible in `docker logs`.

**Cause:** Printing environment variables or connection strings.

**Solution:**
```python
# Don't log sensitive data
# BAD
print(f"Connecting to {DATABASE_URL}")

# GOOD
print("Connecting to database...")

# Use secrets management
import os

def get_secret(key: str) -> str:
    """Read secret from file or environment."""
    secret_file = os.getenv(f"{key}_FILE")
    if secret_file and os.path.exists(secret_file):
        with open(secret_file) as f:
            return f.read().strip()
    return os.getenv(key, "")
```

## Quick Diagnostic Commands

```bash
# Check container logs
docker-compose logs -f web

# Check container status
docker-compose ps

# Inspect container
docker inspect myapp_web_1

# Execute command in running container
docker-compose exec web bash

# Check network connectivity
docker-compose exec web ping db

# View container resource usage
docker stats

# Check port mappings
docker-compose port web 8000

# Rebuild and restart
docker-compose up --build --force-recreate

# Clean up everything
docker-compose down -v --remove-orphans
docker system prune -a --volumes
```
