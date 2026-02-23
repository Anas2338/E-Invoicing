---
id: 005
title: Migrate to uv package manager
stage: misc
date: 2026-02-23
surface: agent
model: claude-opus-4-6
feature: 001-fbr-invoice-backend
branch: 001-fbr-invoice-backend
user: Anas2338
command: /sp.specify
labels: ["package-manager", "uv", "documentation", "tooling"]
links:
  spec: specs/001-fbr-invoice-backend/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-fbr-invoice-backend/research.md
  - specs/001-fbr-invoice-backend/quickstart.md
  - specs/001-fbr-invoice-backend/plan.md
tests:
  - Documentation consistency validated
  - All Poetry references replaced with uv equivalents
---

## Prompt

use uv package manager

## Response snapshot

Updated all technical documentation for the FBR Invoice Integration Backend to use uv package manager instead of Poetry. The migration includes comprehensive updates to installation instructions, dependency management commands, and development workflow documentation.

**Changes Made**:

1. **research.md** - Added uv as Technology Choice #9:
   - Version: 0.5.0+
   - Rationale: 10-100x faster than pip, built-in virtual environment management, lock file support
   - Performance benefits: 100x faster dependency resolution, 10x faster installation, 5x faster than Poetry cold cache
   - Key features: Fast dependency installation, virtual environment management, lock file generation, Python version management

2. **quickstart.md** - Comprehensive command updates:
   - Prerequisites: Changed from Poetry 1.7+ to uv 0.5.0+
   - Installation: Updated to uv installation commands (curl script for macOS/Linux, PowerShell for Windows)
   - Dependency management: `poetry install` → `uv sync`
   - Running commands: All commands now use `uv run` prefix (e.g., `uv run pytest`, `uv run uvicorn`)
   - Adding dependencies: `poetry add` → `uv add`, `poetry add --group dev` → `uv add --dev`
   - Project structure: Updated pyproject.toml description and added uv.lock reference
   - Development workflow: All command examples updated to use uv
   - Troubleshooting: Updated import error solutions to use `uv sync` and `uv venv`
   - Resources: Replaced Poetry documentation link with uv documentation
   - Last updated date: 2026-02-22 → 2026-02-23

3. **plan.md** - Project structure updates:
   - Phase 1 deliverables: "Poetry dependencies installed" → "uv dependencies installed"
   - Key files: "pyproject.toml - Dependencies" → "pyproject.toml - uv project configuration"
   - Added uv.lock to project structure documentation

**Rationale for Migration**:
- Performance: uv is 10-100x faster than pip and significantly faster than Poetry
- Simplicity: Single tool for dependency resolution, installation, and environment management
- Compatibility: Works with existing pip and requirements.txt workflows
- Modern tooling: Written in Rust, actively maintained by Astral (creators of Ruff)
- Lock file support: Provides reproducible builds with uv.lock

**Preserved References**:
- Performance comparison statements in research.md (e.g., "5x faster than Poetry") are intentionally kept as they demonstrate uv's advantages

## Outcome

- ✅ Impact: All technical documentation migrated from Poetry to uv package manager
- 🧪 Tests: Documentation consistency validated across all files
- 📁 Files: 3 files updated (research.md, quickstart.md, plan.md)
- 🔁 Next prompts: Ready to proceed with implementation using uv for dependency management
- 🧠 Reflection: Comprehensive migration completed with all command examples, installation instructions, and development workflows updated to use uv. The migration maintains consistency across all documentation while preserving performance comparison data that justifies the choice of uv over Poetry.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Documentation consistency check - PASS (all Poetry references replaced except intentional performance comparisons)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
