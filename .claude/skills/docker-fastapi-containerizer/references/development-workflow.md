# Development Workflow Optimization for FastAPI Docker Applications

## Overview

This guide covers best practices for optimizing the local development experience when working with containerized FastAPI applications, from dependency management to debugging and multi-architecture builds.

## Dependency Caching Strategies

### Problem: Slow Rebuilds Due to Dependency Installation

Every time you rebuild your Docker image, pip reinstalls all dependencies, even if requirements.txt hasn't changed.

### Solution 1: BuildKit Cache Mounts

Use Docker BuildKit's cache mount feature to persist pip's cache across builds:

```dockerfile
#syntax=docker/dockerfile:1

FROM python:3.11-slim

WORKDIR /app

# Enable BuildKit cache mount for pip
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Enable BuildKit:**
```bash
# Linux/macOS
export DOCKER_BUILDKIT=1
docker build -t myapp .

# Windows PowerShell
$env:DOCKER_BUILDKIT=1
docker build -t myapp .

# Or in docker-compose.yml
version: '3.8'
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DOCKER_BUILDKIT=1
```

### Solution 2: Volume Mount Pip Cache in Development

Mount the host's pip cache into the container during development:

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  web:
    build: .
    volumes:
      - .:/app
      - pip-cache:/root/.cache/pip
    command: |
      sh -c "pip install -r requirements.txt &&
             uvicorn main:app --reload --host 0.0.0.0"

volumes:
  pip-cache:
```

### Solution 3: Layer Caching with Separate Requirements

Split requirements into base and dev dependencies:

```dockerfile
#syntax=docker/dockerfile:1

FROM python:3.11-slim as base

WORKDIR /app

# Install base requirements (changes less frequently)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Development stage
FROM base as development

# Install dev requirements (changes more frequently)
COPY requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-dev.txt

COPY . .

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0"]

# Production stage
FROM base as production

COPY . .

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--workers", "4"]
```

```yaml
# docker-compose.yml
services:
  web:
    build:
      context: .
      target: development  # Use development stage
```

## Debugging in Containers

### Setup 1: debugpy for Python Debugging

Install and configure debugpy for remote debugging:

**requirements-dev.txt:**
```
debugpy==1.8.0
```

**app/main.py:**
```python
import os
from fastapi import FastAPI

app = FastAPI()

# Enable debugpy in development
if os.getenv("DEBUG") == "true":
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("⏳ Debugger listening on port 5678...")
    # Uncomment to wait for debugger to attach before starting
    # debugpy.wait_for_client()
    print("✅ Debugger ready!")

@app.get("/")
def read_root():
    return {"message": "Hello World"}
```

**docker-compose.dev.yml:**
```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      target: development
    ports:
      - "8000:8000"
      - "5678:5678"  # Debug port
    volumes:
      - .:/app
      - /app/__pycache__
    environment:
      - DEBUG=true
      - PYTHONUNBUFFERED=1
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Setup 2: VS Code Debug Configuration

**.vscode/launch.json:**
```json
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
      ],
      "justMyCode": false
    },
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

### Setup 3: PyCharm Debug Configuration

1. Go to Run → Edit Configurations
2. Add new "Python Debug Server"
3. Set host to `localhost` and port to `5678`
4. Add path mappings: `/app` → `<project_root>`
5. Start debug server and run container

### Interactive Debugging with pdb

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()
```

```bash
# Attach to running container for interactive debugging
docker-compose exec web python -m pdb app/main.py
```

## Hot Reload Optimization

### Problem: Slow Hot Reload or Excessive Rebuilds

Hot reload triggers too frequently or doesn't work properly with volume mounts.

### Solution 1: Selective Volume Mounts

Mount only the directories that need hot reload:

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  web:
    build: .
    volumes:
      # Mount only source code directories
      - ./app:/app/app:ro  # Read-only for safety
      - ./tests:/app/tests:ro

      # Exclude Python cache and build artifacts
      - /app/app/__pycache__
      - /app/tests/__pycache__
      - /app/.pytest_cache

      # Mount logs as writable
      - ./logs:/app/logs:rw
    environment:
      - PYTHONDONTWRITEBYTECODE=1  # Prevent .pyc files
```

### Solution 2: Use watchfiles for Better File Watching

```dockerfile
# Dockerfile.dev
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Install watchfiles for better file watching
RUN pip install watchfiles

COPY . .

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0"]
```

**requirements-dev.txt:**
```
watchfiles==0.21.0
```

### Solution 3: Configure Reload Patterns

