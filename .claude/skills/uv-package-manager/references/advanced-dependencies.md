# Advanced Dependency Management and Troubleshooting

This guide covers complex dependency scenarios, debugging techniques, and advanced uv features for production environments.

## Dependency Groups and Extras

### Understanding Dependency Groups

uv supports multiple ways to organize optional dependencies:

**pyproject.toml:**
```toml
[project]
name = "myapp"
version = "0.1.0"
dependencies = [
    "httpx>=0.25.0",
    "pydantic>=2.5.0",
]

# Standard extras (PEP 621)
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]
docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.5.0",
]
test = [
    "pytest>=7.4.0",
    "pytest-mock>=3.12.0",
    "faker>=22.0.0",
]
all = [
    "myapp[dev,docs,test]",  # Combine multiple extras
]
```

### Installing Specific Groups

```bash
# Install with dev dependencies
uv sync --extra dev

# Install with multiple extras
uv sync --extra dev --extra docs

# Install all extras
uv sync --all-extras

# Install without any extras (production)
uv sync --no-dev
```

### Custom Dependency Groups (uv-specific)

```toml
[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "ruff>=0.1.0",
]

[tool.uv.groups]
profiling = [
    "py-spy>=0.3.14",
    "memray>=1.10.0",
]
security = [
    "bandit>=1.7.5",
    "safety>=3.0.0",
]
```

```bash
# Install specific group
uv sync --group profiling

# Install multiple groups
uv sync --group profiling --group security
```

### Conditional Extras

```toml
[project.optional-dependencies]
# Only install on specific platforms
linux = [
    "uvloop>=0.19.0; sys_platform == 'linux'",
]
# Only for specific Python versions
typing = [
    "typing-extensions>=4.0.0; python_version < '3.11'",
]
# Combine conditions
advanced = [
    "uvloop>=0.19.0; sys_platform == 'linux' and python_version >= '3.11'",
]
```

## Dependency Overrides and Constraints

### Override Transitive Dependencies

When a dependency of your dependency has a security vulnerability or bug:

**pyproject.toml:**
```toml
[tool.uv]
override-dependencies = [
    "urllib3>=2.0.0",  # Force minimum version
    "certifi>=2023.7.22",  # Security patch
]
```

**Example scenario:**
```
Your app depends on:
  requests==2.31.0
    └── urllib3==1.26.0 (vulnerable)

With override:
  requests==2.31.0
    └── urllib3==2.0.7 (forced upgrade)
```

### Constraint Dependencies

Prevent specific versions without forcing a particular version:

```toml
[tool.uv]
constraint-dependencies = [
    "numpy<2.0.0",  # Prevent numpy 2.x
    "pandas>=2.0.0,<2.2.0",  # Constrain range
]
```

### Resolution Strategy

```toml
[tool.uv]
# Prefer lowest compatible versions (for testing compatibility)
resolution = "lowest"

# Or prefer highest (default)
resolution = "highest"

# Lowest direct dependencies, highest transitive
resolution = "lowest-direct"
```

### Handling Conflicting Dependencies

**Scenario:** Package A requires B>=2.0, Package C requires B<2.0

**Solution 1: Override one dependency**
```toml
[tool.uv]
override-dependencies = [
    "package-b>=2.0.0",  # Force newer version
]
```

**Solution 2: Use alternative package**
```toml
[project]
dependencies = [
    "package-a>=1.0.0",
    "package-c-alternative>=1.0.0",  # Use different package
]
```

**Solution 3: Fork and patch**
```toml
[project]
dependencies = [
    "package-c @ git+https://github.com/yourorg/package-c@patched-for-b2",
]
```

## Understanding the Lockfile

### Lockfile Structure

**uv.lock:**
```toml
version = 1
requires-python = ">=3.11"

[[package]]
name = "httpx"
version = "0.25.2"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "certifi" },
    { name = "httpcore" },
    { name = "idna" },
    { name = "sniffio" },
]
wheels = [
    { url = "https://files.pythonhosted.org/...", hash = "sha256:..." },
]

[[package]]
name = "certifi"
version = "2023.11.17"
source = { registry = "https://pypi.org/simple" }
wheels = [
    { url = "https://files.pythonhosted.org/...", hash = "sha256:..." },
]
```

