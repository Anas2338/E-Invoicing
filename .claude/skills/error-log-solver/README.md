# Error Log Solver

This skill helps analyze and solve software errors by examining logs, stack traces, and runtime error messages.

## Purpose

The Error Log Solver skill helps Claude:
- Identify root causes of software errors
- Explain errors in simple, understandable terms
- Suggest practical solutions with clear reasoning
- Provide corrected code examples when applicable
- Highlight common pitfalls that cause similar errors
- Suggest debugging and logging improvements

## How It Works

This skill follows a systematic approach to error analysis:
1. Identifies the error type and location
2. Explains the error in simple terms
3. Analyzes the root cause
4. Suggests multiple solutions with reasoning
5. Provides code examples when relevant
6. Highlights potential pitfalls and improvements

## Key Features

1. **Systematic Error Analysis**: Follows a consistent process for error identification and resolution
2. **Multi-language Support**: Handles errors from various programming languages and frameworks
3. **Root Cause Focus**: Goes beyond symptoms to identify the underlying issue
4. **Practical Solutions**: Provides actionable solutions with clear reasoning
5. **Code Examples**: Includes before/after code comparisons when applicable
6. **Prevention Strategies**: Suggests ways to avoid similar errors in the future

## Usage

This skill is automatically triggered when error logs, stack traces, or runtime errors are provided. Claude will analyze the error and provide a comprehensive solution following the structured approach defined in this skill.

## Files Included

- `SKILL.md`: Main skill instructions and guidelines
- `references/error-patterns.md`: Common error patterns and solutions across languages
- `scripts/analyze-logs.py`: Script for automated error log analysis
- `assets/examples/`: Example error scenarios with detailed analysis