```yaml
# docker-compose.dev.yml
services:
  web:
    command: >
      uvicorn app.main:app
      --reload
      --reload-dir /app/app
      --reload-include '*.py'
      --reload-exclude '*.pyc'
      --host 0.0.0.0
      --port 8000
```

### Solution 4: Polling for Network Mounts (Windows/macOS)

For Docker Desktop on Windows/macOS, use polling for file changes:

```yaml
services:
  web:
    environment:
      - WATCHFILES_FORCE_POLLING=true
    command: uvicorn app.main:app --reload --reload-delay 2 --host 0.0.0.0
```

## Database Seeding and Fixtures

### Strategy 1: SQL Init Scripts

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: myapp_dev
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

**database/init/01-schema.sql:**
```sql
-- Create tables
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
```

**database/init/02-seed.sql:**
```sql
-- Seed development data
INSERT INTO users (email, name) VALUES
    ('alice@example.com', 'Alice Smith'),
    ('bob@example.com', 'Bob Johnson'),
    ('charlie@example.com', 'Charlie Brown')
ON CONFLICT (email) DO NOTHING;
```

### Strategy 2: Python Seed Script

**scripts/seed_db.py:**
```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import User, Item
from app.config import settings

async def seed_database():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute("SELECT COUNT(*) FROM users")
        count = result.scalar()

        if count > 0:
            print("Database already seeded, skipping...")
            return

        # Create seed data
        users = [
            User(email="alice@example.com", name="Alice Smith"),
            User(email="bob@example.com", name="Bob Johnson"),
        ]

        session.add_all(users)
        await session.commit()
        print(f"✅ Seeded {len(users)} users")

if __name__ == "__main__":
    asyncio.run(seed_database())
```

**entrypoint.sh:**
```bash
#!/bin/bash
set -e

echo "Waiting for database..."
while ! pg_isready -h db -p 5432 -U ${POSTGRES_USER} > /dev/null 2>&1; do
  sleep 1
done

echo "Running migrations..."
alembic upgrade head

echo "Seeding database..."
python scripts/seed_db.py

echo "Starting application..."
exec "$@"
```

### Strategy 3: Fixtures with pytest

**tests/conftest.py:**
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.main import app
from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("postgresql://test:test@db:5432/test_db")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def sample_user(db_session):
    user = User(email="test@example.com", name="Test User")
    db_session.add(user)
    db_session.commit()
    return user
```

## Environment Switching

### Strategy 1: Multiple Compose Files

**docker-compose.yml (base):**
```yaml
version: '3.8'

services:
  web:
    build: .
    depends_on:
      - db
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    networks:
      - app-network

networks:
  app-network:
```

**docker-compose.dev.yml (development overrides):**
```yaml
version: '3.8'

services:
  web:
    build:
      target: development
    ports:
      - "8000:8000"
      - "5678:5678"
    volumes:
      - .:/app
      - /app/__pycache__
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
      - DATABASE_URL=postgresql://dev:dev@db:5432/dev_db
    command: uvicorn app.main:app --reload --host 0.0.0.0

  db:
    environment:
      POSTGRES_DB: dev_db
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
    ports:
      - "5432:5432"
```

**docker-compose.prod.yml (production overrides):**
```yaml
version: '3.8'

services:
  web:
    build:
      target: production
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - DATABASE_URL=postgresql://prod:prod@db:5432/prod_db
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1G

  db:
    environment:
      POSTGRES_DB: prod_db
      POSTGRES_USER: prod
      POSTGRES_PASSWORD: prod
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

**Usage:**
```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Testing
docker-compose -f docker-compose.yml -f docker-compose.test.yml run web pytest
```

### Strategy 2: Environment-Specific .env Files

**.env.development:**
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=debug
DATABASE_URL=postgresql://dev:dev@db:5432/dev_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=dev-secret-key-not-for-production
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

**.env.production:**
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
DATABASE_URL=postgresql://prod:prod@db:5432/prod_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=${SECRET_KEY}
CORS_ORIGINS=https://myapp.com
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  web:
    build: .
    env_file:
      - .env.${ENVIRONMENT:-development}
```

**Usage:**
```bash
# Development (default)
docker-compose up

# Production
ENVIRONMENT=production docker-compose up -d
```

### Strategy 3: Config Class with Environment Detection

**app/config.py:**
```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    environment: str = "development"
    debug: bool = False
    database_url: str
    redis_url: str
    secret_key: str

    class Config:
        env_file = ".env"
        case_sensitive = False

class DevelopmentSettings(Settings):
    debug: bool = True
    log_level: str = "debug"

