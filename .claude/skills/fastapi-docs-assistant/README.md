# FastAPI Documentation Assistant

This skill assists with writing FastAPI applications using the latest official FastAPI documentation and best practices.

## Purpose

The FastAPI Documentation Assistant skill helps Claude:
- Write FastAPI code following modern patterns (async-first, Pydantic v2, etc.)
- Reference the latest FastAPI documentation
- Avoid deprecated APIs and patterns
- Implement best practices for performance and security
- Generate code that follows current FastAPI conventions

## How It Works

This skill activates automatically when Claude is working with FastAPI code. It provides guidance on:
- Application structure using async/await
- Pydantic v2 models and validation
- Dependency injection patterns
- Router organization
- Security best practices
- Error handling
- Database integration

## Key Features

1. **Modern FastAPI Patterns**: Emphasizes async-first design, Pydantic v2, and dependency injection
2. **Documentation Reference**: Contains comprehensive FastAPI documentation
3. **Best Practices**: Includes current FastAPI recommendations and patterns
4. **Template Assets**: Provides a basic FastAPI project template
5. **Type Safety**: Focuses on proper typing with Pydantic models
6. **Deprecated API Warnings**: Helps avoid outdated patterns

## Usage

This skill is automatically triggered when working with FastAPI code. Claude will reference the documentation and patterns provided in this skill to generate accurate, modern FastAPI code.

## Files Included

- `SKILL.md`: Main skill instructions and guidelines
- `references/documentation.md`: Comprehensive FastAPI documentation
- `scripts/update-docs.py`: Script to update documentation (template)
- `assets/`: Basic FastAPI project template files with src directory structure