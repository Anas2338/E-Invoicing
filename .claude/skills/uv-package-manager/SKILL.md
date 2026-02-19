---
name: uv-package-manager
description: |
  This skill helps users manage Python projects with uv, the extremely fast Python package and project manager written in Rust. Use when initializing projects, managing dependencies, working with virtual environments, or optimizing Python development workflows with uv's performance advantages over traditional tools.
allowed-tools: Bash
---

# uv Package Manager Expert

## Overview
uv is an extremely fast Python package and project manager written in Rust, designed to replace tools like pip, pip-tools, pipx, poetry, and more, offering enhanced speed and comprehensive project management features.

## Project Initialization

### Initialize New Projects
```bash
# Create a new project with complete structure
uv init project-name
cd project-name

# Initialize in existing directory
mkdir my-project && cd my-project
uv init

# Initialize with specific Python version
uv init --python 3.11 my-app
```

The generated `pyproject.toml` includes:
```toml
[project]
name = "hello-world"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
dependencies = []
```

### Python Version Management
```bash
# Pin Python version for project (creates .python-version)
uv python pin 3.11
uv python pin 3.11.5
uv python pin pypy@3.9

# Install specific Python versions
uv python install 3.11
uv python install 3.10 3.11 3.12
uv python install cpython@3.11.5
uv python install pypy@3.9

# List installed Python versions
uv python list
uv python list --only-installed

# Find Python interpreter
uv python find
uv python find 3.11
uv python find pypy
```

## Dependency Management

### Adding Dependencies
```bash
# Add standard dependencies (updates pyproject.toml, uv.lock, and .venv)
uv add requests
uv add 'flask>=2.0'
uv add 'django>=4.0,<5.0'

# Add development dependencies
uv add --dev pytest pytest-cov black

# Add optional dependency groups
uv add --group docs sphinx sphinx-rtd-theme
```

### Advanced Dependency Sources
```bash
# Add from Git repository
uv add git+https://github.com/psf/requests
uv add git+https://github.com/pallets/flask@main
uv add git+ssh://git@github.com/user/repo.git@v1.0.0

# Add from local path
uv add --editable ./local-package
uv add ../another-project

# Add from URL
uv add https://files.pythonhosted.org/packages/.../requests-2.31.0.tar.gz
```

### Removing Dependencies
```bash
# Remove dependencies
uv remove requests flask
uv remove --dev pytest  # Remove dev dependency
uv remove --group docs  # Remove group
```

### Migrating from requirements.txt
```bash
# Migrate from requirements.txt
uv add -r requirements.txt
```

## Lockfile and Environment Management

### Lockfile Operations
```bash
# Generate/update lockfile (resolves dependencies)
uv lock

# Lock with specific upgrades
uv lock --upgrade-package requests  # Upgrade specific package
uv lock --upgrade  # Upgrade all packages

# Generate lockfile without installing (CI/CD)
uv lock --locked
```

### Environment Synchronization
```bash
# Sync environment to match lockfile
uv sync

# Sync without updating lockfile (frozen)
uv sync --frozen

# Sync without installing project (useful in CI)
uv sync --frozen --no-install-project

# Sync specific groups
uv sync --group docs
uv sync --group test
```

## Virtual Environment Management

### Creating Virtual Environments
```bash
# Create virtual environment with specific Python version
uv venv --python 3.12.0
uv venv --python 3.11

# uv automatically creates .venv when needed during add/sync/run operations
```

### Using Virtual Environments
```bash
# Run commands in project environment
uv run python script.py
uv run pytest tests/
uv run black .
uv run my-command

# Run with specific Python version
uv run --python 3.11 script.py
uv run --python pypy@3.8 -- python
```

## Tool Management

### Installing and Running Tools
```bash
# Install tools globally (similar to pipx)
uv tool install ruff
uv tool install black
uv tool install pytest

# Run tools without installation
uvx ruff check .
uvx black .
uvx pytest

# Or use uv tool run
uv tool run ruff check .
```

## Performance Optimization

### Cache Management
```bash
# uv maintains a global cache for dependency deduplication
# Cache location:
# Unix: ~/.cache/uv
# macOS: ~/Library/Caches/uv
# Windows: %LOCALAPPDATA%\uv\cache

# Manage cache
uv cache dir  # Show cache directory
uv cache clean  # Clean entire cache
uv cache clean requests  # Clean specific package
uv cache prune  # Remove unreachable entries
uv cache prune --ci  # Optimize for CI (keep built wheels, remove downloads)

# Disable cache for specific operations
uv --no-cache pip install requests

# Use custom cache directory
uv --cache-dir /tmp/uv-cache pip install requests
```

## Recommended Workflows

### New Project Setup
```bash
# 1. Initialize project
uv init my-awesome-project
cd my-awesome-project

# 2. Pin Python version
uv python pin 3.11

# 3. Add dependencies
uv add requests fastapi pydantic
uv add --dev pytest black flake8

# 4. Run project-specific commands
uv run python -m my_project
uv run pytest

# 5. Lock dependencies
uv lock

# 6. Sync environment
uv sync
```

### Continuous Development
```bash
# After adding dependencies manually to pyproject.toml
uv sync  # Sync environment to reflect changes

# Before committing
uv lock  # Ensure lockfile is up to date

# When switching branches with different dependencies
uv sync  # Sync to new dependency set
```

### CI/CD Integration
```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync --frozen --no-install-project

      - name: Run tests
        run: uv run pytest

      - name: Build
        run: uv build

      # Cache for faster CI
      - uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
```

## Troubleshooting Common Issues

### Dependency Resolution Failures
```bash
# Try with specific upgrade
uv lock --upgrade-package problematic-package

# Clear cache and retry
uv cache clean
uv sync

# Force reinstall
rm -rf .venv
uv sync
```

### Python Version Issues
```bash
# If Python version not found
uv python install 3.11
uv python list  # Check what's available
uv python pin 3.11  # Ensure project uses correct version
```

## Key Advantages Over Traditional Tools

- **Speed**: 10-100x faster than pip/pip-tools/poetry
- **Unified Tool**: Replaces pip, pip-tools, pipx, poetry, pyenv
- **Reproducible**: Universal lockfile ensures consistent environments
- **Performance**: Global cache with dependency deduplication
- **Flexibility**: Works with existing pip-compatible packages
- **Cross-platform**: Supports macOS, Linux, and Windows
- **Disk-efficient**: Global cache for dependency deduplication

## Reference Documentation

This skill includes comprehensive reference documentation:

- **migration-guide.md**: Complete migration paths from Poetry, pip, pipenv, and pip-tools with command mappings, version specifier conversion, and troubleshooting
- **project-patterns.md**: Real-world patterns for monorepos, Docker integration, private package indexes, building/publishing, scripts, platform-specific dependencies, and CI/CD
- **advanced-dependencies.md**: Dependency groups, overrides, constraints, lockfile inspection, environment markers, security scanning, performance optimization, and troubleshooting

## When to Use This Skill

Use this skill when:
- Setting up new Python projects with optimal dependency management
- Migrating from pip/poetry/pipenv to uv for performance gains
- Managing virtual environments and Python versions
- Working with lockfiles for reproducible builds
- Installing and managing Python tools
- Optimizing CI/CD pipelines for Python projects
- Troubleshooting dependency resolution issues
- Following best practices for Python project structure
- Handling complex dependency scenarios (monorepos, private indexes, platform-specific packages)
- Building and publishing Python packages