class ProductionSettings(Settings):
    debug: bool = False
    log_level: str = "info"

@lru_cache()
def get_settings() -> Settings:
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()

settings = get_settings()
```

## Multi-Architecture Builds

### Problem: Building for ARM64 (Apple Silicon M1/M2/M3)

Docker images built on x86_64 machines don't run efficiently on ARM64 Macs.

### Solution 1: Use buildx for Multi-Platform Builds

```bash
# Create a new builder instance
docker buildx create --name multiarch --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myapp:latest \
  --push \
  .

# Or build and load for local use
docker buildx build \
  --platform linux/arm64 \
  -t myapp:latest \
  --load \
  .
```

### Solution 2: Platform-Specific Base Images

```dockerfile
#syntax=docker/dockerfile:1

# Use platform-specific base image
FROM --platform=$BUILDPLATFORM python:3.11-slim as builder

ARG TARGETPLATFORM
ARG BUILDPLATFORM

RUN echo "Building on $BUILDPLATFORM for $TARGETPLATFORM"

WORKDIR /app

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

ENV PATH="/app/venv/bin:$PATH"

COPY --from=builder /app/venv /app/venv
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### Solution 3: Docker Compose with Platform Specification

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build:
      context: .
      platforms:
        - linux/amd64
        - linux/arm64
    platform: linux/arm64  # Force ARM64 on M1/M2 Macs
```

### Solution 4: Conditional Dependencies for ARM64

```dockerfile
#syntax=docker/dockerfile:1

FROM python:3.11-slim

WORKDIR /app

# Install platform-specific dependencies
RUN if [ "$(uname -m)" = "aarch64" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ && \
      rm -rf /var/lib/apt/lists/*; \
    fi

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

## Development Workflow Scripts

### Makefile for Common Tasks

**Makefile:**
```makefile
.PHONY: help build up down logs shell test clean

help:
	@echo "Available commands:"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start development environment"
	@echo "  make down     - Stop all containers"
	@echo "  make logs     - View container logs"
	@echo "  make shell    - Open shell in web container"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Remove all containers and volumes"

build:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

up:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

down:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

logs:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

shell:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec web bash

test:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml run --rm web pytest

clean:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
	docker system prune -f
```

### Shell Scripts for Development

**scripts/dev.sh:**
```bash
#!/bin/bash
set -e

echo "🚀 Starting development environment..."

# Export user ID for volume permissions
export UID=$(id -u)
export GID=$(id -g)

# Enable BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Start services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Cleanup on exit
trap "docker-compose -f docker-compose.yml -f docker-compose.dev.yml down" EXIT
```

**scripts/test.sh:**
```bash
#!/bin/bash
set -e

echo "🧪 Running tests..."

docker-compose -f docker-compose.yml -f docker-compose.test.yml run --rm web pytest -v

echo "✅ Tests completed!"
```

## Performance Optimization Tips

### 1. Use .dockerignore Aggressively
```
**/.git
**/__pycache__
**/.pytest_cache
**/.venv
**/venv
**/*.pyc
**/node_modules
**/coverage
**/.coverage
**/htmlcov
**/*.log
```

### 2. Optimize Layer Caching Order
```dockerfile
# Copy requirements first (changes less frequently)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code last (changes most frequently)
COPY . .
```

### 3. Use Smaller Base Images
```dockerfile
# Good: 150MB
FROM python:3.11-slim

# Better: 50MB (but may have compatibility issues)
FROM python:3.11-alpine
```

### 4. Parallel Builds with BuildKit
```bash
export DOCKER_BUILDKIT=1
docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t myapp .
```

### 5. Use Docker Compose Profiles
```yaml
services:
  web:
    profiles: ["app"]

  worker:
    profiles: ["app", "worker"]

  db:
    profiles: ["app", "worker"]
```

```bash
# Start only app services
docker-compose --profile app up

# Start app and worker services
docker-compose --profile app --profile worker up
```

## Summary

Optimizing your Docker development workflow involves:

1. **Caching**: Use BuildKit cache mounts and layer caching
2. **Debugging**: Set up remote debugging with debugpy
3. **Hot Reload**: Configure selective volume mounts and file watching
4. **Database**: Implement seeding strategies for consistent dev data
5. **Environments**: Use compose overrides for different environments
6. **Multi-arch**: Build for ARM64 when developing on Apple Silicon
7. **Automation**: Create scripts and Makefiles for common tasks

These optimizations significantly improve the daily development experience while maintaining production-ready configurations.