### Inspecting Dependencies

```bash
# Show dependency tree
uv tree

# Show why a package was installed
uv tree --package requests

# Show reverse dependencies (what depends on this)
uv tree --invert --package urllib3

# Show only direct dependencies
uv tree --depth 1

# Export to different formats
uv export --format requirements-txt > requirements.txt
uv export --format requirements-txt --no-hashes > requirements-no-hash.txt
```

### Debugging Resolution Issues

```bash
# Verbose resolution output
uv lock --verbose

# Show resolution strategy
uv lock --verbose 2>&1 | grep -i "resolving"

# Check for conflicts
uv pip check

# Dry run to see what would change
uv lock --dry-run
```

### Reading Dependency Trees

**Example output:**
```
myapp v0.1.0
├── httpx v0.25.2
│   ├── certifi v2023.11.17
│   ├── httpcore v1.0.2
│   │   ├── certifi v2023.11.17 (*)
│   │   └── h11 v0.14.0
│   ├── idna v3.6
│   └── sniffio v1.3.0
└── pydantic v2.5.3
    ├── pydantic-core v2.14.6
    └── typing-extensions v4.9.0

(*) = dependency already shown
```

**Interpreting the tree:**
- Direct dependencies are at the first level
- Transitive dependencies are indented
- `(*)` indicates a package already shown (prevents duplication)

## Platform and Environment Markers

### Marker Syntax

```toml
[project]
dependencies = [
    # Operating system
    "pywin32>=306; sys_platform == 'win32'",
    "pyobjc>=10.0; sys_platform == 'darwin'",
    "python-prctl>=1.8.1; sys_platform == 'linux'",

    # Python version
    "typing-extensions>=4.0.0; python_version < '3.11'",
    "tomli>=2.0.0; python_version < '3.11'",

    # Platform machine (architecture)
    "tensorflow-macos>=2.15.0; platform_machine == 'arm64'",
    "tensorflow>=2.15.0; platform_machine == 'x86_64'",

    # Python implementation
    "greenlet>=3.0.0; platform_python_implementation == 'CPython'",

    # Combined conditions
    "uvloop>=0.19.0; sys_platform == 'linux' and python_version >= '3.11'",
]
```

### Available Markers

| Marker | Example Values | Description |
|--------|---------------|-------------|
| `sys_platform` | `linux`, `darwin`, `win32` | Operating system |
| `platform_machine` | `x86_64`, `arm64`, `aarch64` | CPU architecture |
| `platform_system` | `Linux`, `Darwin`, `Windows` | OS name |
| `python_version` | `3.11`, `3.12` | Python version |
| `python_full_version` | `3.11.5` | Full Python version |
| `platform_python_implementation` | `CPython`, `PyPy` | Python implementation |
| `implementation_name` | `cpython`, `pypy` | Implementation name |
| `os_name` | `posix`, `nt` | OS type |

### Testing Markers Locally

```bash
# Check current environment markers
python -c "import sys; print(sys.platform)"
python -c "import platform; print(platform.machine())"

# Test if marker would match
python -c "import sys; print('linux' if sys.platform == 'linux' else 'other')"
```

### Complex Marker Examples

```toml
[project]
dependencies = [
    # Linux ARM64 with Python 3.11+
    "package-a>=1.0.0; sys_platform == 'linux' and platform_machine == 'aarch64' and python_version >= '3.11'",

    # Not Windows
    "package-b>=1.0.0; sys_platform != 'win32'",

    # Windows or old Python
    "package-c>=1.0.0; sys_platform == 'win32' or python_version < '3.11'",

    # Specific Python versions
    "package-d>=1.0.0; python_version in '3.11 3.12'",
]
```

## Security and Vulnerability Management

### Scanning for Vulnerabilities

```bash
# Install safety
uv tool install safety

# Scan dependencies
uv export --format requirements-txt | safety check --stdin

# Or use pip-audit
uv tool install pip-audit
uv export --format requirements-txt | pip-audit -r /dev/stdin
```

### Automated Security Updates

