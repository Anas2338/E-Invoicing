# Real-World FastAPI Project Structures and Containerization

## Overview

This guide shows how to containerize FastAPI applications with different architectural patterns, from simple single-file apps to complex modular applications with databases, background tasks, and multiple services.

## Pattern 1: Simple Single-File Application

### Project Structure
```
simple-app/
├── main.py
├── requirements.txt
├── Dockerfile
└── .dockerignore
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
```

## Pattern 2: Modular Application with Routers

### Project Structure
```
modular-app/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── items.py
│   │   └── auth.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   └── utils/
│       ├── __init__.py
│       └── security.py
├── tests/
│   ├── __init__.py
│   ├── test_users.py
│   └── test_items.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

### Dockerfile
```dockerfile
#syntax=docker/dockerfile:1

FROM python:3.11-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH=/app

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app/venv /app/venv
COPY --chown=appuser:appuser app/ ./app/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
    volumes:
      - ./app:/app/app  # Mount only app directory for hot reload
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### .dockerignore
```
**/.git
**/.gitignore
**/__pycache__
**/.pytest_cache
**/.venv
**/venv
**/*.pyc
**/*.pyo
**/*.pyd
**/tests
**/.env
**/.env.*
**/docker-compose*.yml
**/Dockerfile*
**/.dockerignore
**/README.md
**/docs
**/.coverage
**/htmlcov
```

## Pattern 3: Application with Database (SQLAlchemy/SQLModel)

### Project Structure
```
db-app/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── user.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── users.py
│   └── crud/
│       ├── __init__.py
│       └── user.py
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
└── .env.example
```

### Dockerfile
```dockerfile
#syntax=docker/dockerfile:1

FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH=/app

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app/venv /app/venv
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser entrypoint.sh .

RUN chmod +x entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### entrypoint.sh
```bash
#!/bin/bash
set -e

echo "Waiting for database..."
while ! pg_isready -h db -p 5432 -U ${POSTGRES_USER:-postgres} > /dev/null 2>&1; do
  sleep 1
done
echo "Database is ready!"

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://fastapi_user:fastapi_pass@db:5432/fastapi_db
      - POSTGRES_USER=fastapi_user
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: fastapi_db
      POSTGRES_USER: fastapi_user
      POSTGRES_PASSWORD: fastapi_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fastapi_user -d fastapi_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

### app/database.py
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Pattern 4: Application with Background Tasks (Celery + Redis)

### Project Structure
```
celery-app/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── celery_app.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── email.py
│   │   └── reports.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── jobs.py
│   └── config.py
├── requirements.txt
├── Dockerfile
├── Dockerfile.worker
├── docker-compose.yml
└── .dockerignore
```

### Dockerfile (API)
```dockerfile
#syntax=docker/dockerfile:1

FROM python:3.11-slim as builder

WORKDIR /app

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH=/app

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app/venv /app/venv
COPY --chown=appuser:appuser app/ ./app/

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile.worker (Celery Worker)
```dockerfile
#syntax=docker/dockerfile:1

FROM python:3.11-slim as builder

WORKDIR /app

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV C_FORCE_ROOT=true

RUN useradd --create-home --shell /bin/bash celeryuser && \
    chown -R celeryuser:celeryuser /app

COPY --from=builder --chown=celeryuser:celeryuser /app/venv /app/venv
COPY --chown=celeryuser:celeryuser app/ ./app/

USER celeryuser

CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - app-network

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

### app/celery_app.py
```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.email", "app.tasks.reports"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```

## Pattern 5: Microservices with Multiple FastAPI Apps

### Project Structure
```
microservices/
├── services/
│   ├── auth/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── users/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── orders/
│       ├── app/
│       │   ├── __init__.py
│       │   └── main.py
│       ├── Dockerfile
│       └── requirements.txt
├── shared/
│   ├── __init__.py
│   └── utils.py
├── docker-compose.yml
└── nginx/
    └── nginx.conf
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - auth-service
      - users-service
      - orders-service
    restart: unless-stopped
    networks:
      - app-network

  auth-service:
    build:
      context: ./services/auth
    environment:
      - SERVICE_NAME=auth
      - DATABASE_URL=postgresql://user:pass@db:5432/auth_db
    depends_on:
      - db
    restart: unless-stopped
    networks:
      - app-network

  users-service:
    build:
      context: ./services/users
    environment:
      - SERVICE_NAME=users
      - DATABASE_URL=postgresql://user:pass@db:5432/users_db
      - AUTH_SERVICE_URL=http://auth-service:8000
    depends_on:
      - db
      - auth-service
    restart: unless-stopped
    networks:
      - app-network

  orders-service:
    build:
      context: ./services/orders
    environment:
      - SERVICE_NAME=orders
      - DATABASE_URL=postgresql://user:pass@db:5432/orders_db
      - AUTH_SERVICE_URL=http://auth-service:8000
      - USERS_SERVICE_URL=http://users-service:8000
    depends_on:
      - db
      - auth-service
      - users-service
    restart: unless-stopped
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

### nginx/nginx.conf
```nginx
events {
    worker_connections 1024;
}

http {
    upstream auth {
        server auth-service:8000;
    }

    upstream users {
        server users-service:8000;
    }

    upstream orders {
        server orders-service:8000;
    }

    server {
        listen 80;

        location /auth/ {
            proxy_pass http://auth/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /users/ {
            proxy_pass http://users/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /orders/ {
            proxy_pass http://orders/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

## Pattern 6: Application with Static Files and Frontend

### Project Structure
```
fullstack-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── routers/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── dist/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── nginx/
    └── nginx.conf
```

### backend/Dockerfile
```dockerfile
#syntax=docker/dockerfile:1

FROM python:3.11-slim as builder

WORKDIR /app

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH=/app

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app/venv /app/venv
COPY --chown=appuser:appuser app/ ./app/

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### frontend/Dockerfile
```dockerfile
#syntax=docker/dockerfile:1

FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
    environment:
      - CORS_ORIGINS=http://localhost:3000
    restart: unless-stopped
    networks:
      - app-network

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

## Best Practices Summary

### 1. Always Use Multi-Stage Builds
Reduces image size and improves security by separating build and runtime dependencies.

### 2. Set PYTHONPATH for Modular Apps
```dockerfile
ENV PYTHONPATH=/app
```

### 3. Use Entrypoint Scripts for Initialization
Run migrations, wait for dependencies, or perform setup tasks before starting the app.

### 4. Implement Health Checks
Essential for production deployments and orchestration platforms.

### 5. Use Docker Compose for Multi-Service Apps
Simplifies development and testing of complex applications.

### 6. Separate Development and Production Configurations
Use `docker-compose.override.yml` for local development overrides.

### 7. Mount Only Necessary Directories in Development
```yaml
volumes:
  - ./app:/app/app  # Not ./:/app
```

### 8. Use Networks for Service Isolation
Create custom networks to control service communication.

### 9. Implement Proper Logging
Configure uvicorn logging and use structured logging for production.

### 10. Use Secrets Management
Never hardcode secrets; use Docker secrets or environment files.
