# Docker Compose Best Practices for Python/FastAPI Applications

## Basic Service Configuration

### Simple FastAPI Service
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
      - .:/app  # For development hot-reloading
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Ready Service
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
      - LOG_LEVEL=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

## Multi-Service Applications

### FastAPI with Database
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://fastapi_user:password@db:5432/fastapi_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: fastapi_db
      POSTGRES_USER: fastapi_user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fastapi_user -d fastapi_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres_data:
```

## Environment-Specific Configurations

### Development Configuration
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  web:
    build:
      context: .
      target: development
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - /app/__pycache__  # Exclude Python cache
    environment:
      - ENVIRONMENT=development
      - DEBUG=1
      - RELOAD=true
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Configuration
```yaml
# docker-compose.prod.yml
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
      - DEBUG=0
      - WORKERS=4
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 512M
```

## Secrets Management

### Using Docker Secrets
```yaml
# docker-compose.secrets.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    secrets:
      - db_password
      - jwt_secret
    environment:
      - DB_PASSWORD_FILE=/run/secrets/db_password
      - JWT_SECRET_FILE=/run/secrets/jwt_secret

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: myuser
    secrets:
      - db_password
    command: >
      bash -c "
        export PGPASSWORD=$$(cat /run/secrets/db_password)
        exec postgres
      "

secrets:
  db_password:
    file: ./secrets/db_password.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
```

## Advanced Configuration Patterns

### Load Balancing with Multiple Instances
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - web1
      - web2
    restart: unless-stopped

  web1:
    build: .
    environment:
      - INSTANCE_ID=web1
    restart: unless-stopped

  web2:
    build: .
    environment:
      - INSTANCE_ID=web2
    restart: unless-stopped
```

### Monitoring and Logging
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.web.rule=Host(`myapp.local`)"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_storage:/var/lib/grafana
    restart: unless-stopped

volumes:
  grafana_storage:
```

## Override Patterns

### Local Development Overrides
```yaml
# docker-compose.override.yml
version: '3.8'

services:
  web:
    volumes:
      - .:/app
    environment:
      - DEBUG=1
      - RELOAD=1
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing Overrides
```yaml
# docker-compose.test.yml
version: '3.8'

services:
  web:
    environment:
      - ENVIRONMENT=test
      - DATABASE_URL=postgresql://test_user:test_pass@test_db:5432/test_db
    depends_on:
      - test_db

  test_db:
    image: postgres:15
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    volumes:
      - test_postgres_data:/var/lib/postgresql/data

volumes:
  test_postgres_data:
```

## Complete Production Example

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
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=info
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 512M
    networks:
      - app-network

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mydb"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

## Commands for Different Environments

### Development
```bash
# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Build and start
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Production
```bash
# Start production environment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Build and start production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

### Testing
```bash
# Run tests
docker-compose -f docker-compose.yml -f docker-compose.test.yml run web pytest
```