**GitHub Actions workflow:**
```yaml
name: Security Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v1

      - name: Install dependencies
        run: uv sync --frozen

      - name: Security scan
        run: |
          uv tool install safety
          uv export --format requirements-txt | safety check --stdin

      - name: Create issue if vulnerabilities found
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Security vulnerabilities detected',
              body: 'Automated security scan found vulnerabilities. Please review.',
              labels: ['security']
            })
```

### Updating Vulnerable Packages

```bash
# Update specific vulnerable package
uv lock --upgrade-package urllib3

# Update all packages
uv lock --upgrade

# Sync to apply updates
uv sync
```

### Pinning Secure Versions

```toml
[tool.uv]
override-dependencies = [
    "urllib3>=2.0.7",  # CVE-2023-45803 fix
    "certifi>=2023.7.22",  # CVE-2023-37920 fix
]
```

## Performance Optimization

### Parallel Installation

uv automatically parallelizes installations, but you can tune it:

```bash
# Use more parallel downloads (default: 4)
UV_CONCURRENT_DOWNLOADS=8 uv sync

# Use more parallel builds (default: number of CPUs)
UV_CONCURRENT_BUILDS=8 uv sync
```

### Offline Mode

For air-gapped environments or when network is unavailable:

```bash
# Populate cache first (on machine with internet)
uv sync

# Copy cache to offline machine
tar -czf uv-cache.tar.gz ~/.cache/uv

# On offline machine
tar -xzf uv-cache.tar.gz -C ~/

# Install from cache only
uv sync --offline
```

### Reducing Lockfile Size

```bash
# Exclude unnecessary platforms
uv lock --exclude-newer 2024-01-01

# Use resolution strategy
[tool.uv]
resolution = "lowest-direct"  # Smaller lockfile
```

### Optimizing for CI/CD

```yaml
# GitHub Actions
- name: Cache uv
  uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}

- name: Install dependencies
  run: |
    uv sync --frozen --no-install-project
    # Skip installing the project itself in CI if not needed
```

**Dockerfile optimization:**
```dockerfile
# Use cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
```

## Common Issues and Solutions

### Issue: "No solution found"

**Symptom:**
```
error: No solution found when resolving dependencies:
  package-a 1.0.0 depends on package-b>=2.0.0
  package-c 1.0.0 depends on package-b<2.0.0
```

**Diagnosis:**
```bash
# Show verbose resolution
uv lock --verbose 2>&1 | grep -A 10 "conflict"

# Check dependency tree
uv tree --package package-b
```

**Solutions:**

1. **Update packages:**
```bash
uv lock --upgrade-package package-a
uv lock --upgrade-package package-c
```

2. **Override dependency:**
```toml
[tool.uv]
override-dependencies = ["package-b>=2.0.0"]
```

3. **Use alternative package:**
```toml
[project]
dependencies = [
    "package-a>=1.0.0",
    "package-c-alternative>=1.0.0",
]
```

### Issue: Conflicting Dependencies

**Symptom:**
```
error: Conflicting versions for package-x:
  1.0.0 (required by package-a)
  2.0.0 (required by package-b)
```

**Solution:**
```bash
# Find which packages require it
uv tree --invert --package package-x

# Try upgrading the packages that depend on it
uv lock --upgrade-package package-a --upgrade-package package-b

# Or override
[tool.uv]
override-dependencies = ["package-x>=2.0.0"]
```

### Issue: Yanked Packages

**Symptom:**
```
error: Package package-x 1.0.0 has been yanked
```

**Explanation:** Package maintainers can "yank" releases from PyPI to prevent new installations (usually due to critical bugs).

**Solution:**
```bash
# Update to non-yanked version
uv lock --upgrade-package package-x

# Or specify different version
uv add "package-x!=1.0.0"
```

### Issue: Network/Proxy Errors

**Symptom:**
```
error: Failed to download package-x
  Caused by: connection timeout
```

**Solutions:**

1. **Configure proxy:**
```bash
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1"
```

2. **Use alternative index:**
```toml
[tool.uv]
index-url = "https://mirror.example.com/simple"
```

3. **Increase timeout:**
```bash
UV_HTTP_TIMEOUT=300 uv sync  # 5 minutes
```

### Issue: Permission Errors

