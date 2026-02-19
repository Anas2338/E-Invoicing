# Migration Guide to uv

This guide helps you migrate existing Python projects from other package managers to uv.

## Quick Reference: Command Mapping

### From Poetry

| Poetry Command | uv Equivalent | Notes |
|----------------|---------------|-------|
| `poetry init` | `uv init` | Initialize new project |
| `poetry install` | `uv sync` | Install all dependencies |
| `poetry add requests` | `uv add requests` | Add dependency |
| `poetry add --group dev pytest` | `uv add --dev pytest` | Add dev dependency |
| `poetry remove requests` | `uv remove requests` | Remove dependency |
| `poetry update` | `uv lock --upgrade` | Update all dependencies |
| `poetry update requests` | `uv lock --upgrade-package requests` | Update specific package |
| `poetry run python script.py` | `uv run python script.py` | Run command in venv |
| `poetry shell` | `uv run bash` or `uv run zsh` | Activate shell |
| `poetry build` | `uv build` | Build package |
| `poetry publish` | `uv publish` | Publish to PyPI |
| `poetry show` | `uv tree` | Show dependencies |
| `poetry show --tree` | `uv tree` | Show dependency tree |
| `poetry env info` | `uv python find` | Show Python info |
| `poetry lock` | `uv lock` | Generate lockfile |
| `poetry export -f requirements.txt` | N/A | Use pyproject.toml directly |

### From pip + requirements.txt

| pip Command | uv Equivalent | Notes |
|-------------|---------------|-------|
| `pip install -r requirements.txt` | `uv pip install -r requirements.txt` | Install from requirements |
| `pip install requests` | `uv pip install requests` | Install package |
| `pip install -e .` | `uv pip install -e .` | Editable install |
| `pip freeze > requirements.txt` | `uv pip freeze > requirements.txt` | Export dependencies |
| `pip list` | `uv pip list` | List installed packages |
| `pip show requests` | `uv pip show requests` | Show package info |
| `pip uninstall requests` | `uv pip uninstall requests` | Uninstall package |

**Better approach with uv project management:**
- `uv add -r requirements.txt` - Migrate to pyproject.toml
- `uv sync` - Install from pyproject.toml

### From pipenv

| pipenv Command | uv Equivalent | Notes |
|----------------|---------------|-------|
| `pipenv install` | `uv sync` | Install dependencies |
| `pipenv install requests` | `uv add requests` | Add dependency |
| `pipenv install --dev pytest` | `uv add --dev pytest` | Add dev dependency |
| `pipenv uninstall requests` | `uv remove requests` | Remove dependency |
| `pipenv update` | `uv lock --upgrade` | Update all |
| `pipenv run python script.py` | `uv run python script.py` | Run in venv |
| `pipenv shell` | `uv run bash` | Activate shell |
| `pipenv lock` | `uv lock` | Generate lockfile |
| `pipenv graph` | `uv tree` | Show dependency tree |

### From pip-tools

| pip-tools Command | uv Equivalent | Notes |
|-------------------|---------------|-------|
| `pip-compile requirements.in` | `uv lock` | Generate lockfile |
| `pip-sync requirements.txt` | `uv sync` | Sync environment |
| `pip-compile --upgrade` | `uv lock --upgrade` | Update all |
| `pip-compile --upgrade-package requests` | `uv lock --upgrade-package requests` | Update specific |

## Migrating from Poetry

### Step 1: Understand Your Current Setup

**Check your current Poetry configuration:**
```bash
# View current dependencies
poetry show

# View dependency tree
poetry show --tree

# Check Python version
poetry env info
```

### Step 2: Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Step 3: Convert pyproject.toml

Poetry's `pyproject.toml` is mostly compatible with uv, but some sections need adjustment.

**Before (Poetry):**
```toml
[tool.poetry]
name = "my-project"
version = "0.1.0"
description = "My awesome project"
authors = ["Your Name <you@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.31.0"
fastapi = ">=0.109.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^23.0.0"
ruff = "^0.1.0"

[tool.poetry.scripts]
my-cli = "my_project.cli:main"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**After (uv):**
```toml
[project]
name = "my-project"
version = "0.1.0"
description = "My awesome project"
authors = [
    {name = "Your Name", email = "you@example.com"}
]
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31.0",
    "fastapi>=0.109.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
