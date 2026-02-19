---
name: docker-fastapi-containerizer
description: |
  This skill helps containerize Python/FastAPI applications from hello world to professional production deployments. It provides best practices for Dockerfiles, multi-stage builds, security configurations, and Docker Compose setups for Python/FastAPI applications. Use when users need to create Docker artifacts for their Python/FastAPI projects.
allowed-tools: Read, Grep, Glob, Bash
---

# Docker FastAPI Containerizer

This skill helps containerize Python/FastAPI applications from hello world to professional production deployments, following Docker best practices and security guidelines.

## What This Skill Does

- Creates optimized Dockerfiles for Python/FastAPI applications
- Implements multi-stage builds for reduced image size and enhanced security
- Sets up Docker Compose configurations for multi-service applications
- Applies security best practices (non-root users, hardened images)
- Provides production-ready configurations

## When to Use This Skill

Use when users need to containerize Python/FastAPI applications with proper security, performance, and maintainability considerations.

## Before Implementation

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Codebase** | Existing Python/FastAPI application structure, requirements.txt, entry points |
| **Conversation** | User's specific deployment requirements, environment constraints |
| **Skill References** | Docker best practices from `references/` (multi-stage builds, security, production configs, troubleshooting, project structures, development workflow) |
| **User Guidelines** | Team-specific conventions, security policies |

Ensure all required context is gathered before implementing.
Only ask user for THEIR specific requirements (domain expertise is in this skill).

## Reference Documentation

This skill includes comprehensive reference documentation:

- **dockerfile-best-practices.md**: Multi-stage builds, layer caching, production optimizations
- **docker-compose-configurations.md**: Multi-service setups, environment-specific configs, secrets management
- **security-best-practices.md**: Non-root users, minimal images, vulnerability management, network security
- **troubleshooting.md**: Common Docker issues and solutions (permissions, imports, database connections, hot reload, debugging)
- **project-structures.md**: Real-world FastAPI project patterns (modular apps, databases, Celery, microservices, fullstack)
- **development-workflow.md**: Development optimization (dependency caching, debugging setup, hot reload, database seeding, multi-arch builds)

## Dockerfile Best Practices for Python/FastAPI Applications

### 1. Multi-Stage Builds

Use multi-stage builds to separate build-time dependencies from runtime image:

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

### 2. Security Best Practices

- Use non-root users to reduce attack surface
- Implement Docker Hardened Images (DHI) when available
- Set environment variables to prevent bytecode generation and buffering
- Minimize installed packages in final image

### 3. Production Optimizations

- Use slim or alpine base images
- Clean up build dependencies in final stage
- Use `--no-cache-dir` with pip install
- Leverage Docker layer caching with proper COPY order

## Docker Compose Configuration

For multi-service applications, use Docker Compose with production-ready configurations:

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      target: production
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

## Production Deployment Patterns

### 1. Hello World to Production Scale

For simple applications:
- Basic Dockerfile with single stage
- Direct uvicorn command execution

For production applications:
- Multi-stage builds
- Health checks
- Proper logging
- Resource limits
- Security configurations

### 2. Environment-Specific Configurations

Different configurations for development, staging, and production:

Development:
- Volume mounts for hot reloading
- Debug mode enabled
- Additional development tools

Production:
- Optimized base images
- Security hardening
- Resource constraints
- Health checks

## Implementation Workflow

### Step 1: Analyze Application Structure
- Identify requirements.txt or pyproject.toml
- Locate application entry point
- Determine exposed port
- Identify additional dependencies

### Step 2: Choose Dockerfile Pattern
- Simple: Single-stage for basic applications
- Multi-stage: For production with optimized size
- Custom: With specific base image requirements

### Step 3: Apply Security Measures
- Create non-root user
- Use minimal base images
- Remove unnecessary packages
- Set appropriate environment variables

### Step 4: Optimize for Production
- Implement multi-stage builds
- Configure proper logging
- Add health checks
- Set resource limits

### Step 5: Create Supporting Files
- Docker Compose for multi-service apps
- .dockerignore file
- Build scripts if needed

## Common Dockerfile Patterns

### Basic FastAPI Application
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Multi-Stage with Builder Pattern
```dockerfile
#syntax=docker/dockerfile:1

FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH
```

## Docker Ignore Patterns

Create a `.dockerignore` file to exclude unnecessary files:

```
**/.git
**/.gitignore
**/.dockerignore
**/.env
**/.venv
**/venv
**/requirements-dev.txt
**/Dockerfile*
**/docker-compose*
**/.DS_Store
**/README.md
**/LICENSE
**/*.log
**/__pycache__
**/*.pyc
**/*.pyo
**/*.pyd
**/.pytest_cache
**/.coverage
**/htmlcov
**/node_modules
```

## Health Checks for Production

Add health checks to monitor application status:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

## Quality Checklist

Before finalizing Docker setup, ensure:

- [ ] Multi-stage build implemented for production
- [ ] Non-root user configured
- [ ] Minimal base image used
- [ ] Environment variables properly set
- [ ] Proper logging configuration
- [ ] .dockerignore file created
- [ ] Docker Compose available for multi-service
- [ ] Health checks implemented
- [ ] Security scan passed
- [ ] Resource limits configured