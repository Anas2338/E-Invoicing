# Next.js Documentation Assistant

This skill assists with writing Next.js applications using the latest official Next.js documentation and best practices.

## Purpose

The Next.js Documentation Assistant skill helps Claude:
- Write Next.js code following modern patterns (App Router, Server Components, etc.)
- Reference the latest Next.js documentation
- Avoid deprecated APIs and patterns
- Implement best practices for performance and security
- Generate code that follows TypeScript conventions

## How It Works

This skill activates automatically when Claude is working with Next.js code. It provides guidance on:
- File structure using the App Router
- Server vs Client Components
- Data fetching patterns
- Server Actions
- TypeScript integration
- Performance optimizations
- Security best practices

## Key Features

1. **Modern Next.js Patterns**: Emphasizes App Router, Server Components, and Server Actions
2. **Documentation Reference**: Contains comprehensive Next.js documentation
3. **Best Practices**: Includes current Next.js recommendations and patterns
4. **Template Assets**: Provides a Next.js project template with src directory structure
5. **TypeScript Support**: Focuses on TypeScript best practices with proper path aliases
6. **Deprecated API Warnings**: Helps avoid outdated patterns

## Usage

This skill is automatically triggered when working with Next.js code. Claude will reference the documentation and patterns provided in this skill to generate accurate, modern Next.js code.

## Files Included

- `SKILL.md`: Main skill instructions and guidelines
- `references/documentation.md`: Comprehensive Next.js documentation
- `scripts/update-docs.js`: Script to update documentation (template)
- `assets/`: Basic Next.js project template files