my-cli = "my_project.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Key differences:**
- `[tool.poetry]` → `[project]`
- `python = "^3.11"` → `requires-python = ">=3.11"`
- `[tool.poetry.dependencies]` → `[project.dependencies]`
- `[tool.poetry.group.dev.dependencies]` → `[project.optional-dependencies] dev = [...]`
- Poetry's `^` (caret) operator → Standard version specifiers (`>=`, `<`, etc.)
- Build backend: `poetry-core` → `hatchling` (or `setuptools`, `flit`)

### Step 4: Convert Version Specifiers

Poetry uses special version syntax that needs conversion:

| Poetry | Standard (uv) | Meaning |
|--------|---------------|---------|
| `^2.31.0` | `>=2.31.0,<3.0.0` | Compatible release |
| `~2.31.0` | `>=2.31.0,<2.32.0` | Patch updates only |
| `^0.1.0` | `>=0.1.0,<0.2.0` | 0.x versions |
| `*` | `>=0` | Any version |
| `2.31.*` | `>=2.31.0,<2.32.0` | Patch wildcard |

**Conversion script:**
```python
# convert_poetry_versions.py
import re

def convert_poetry_version(spec):
    """Convert Poetry version specifier to standard format."""
    spec = spec.strip()

    # Caret (^) operator
    if spec.startswith('^'):
        version = spec[1:]
        parts = version.split('.')

        if parts[0] == '0':
            # ^0.x.y -> >=0.x.y,<0.(x+1).0
            if len(parts) > 1:
                return f">={version},<0.{int(parts[1])+1}.0"
        else:
            # ^x.y.z -> >=x.y.z,<(x+1).0.0
            return f">={version},<{int(parts[0])+1}.0.0"

    # Tilde (~) operator
    elif spec.startswith('~'):
        version = spec[1:]
        parts = version.split('.')
        if len(parts) >= 2:
            # ~x.y.z -> >=x.y.z,<x.(y+1).0
            return f">={version},<{parts[0]}.{int(parts[1])+1}.0"

    # Wildcard (*)
    elif '*' in spec:
        base = spec.replace('.*', '')
        parts = base.split('.')
        if len(parts) >= 2:
            return f">={base}.0,<{parts[0]}.{int(parts[1])+1}.0"

    return spec

# Example usage
print(convert_poetry_version("^2.31.0"))  # >=2.31.0,<3.0.0
print(convert_poetry_version("~2.31.0"))  # >=2.31.0,<2.32.0
print(convert_poetry_version("^0.1.0"))   # >=0.1.0,<0.2.0
```

### Step 5: Initialize uv Project

```bash
# Remove Poetry artifacts
rm -rf .venv poetry.lock

# Pin Python version (if you had a specific version)
uv python pin 3.11

# Generate lockfile from converted pyproject.toml
uv lock

# Sync environment
uv sync

# Verify installation
uv run python --version
uv run python -c "import requests; print(requests.__version__)"
```

### Step 6: Update Scripts and CI/CD

**Update package.json scripts (if using):**
```json
{
  "scripts": {
    "install": "uv sync",
    "test": "uv run pytest",
    "lint": "uv run ruff check .",
    "format": "uv run black ."
  }
}
```

**Update Makefile:**
```makefile
.PHONY: install test lint format

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run black .
```

**Update GitHub Actions:**
```yaml
# Before (Poetry)
- name: Install Poetry
  uses: snok/install-poetry@v1

- name: Install dependencies
  run: poetry install

- name: Run tests
  run: poetry run pytest

# After (uv)
- name: Install uv
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Set up Python
  run: uv python install 3.11

- name: Install dependencies
  run: uv sync --frozen

- name: Run tests
  run: uv run pytest
```

### Step 7: Handle Poetry-Specific Features

