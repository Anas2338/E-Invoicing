# Real-World Project Patterns with uv

This guide demonstrates how to use uv in complex, real-world scenarios beyond basic package management.

## Monorepo and Workspace Management

### Basic Monorepo Structure

```
my-monorepo/
├── pyproject.toml          # Workspace root
├── uv.lock                 # Shared lockfile
├── packages/
│   ├── core/
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── myapp_core/
│   │   │       ├── __init__.py
│   │   │       └── utils.py
│   │   └── tests/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── myapp_api/
│   │   │       ├── __init__.py
│   │   │       └── main.py
│   │   └── tests/
│   └── cli/
│       ├── pyproject.toml
│       ├── src/
│       │   └── myapp_cli/
│       │       ├── __init__.py
│       │       └── main.py
│       └── tests/
└── README.md
```

### Workspace Root Configuration

**pyproject.toml (root):**
```toml
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]
```

### Package Configuration with Local Dependencies

**packages/core/pyproject.toml:**
```toml
[project]
name = "myapp-core"
version = "0.1.0"
description = "Core utilities for MyApp"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.5.0",
    "httpx>=0.25.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**packages/api/pyproject.toml:**
```toml
[project]
name = "myapp-api"
version = "0.1.0"
description = "API service for MyApp"
requires-python = ">=3.11"
dependencies = [
    "myapp-core",  # Local dependency
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
]

[tool.uv.sources]
myapp-core = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**packages/cli/pyproject.toml:**
```toml
[project]
name = "myapp-cli"
version = "0.1.0"
description = "CLI tool for MyApp"
requires-python = ">=3.11"
dependencies = [
    "myapp-core",  # Local dependency
    "myapp-api",   # Another local dependency
    "click>=8.1.0",
    "rich>=13.7.0",
]

[project.scripts]
myapp = "myapp_cli.main:cli"

[tool.uv.sources]
myapp-core = { workspace = true }
myapp-api = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Working with Monorepos

```bash
# From workspace root, sync all packages
uv sync

