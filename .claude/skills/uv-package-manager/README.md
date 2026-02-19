# uv Package Manager Skill

This skill provides comprehensive guidance for managing Python projects with uv, the extremely fast Python package and project manager written in Rust.

## Overview

uv is designed to replace traditional Python package management tools (pip, pip-tools, pipx, poetry, pipenv) with a unified, high-performance solution that offers 10-100x faster dependency resolution and installation.

## Features

- **Project Initialization**: Set up new Python projects with proper structure
- **Dependency Management**: Add, remove, and update dependencies with lockfile support
- **Python Version Management**: Install and manage multiple Python versions
- **Virtual Environment Management**: Automatic venv creation and management
- **Tool Management**: Install and run Python tools globally (like pipx)
- **Migration Support**: Comprehensive guides for migrating from other tools
- **Performance Optimization**: Cache management and parallel installation
- **CI/CD Integration**: Optimized workflows for automated pipelines

## Components

- `SKILL.md`: Main skill documentation with core commands and workflows
- `references/`: Comprehensive documentation for advanced scenarios
  - `migration-guide.md`: Complete migration paths from Poetry, pip, pipenv, and pip-tools
  - `project-patterns.md`: Real-world patterns for monorepos, Docker, publishing, and CI/CD
  - `advanced-dependencies.md`: Dependency management, troubleshooting, and optimization

## Quick Start

### New Project
```bash
# Initialize project
uv init my-project
cd my-project

# Pin Python version
uv python pin 3.11

# Add dependencies
uv add fastapi uvicorn pydantic

# Add dev dependencies
uv add --dev pytest black ruff

# Run application
uv run python -m myapp
```

### Existing Project Migration
```bash
# From requirements.txt
uv add -r requirements.txt

# From Poetry
# Convert pyproject.toml, then:
uv lock
uv sync

# From pipenv
pipenv requirements > requirements.txt
uv add -r requirements.txt
```

## Key Advantages

- **Speed**: 10-100x faster than pip, pip-tools, and poetry
- **Unified Tool**: Replaces multiple tools with a single solution
- **Reproducible**: Universal lockfile ensures consistent environments
- **Performance**: Global cache with dependency deduplication
- **Cross-platform**: Supports macOS, Linux, and Windows
- **Disk-efficient**: Shared cache reduces storage requirements

## Use Cases

### Development Workflows
- Setting up new Python projects
- Managing dependencies across multiple environments
- Working with monorepos and workspaces
- Creating reproducible development environments

### Production Deployments
- Building optimized Docker images
- Publishing packages to PyPI
- Managing platform-specific dependencies
- Implementing secure CI/CD pipelines

### Migration Projects
- Moving from Poetry to uv
- Upgrading from pip + requirements.txt
- Transitioning from pipenv
- Converting pip-tools workflows

### Advanced Scenarios
- Private package indexes
- Dependency overrides and constraints
- Security vulnerability management
- Multi-architecture builds

## Reference Documentation

### Migration Guide
Complete migration paths with:
- Command mapping tables for Poetry, pip, pipenv, pip-tools
- Version specifier conversion (Poetry's `^` to standard format)
- pyproject.toml conversion examples
- CI/CD pipeline updates
- Common migration issues and solutions
- Migration checklists

### Project Patterns
Real-world patterns including:
- Monorepo/workspace management with local dependencies
- Docker integration with optimized multi-stage builds
- Private package index configuration and authentication
- Building and publishing packages to PyPI
- Console scripts and entry points
- Platform-specific dependencies (OS, architecture, Python version)
- GitHub Actions and GitLab CI integration

### Advanced Dependencies
Complex scenarios covering:
- Dependency groups and extras organization
- Overrides and constraints for conflict resolution
- Lockfile structure and inspection
- Environment markers for platform-specific packages
- Security scanning and vulnerability management
- Performance optimization techniques
- Comprehensive troubleshooting guide

## Common Commands

```bash
# Project management
uv init                          # Initialize new project
uv python pin 3.11              # Pin Python version

# Dependency management
uv add requests                 # Add dependency
uv add --dev pytest             # Add dev dependency
uv remove requests              # Remove dependency
uv lock                         # Generate/update lockfile
uv sync                         # Sync environment to lockfile

# Environment management
uv run python script.py         # Run command in venv
uv run pytest                   # Run tests
uv tree                         # Show dependency tree

# Tool management
uv tool install ruff            # Install tool globally
uvx ruff check .                # Run tool without installing

# Cache management
uv cache clean                  # Clean cache
uv cache prune                  # Remove unreachable entries
```

## Troubleshooting

Common issues and solutions are documented in `references/advanced-dependencies.md`:

- "No solution found" errors
- Conflicting dependencies
- Yanked packages
- Network/proxy issues
- Permission errors
- Cache corruption
- Python version not found
- Slow resolution

## Performance Tips

1. **Use BuildKit cache mounts** in Docker for faster builds
2. **Enable caching in CI/CD** to speed up pipelines
3. **Use `--frozen` flag** in production to skip resolution
4. **Leverage offline mode** for air-gapped environments
5. **Optimize lockfile size** with resolution strategies
6. **Clean cache periodically** with `uv cache prune`

## Best Practices

- Always commit `uv.lock` for reproducible builds
- Pin Python version with `uv python pin`
- Organize dependencies using groups/extras
- Document dependency overrides with comments
- Regularly scan for security vulnerabilities
- Use `--dry-run` to test changes before applying
- Keep uv itself up to date

## Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [Migration Guide](./references/migration-guide.md)
- [Project Patterns](./references/project-patterns.md)
- [Advanced Dependencies](./references/advanced-dependencies.md)

## When to Use This Skill

Use this skill when you need to:
- Set up new Python projects with modern tooling
- Migrate from legacy package managers
- Optimize dependency management workflows
- Troubleshoot dependency resolution issues
- Implement CI/CD pipelines for Python projects
- Build and publish Python packages
- Manage complex dependency scenarios
- Work with monorepos or multiple packages
- Handle platform-specific dependencies
- Integrate with Docker and containerization