**Poetry Scripts:**
Poetry scripts in `[tool.poetry.scripts]` map directly to `[project.scripts]` in standard format.

**Poetry Plugins:**
Poetry plugins are not supported in uv. You'll need to find alternatives or use them as regular dependencies.

**Poetry Source Repositories:**
```toml
# Poetry
[tool.poetry.source]
name = "private"
url = "https://pypi.example.com/simple"

# uv
[tool.uv]
index-url = "https://pypi.example.com/simple"
# Or for additional indexes
extra-index-url = ["https://pypi.example.com/simple"]
```

## Migrating from pip + requirements.txt

### Step 1: Analyze Current Setup

```bash
# Check current dependencies
pip list

# Generate current requirements
pip freeze > requirements-backup.txt
```

### Step 2: Create pyproject.toml

```bash
# Initialize uv project
uv init

# This creates a basic pyproject.toml
```

### Step 3: Migrate Dependencies

**Option A: Automatic Migration**
```bash
# Add all dependencies from requirements.txt
uv add -r requirements.txt

# Add dev dependencies
uv add --dev -r requirements-dev.txt
```

**Option B: Manual Migration**

**Before (requirements.txt):**
```
requests==2.31.0
fastapi>=0.109.0
pydantic>=2.0.0,<3.0.0
uvicorn[standard]>=0.27.0
```

**After (pyproject.toml):**
```toml
[project]
name = "my-project"
version = "0.1.0"
dependencies = [
    "requests==2.31.0",
    "fastapi>=0.109.0",
    "pydantic>=2.0.0,<3.0.0",
    "uvicorn[standard]>=0.27.0",
]
```

### Step 4: Handle Special Cases

**Editable Installs:**
```bash
# Before
pip install -e ./local-package

# After
uv add --editable ./local-package
```

**Git Dependencies:**
```bash
# Before (requirements.txt)
git+https://github.com/user/repo.git@v1.0.0

# After
uv add git+https://github.com/user/repo.git@v1.0.0
```

**Constraints Files:**
```bash
# Before
pip install -r requirements.txt -c constraints.txt

# After (pyproject.toml)
[tool.uv]
constraint-dependencies = [
    "urllib3<2.0.0",
    "certifi>=2023.0.0",
]
```

### Step 5: Update Workflow

```bash
# Remove old virtual environment
rm -rf venv/

# Create lockfile
uv lock

# Sync environment
uv sync

# Verify
uv run python -c "import requests; print('Success!')"
```

## Migrating from pipenv

### Step 1: Export Current State

```bash
# Export current dependencies
pipenv requirements > requirements.txt
pipenv requirements --dev > requirements-dev.txt
```

### Step 2: Convert Pipfile to pyproject.toml

**Before (Pipfile):**
```toml
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
requests = "*"
fastapi = ">=0.109.0"

[dev-packages]
pytest = "*"
black = "*"

[requires]
python_version = "3.11"

[scripts]
test = "pytest tests/"
```

**After (pyproject.toml):**
```toml
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "requests",
    "fastapi>=0.109.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "black",
]

[project.scripts]
test = "pytest tests/"
```

### Step 3: Migrate

```bash
# Remove pipenv artifacts
rm -rf Pipfile Pipfile.lock

# Initialize uv
uv init

# Add dependencies
uv add -r requirements.txt
uv add --dev -r requirements-dev.txt

# Lock and sync
uv lock
uv sync
```

### Step 4: Update Environment Variables

Pipenv automatically loads `.env` files. With uv, you need to handle this explicitly:

```bash
# Install python-dotenv
uv add python-dotenv

# In your code
from dotenv import load_dotenv
load_dotenv()
```

Or use a tool like `direnv` or load manually:
```bash
# Load .env and run
set -a; source .env; set +a
uv run python script.py
```

## Migrating from pip-tools

### Step 1: Understand Current Setup

**Current structure:**
```
requirements.in      # Abstract dependencies
requirements.txt     # Locked dependencies (from pip-compile)
requirements-dev.in  # Dev dependencies
requirements-dev.txt # Locked dev dependencies
```