# Run tests for all packages
uv run pytest packages/*/tests/

# Run specific package
uv run --package myapp-api python -m myapp_api.main

# Add dependency to specific package
cd packages/api
uv add redis

# Build all packages
uv build --all

# Build specific package
uv build --package myapp-core
```

### Editable Local Dependencies

For development, use editable installs:

```toml
[tool.uv.sources]
myapp-core = { path = "../core", editable = true }
```

```bash
# Changes to myapp-core are immediately reflected in myapp-api
cd packages/core
# Edit src/myapp_core/utils.py

cd ../api
uv run python -c "from myapp_core import utils; print(utils.some_function())"
# Uses the edited version immediately
```

## Docker Integration

### Optimized Dockerfile with uv

**Dockerfile (Multi-stage with uv):**
```dockerfile
# syntax=docker/dockerfile:1

# Stage 1: Build stage with uv
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies to a virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "myapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Development Dockerfile

**Dockerfile.dev:**
```dockerfile
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install all dependencies including dev
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Application code will be mounted as volume

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "myapp.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose with uv

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  app-dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - /app/.venv  # Don't mount venv
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - DEBUG=true
    depends_on:
      - db
    profiles: ["dev"]

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d myapp"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
```

**Usage:**
```bash
# Production
docker-compose up app

# Development with hot reload
docker-compose --profile dev up app-dev
```

### Optimized Multi-Architecture Build

**Dockerfile (ARM64 + AMD64):**
```dockerfile
# syntax=docker/dockerfile:1

FROM --platform=$BUILDPLATFORM python:3.11-slim AS builder

ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Install dependencies for target platform
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY . .

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "myapp"]
```

**Build for multiple platforms:**
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myapp:latest \
  --push \
  .
```

## Private Package Indexes

### Configuring Private PyPI

**pyproject.toml:**
```toml
[tool.uv]
index-url = "https://pypi.example.com/simple"

# Or use default PyPI with additional private index
# index-url = "https://pypi.org/simple"
extra-index-url = ["https://pypi.example.com/simple"]
```

### Authentication Methods

**Method 1: Environment Variables**
```bash
# Set credentials in environment
export UV_INDEX_URL="https://user:password@pypi.example.com/simple"

# Or use token
export UV_INDEX_URL="https://__token__:pypi-token-here@pypi.example.com/simple"

uv sync
```

**Method 2: Credentials File**
```bash
# Create credentials file
mkdir -p ~/.config/uv
cat > ~/.config/uv/credentials.toml << EOF
[[index]]
url = "https://pypi.example.com/simple"
username = "user"
password = "password"
EOF

# Or use token
cat > ~/.config/uv/credentials.toml << EOF
[[index]]
url = "https://pypi.example.com/simple"
token = "pypi-token-here"
EOF
```

**Method 3: Keyring Integration**
```bash
# Install keyring
uv tool install keyring

# Store credentials
keyring set pypi.example.com username

# uv will automatically use keyring
uv sync
```

### Corporate Proxy Configuration

```bash
# Set proxy environment variables
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.company.com"

# Or configure in pyproject.toml
[tool.uv]
proxy = "http://proxy.company.com:8080"
```

### Multiple Package Sources

```toml
[tool.uv]
# Primary index
index-url = "https://pypi.org/simple"

# Additional indexes
extra-index-url = [
    "https://pypi.example.com/simple",      # Private packages
    "https://download.pytorch.org/whl/cpu", # PyTorch CPU builds
]

# Specify source for specific packages
[tool.uv.sources]
my-private-package = { index = "https://pypi.example.com/simple" }
torch = { index = "https://download.pytorch.org/whl/cpu" }
```

## Building and Publishing Packages

### Package Structure

```
my-package/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── core.py
│       └── py.typed
├── tests/
│   ├── __init__.py
│   └── test_core.py
└── docs/
    └── index.md
```

### Complete pyproject.toml for Publishing

```toml
[project]
name = "my-awesome-package"
version = "0.1.0"
description = "An awesome Python package"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "you@example.com"}
]
keywords = ["awesome", "package", "example"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "httpx>=0.25.0",
    "pydantic>=2.5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]
docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.5.0",
]

[project.urls]
Homepage = "https://github.com/username/my-awesome-package"
Documentation = "https://my-awesome-package.readthedocs.io"
Repository = "https://github.com/username/my-awesome-package"
Changelog = "https://github.com/username/my-awesome-package/blob/main/CHANGELOG.md"

[project.scripts]
my-cli = "my_package.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatchling.build.targets.wheel]
packages = ["src/my_package"]
```

### Building Packages

```bash
# Build wheel and sdist
uv build

# Output:
# dist/
#   my_awesome_package-0.1.0-py3-none-any.whl
#   my_awesome_package-0.1.0.tar.gz

# Build only wheel
uv build --wheel

# Build only sdist
uv build --sdist

# Build with specific output directory
uv build --out-dir build/
```

### Publishing to PyPI

```bash
# Install twine for publishing
uv tool install twine

# Test on TestPyPI first
uv run twine upload --repository testpypi dist/*

# Publish to PyPI
uv run twine upload dist/*

# Or use environment variables for credentials
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-token-here
uv run twine upload dist/*
```

### Publishing to Private PyPI

```bash
# Configure repository
cat > ~/.pypirc << EOF
[distutils]
index-servers =
    private

[private]
repository = https://pypi.example.com
username = user
password = password
EOF

# Upload
uv run twine upload --repository private dist/*
```

### Version Management

**Using dynamic versioning:**
```toml
[project]
name = "my-package"
dynamic = ["version"]

[tool.hatchling.version]
path = "src/my_package/__init__.py"
```

**src/my_package/__init__.py:**
```python
__version__ = "0.1.0"
```

**Automated version bumping:**
```bash
# Install bump2version
uv tool install bump2version

# Bump version
bump2version patch  # 0.1.0 -> 0.1.1
bump2version minor  # 0.1.1 -> 0.2.0
bump2version major  # 0.2.0 -> 1.0.0
```

## Scripts and Entry Points

### Console Scripts

**pyproject.toml:**
```toml
[project.scripts]
myapp = "myapp.cli:main"
myapp-admin = "myapp.admin:main"
myapp-worker = "myapp.worker:run"
```

**src/myapp/cli.py:**
```python
import click

@click.group()
def main():
    """MyApp CLI tool."""
    pass

@main.command()
def start():
    """Start the application."""
    click.echo("Starting MyApp...")

@main.command()
@click.option('--config', help='Config file path')
def configure(config):
    """Configure the application."""
    click.echo(f"Configuring with {config}")

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# After uv sync, scripts are available
uv run myapp start
uv run myapp configure --config config.yaml
uv run myapp-admin
```

### GUI Scripts

```toml
[project.gui-scripts]
myapp-gui = "myapp.gui:main"
```

### Custom Task Runner

**pyproject.toml:**
```toml
[tool.uv.scripts]
test = "pytest tests/"
lint = "ruff check src/"
format = "ruff format src/"
type-check = "mypy src/"
docs = "mkdocs serve"
all-checks = ["lint", "type-check", "test"]
```

**Usage:**
```bash
uv run test
uv run lint
uv run all-checks  # Runs lint, type-check, and test
```

### Pre-commit Integration

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: uv run ruff check
        language: system
        types: [python]
        pass_filenames: false

      - id: ruff-format
        name: ruff format
        entry: uv run ruff format
        language: system
        types: [python]
        pass_filenames: false

      - id: mypy
        name: mypy
        entry: uv run mypy
        language: system
        types: [python]
        pass_filenames: false
```

**Setup:**
```bash
# Install pre-commit
uv tool install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Platform-Specific Dependencies

### OS-Specific Packages

```toml
[project]
dependencies = [
    "httpx>=0.25.0",
    "pydantic>=2.5.0",
]

[project.optional-dependencies]
linux = [
    "uvloop>=0.19.0; sys_platform == 'linux'",
]
macos = [
    "pyobjc-framework-Cocoa>=10.0; sys_platform == 'darwin'",
]
windows = [
    "pywin32>=306; sys_platform == 'win32'",
    "wmi>=1.5.1; sys_platform == 'win32'",
]
```

**Install platform-specific dependencies:**
```bash
# On Linux
uv sync --group linux

# On macOS
uv sync --group macos

# On Windows
uv sync --group windows
```

### Python Version-Specific Dependencies

```toml
[project]
dependencies = [
    "typing-extensions>=4.0.0; python_version < '3.11'",
    "tomli>=2.0.0; python_version < '3.11'",
    "exceptiongroup>=1.0.0; python_version < '3.11'",
]
```

### Architecture-Specific Dependencies

```toml
[project.optional-dependencies]
arm64 = [
    "tensorflow-macos>=2.15.0; platform_machine == 'arm64'",
]
x86_64 = [
    "tensorflow>=2.15.0; platform_machine == 'x86_64'",
]
```

### Complex Environment Markers

```toml
[project]
dependencies = [
    # Only on Linux with Python 3.11+
    "uvloop>=0.19.0; sys_platform == 'linux' and python_version >= '3.11'",

    # Only on macOS ARM64
    "tensorflow-macos>=2.15.0; sys_platform == 'darwin' and platform_machine == 'arm64'",

    # Only on Windows or Python < 3.11
    "backports.zoneinfo>=0.2.1; sys_platform == 'win32' or python_version < '3.11'",
]
```

## CI/CD Patterns

### GitHub Actions

**.github/workflows/ci.yml:**
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v1
        with:
          version: "latest"

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --frozen --all-extras

      - name: Run tests
        run: uv run pytest tests/ --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v1

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync --frozen

      - name: Run ruff
        run: uv run ruff check .

      - name: Run mypy
        run: uv run mypy src/

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v1

      - name: Build package
        run: uv build

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/
```

### GitLab CI

**.gitlab-ci.yml:**
```yaml
image: python:3.11-slim

variables:
  UV_CACHE_DIR: "$CI_PROJECT_DIR/.cache/uv"

cache:
  paths:
    - .cache/uv

before_script:
  - curl -LsSf https://astral.sh/uv/install.sh | sh
  - export PATH="$HOME/.cargo/bin:$PATH"

stages:
  - test
  - build
  - deploy

test:
  stage: test
  script:
    - uv python install 3.11
    - uv sync --frozen
    - uv run pytest tests/ --cov

lint:
  stage: test
  script:
    - uv python install 3.11
    - uv sync --frozen
    - uv run ruff check .
    - uv run mypy src/

build:
  stage: build
  script:
    - uv build
  artifacts:
    paths:
      - dist/
```

### Caching Strategies

**Aggressive caching:**
```yaml
- name: Cache uv
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/uv
      .venv
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
    restore-keys: |
      uv-${{ runner.os }}-
```

**Minimal caching (faster restore):**
```yaml
- name: Cache uv
  uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
```

## Summary

These patterns cover the most common real-world scenarios:

1. **Monorepos**: Manage multiple related packages with shared dependencies
2. **Docker**: Optimize container builds with uv's speed
3. **Private Indexes**: Work with corporate package repositories
4. **Publishing**: Build and distribute packages to PyPI
5. **Scripts**: Create CLI tools and automate tasks
6. **Platform-Specific**: Handle OS and architecture differences
7. **CI/CD**: Integrate uv into automated pipelines

Each pattern is production-tested and optimized for uv's strengths.