**Symptom:**
```
error: Permission denied (os error 13)
```

**Solutions:**

1. **Fix cache permissions:**
```bash
sudo chown -R $USER:$USER ~/.cache/uv
```

2. **Use custom cache directory:**
```bash
uv --cache-dir ./uv-cache sync
```

3. **Run without cache:**
```bash
uv --no-cache sync
```

### Issue: Cache Corruption

**Symptom:**
```
error: Failed to extract wheel
  Caused by: invalid gzip header
```

**Solution:**
```bash
# Clean cache
uv cache clean

# Or remove specific package
uv cache clean package-name

# Prune unreachable entries
uv cache prune

# Reinstall
uv sync
```

### Issue: Python Version Not Found

**Symptom:**
```
error: No Python interpreter found for Python 3.11
```

**Solution:**
```bash
# Install Python version
uv python install 3.11

# Or use specific version
uv python install 3.11.5

# List available versions
uv python list

# Pin version for project
uv python pin 3.11
```

### Issue: Slow Resolution

**Symptom:** `uv lock` takes several minutes.

**Diagnosis:**
```bash
# Run with verbose output
uv lock --verbose
```

**Solutions:**

1. **Use resolution strategy:**
```toml
[tool.uv]
resolution = "lowest-direct"  # Faster resolution
```

2. **Constrain problematic packages:**
```toml
[tool.uv]
constraint-dependencies = [
    "numpy<2.0.0",  # Reduce version space
]
```

3. **Update uv:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Issue: Editable Install Not Updating

**Symptom:** Changes to local package not reflected.

**Solution:**
```bash
# Reinstall in editable mode
uv sync --reinstall-package mypackage

# Or force reinstall everything
rm -rf .venv
uv sync
```

## Advanced Debugging Techniques

### Enable Debug Logging

```bash
# Maximum verbosity
UV_LOG=trace uv sync

# Or use verbose flag
uv sync -vvv
```

### Inspect Resolution Process

```bash
# Show what uv is doing
uv lock --verbose 2>&1 | tee resolution.log

# Analyze the log
grep -i "resolving" resolution.log
grep -i "conflict" resolution.log
grep -i "backtrack" resolution.log
```

### Compare Lockfiles

```bash
# Before changes
cp uv.lock uv.lock.old

# Make changes
uv add new-package

# Compare
diff uv.lock.old uv.lock
```

### Test Dependency Resolution

```bash
# Dry run to see what would change
uv lock --dry-run

# Test upgrade without applying
uv lock --upgrade --dry-run
```

### Reproduce Issues

```bash
# Create minimal reproduction
mkdir test-issue
cd test-issue
uv init

# Add problematic dependencies
uv add package-a package-b

# Try to lock
uv lock --verbose
```

## Best Practices Summary

1. **Use lockfiles**: Always commit `uv.lock` for reproducible builds
2. **Pin Python version**: Use `uv python pin` to ensure consistency
3. **Organize dependencies**: Use groups/extras for different environments
4. **Override carefully**: Document why overrides are needed
5. **Monitor security**: Regularly scan for vulnerabilities
6. **Cache in CI**: Use caching to speed up builds
7. **Test upgrades**: Use `--dry-run` before applying changes
8. **Document markers**: Comment complex environment markers
9. **Clean cache**: Periodically run `uv cache prune`
10. **Stay updated**: Keep uv itself up to date

## Quick Reference: Troubleshooting Commands

```bash
# Dependency inspection
uv tree                          # Show dependency tree
uv tree --package pkg            # Why is pkg installed?
uv tree --invert --package pkg   # What depends on pkg?

# Resolution debugging
uv lock --verbose                # Verbose resolution
uv lock --dry-run                # Test without applying
uv pip check                     # Check for conflicts

# Cache management
uv cache dir                     # Show cache location
uv cache clean                   # Clean entire cache
uv cache prune                   # Remove unreachable entries

# Environment inspection
uv python list                   # List Python versions
uv python find                   # Find current Python
uv pip list                      # List installed packages

# Recovery
rm -rf .venv && uv sync          # Fresh environment
uv sync --reinstall              # Reinstall all packages
uv --no-cache sync               # Bypass cache
```