### Step 2: Convert to pyproject.toml

**Before (requirements.in):**
```
requests
fastapi>=0.109.0
pydantic
```

**After (pyproject.toml):**
```toml
[project]
name = "my-project"
version = "0.1.0"
dependencies = [
    "requests",
    "fastapi>=0.109.0",
    "pydantic",
]
```

### Step 3: Migrate

```bash
# Add dependencies from .in files
uv add -r requirements.in
uv add --dev -r requirements-dev.in

# Generate lockfile (replaces pip-compile)
uv lock

# Sync environment (replaces pip-sync)
uv sync
```

### Step 4: Update Workflow

**Before:**
```bash
pip-compile requirements.in
pip-compile requirements-dev.in
pip-sync requirements.txt requirements-dev.txt
```

**After:**
```bash
uv lock
uv sync
```

## Migration Checklist

### Pre-Migration
- [ ] Backup current lock files (poetry.lock, Pipfile.lock, requirements.txt)
- [ ] Document current Python version
- [ ] List all dependencies with versions
- [ ] Note any custom scripts or commands
- [ ] Check for private package indexes

### Migration
- [ ] Install uv
- [ ] Create/convert pyproject.toml
- [ ] Convert version specifiers
- [ ] Pin Python version with `uv python pin`
- [ ] Generate lockfile with `uv lock`
- [ ] Sync environment with `uv sync`
- [ ] Test imports: `uv run python -c "import package"`

### Post-Migration
- [ ] Update CI/CD pipelines
- [ ] Update documentation
- [ ] Update Makefile/scripts
- [ ] Update .gitignore (add `.venv/`, `uv.lock`)
- [ ] Remove old artifacts (poetry.lock, Pipfile.lock, etc.)
- [ ] Test all scripts and commands
- [ ] Verify builds work
- [ ] Update team documentation

### Verification
- [ ] All dependencies install correctly
- [ ] Tests pass: `uv run pytest`
- [ ] Application runs: `uv run python -m myapp`
- [ ] Build succeeds: `uv build`
- [ ] CI/CD pipeline works

## Common Migration Issues

### Issue: Version Conflicts After Migration

**Problem:** Dependencies that worked before now have conflicts.

**Solution:**
```bash
# Try upgrading all packages
uv lock --upgrade

# Or upgrade specific packages
uv lock --upgrade-package problematic-package

# Check dependency tree
uv tree
```

### Issue: Missing Development Dependencies

**Problem:** Dev dependencies not installed.

**Solution:**
```bash
# Ensure dev dependencies are in pyproject.toml
[project.optional-dependencies]
dev = ["pytest", "black", "ruff"]

# Sync with dev dependencies
uv sync --group dev
```

### Issue: Scripts Not Working

**Problem:** Poetry/pipenv scripts don't work with uv.

**Solution:**
```toml
# Ensure scripts are in [project.scripts]
[project.scripts]
my-command = "my_package.module:function"

# Run with uv
uv run my-command
```

### Issue: Private Package Index Not Working

**Problem:** Can't access private PyPI.

**Solution:**
```toml
[tool.uv]
index-url = "https://pypi.example.com/simple"

# Or with authentication
# Set in environment: UV_INDEX_URL=https://user:pass@pypi.example.com/simple
```

## Performance Comparison

After migration, you should see significant performance improvements:

| Operation | Poetry | pip-tools | uv | Speedup |
|-----------|--------|-----------|-----|---------|
| Install (cold) | 45s | 38s | 2s | 20-22x |
| Install (warm) | 12s | 10s | 0.5s | 20-24x |
| Lock | 30s | 25s | 1s | 25-30x |
| Add package | 15s | N/A | 0.3s | 50x |

## Next Steps

After successful migration:

1. **Optimize CI/CD**: Use uv's caching features
2. **Explore uv features**: Try `uv tool`, `uvx`, workspace management
3. **Update documentation**: Document new commands for team
4. **Monitor performance**: Track build and install times
5. **Share feedback**: Report issues or suggestions to uv team
