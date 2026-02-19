#!/bin/bash
# Docker initialization script for Python/FastAPI applications

set -e

echo "Docker FastAPI Containerizer - Initialization Script"
echo "=================================================="

# Function to detect if it's a FastAPI application
detect_fastapi() {
    if [ -f "main.py" ] || [ -f "app.py" ]; then
        if grep -q "FastAPI\|import.*fastapi" "main.py" 2>/dev/null || grep -q "FastAPI\|import.*fastapi" "app.py" 2>/dev/null; then
            echo "Detected FastAPI application"
            return 0
        fi
    fi
    echo "Could not detect FastAPI application. Please verify your project structure."
    return 1
}

# Function to create Dockerfile
create_dockerfile() {
    local app_file="$1"
    local multi_stage="$2"

    if [ "$multi_stage" = "true" ]; then
        cat > Dockerfile << 'EOF'
#syntax=docker/dockerfile:1

# === Build stage: Install dependencies and create virtual environment ===
FROM python:3.11-slim as builder

ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

# Install build dependencies if needed for certain packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc musl-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

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

COPY --from=builder /app/venv /app/venv
COPY . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/venv/bin/uvicorn", "APP_FILE_PLACEHOLDER", "--host", "0.0.0.0", "--port", "8000"]
EOF
    else
        cat > Dockerfile << 'EOF'
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

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "APP_FILE_PLACEHOLDER", "--host", "0.0.0.0", "--port", "8000"]
EOF
    fi

    # Replace placeholder with actual app file
    sed -i.bak "s/APP_FILE_PLACEHOLDER/$app_file/g" Dockerfile && rm Dockerfile.bak

    echo "Created Dockerfile for $app_file"
}

# Function to create docker-compose.yml
create_docker_compose() {
    cat > docker-compose.yml << 'EOF'
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
    restart: unless-stopped
EOF

    echo "Created docker-compose.yml"
}

# Function to create .dockerignore
create_docker_ignore() {
    cat > .dockerignore << 'EOF'
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
**/.vscode
**/.idea
**/dist
**/build
**/*.egg-info
EOF

    echo "Created .dockerignore"
}

# Main execution
if ! detect_fastapi; then
    echo "Please ensure you're in a FastAPI project directory with a main.py or app.py file."
    exit 1
fi

echo "Detecting application entry point..."
APP_FILE="main:app"
if [ -f "main.py" ] && grep -q "app = FastAPI" "main.py"; then
    APP_FILE="main:app"
elif [ -f "app.py" ] && grep -q "app = FastAPI" "app.py"; then
    APP_FILE="app:app"
else
    echo "Could not determine application entry point. Defaulting to main:app."
    echo "Please update the CMD instruction in the Dockerfile if needed."
fi

echo "Application entry point detected as: $APP_FILE"

echo "Choose Dockerfile type:"
echo "1) Multi-stage build (recommended for production)"
echo "2) Simple build (for development)"
read -p "Enter choice (1 or 2): " build_choice

MULTI_STAGE=false
if [ "$build_choice" = "1" ]; then
    MULTI_STAGE=true
fi

echo "Creating Docker configuration files..."

create_dockerfile "$APP_FILE" "$MULTI_STAGE"
create_docker_compose
create_docker_ignore

echo ""
echo "Docker configuration created successfully!"
echo ""
echo "Next steps:"
echo "1. Review the generated Dockerfile and customize if needed"
echo "2. Run 'docker build -t my-fastapi-app .' to build the image"
echo "3. Run 'docker-compose up' to start the application"
echo ""
echo "For production deployments, consider:"
echo "- Using Docker Hardened Images (DHI)"
echo "- Adding health checks"
echo "- Implementing secrets management"
echo "- Setting resource limits"