---
name: error-log-solver
description: Helps solve software errors using logs, stack traces, and runtime error messages. Identifies root causes, explains errors in simple terms, suggests fixes with reasoning, provides corrected code, highlights common pitfalls, and suggests debugging improvements.
---

# Error Log Solver

This skill helps analyze and solve software errors by examining logs, stack traces, and runtime error messages.

## When to Use This Skill

Use this skill when you encounter:
- Runtime error messages
- Stack traces from applications
- Error logs from servers or applications
- Build or compilation errors
- Database connection errors
- API or network errors
- Any software error that produces logs or error messages

## Core Process

When analyzing errors, follow this systematic approach:

### 1. Error Identification
- Extract the main error message
- Identify the error type (syntax, runtime, logical, etc.)
- Determine the component or module where the error occurred
- Note the error location (file, line number, function)

### 2. Root Cause Analysis
- Trace the error back to its source
- Identify the specific line or code block causing the issue
- Consider the context in which the error occurred
- Look for related dependencies or external factors

### 3. Simple Explanation
- Explain the error in plain English
- Describe what the code was trying to do when the error occurred
- Identify the underlying problem without technical jargon
- Relate the error to common programming concepts

### 4. Solution Suggestions
- Provide 1-3 practical solutions with clear reasoning
- Rank solutions by effectiveness and ease of implementation
- Explain why each solution works
- Consider both quick fixes and long-term improvements

### 5. Code Examples
- Provide corrected code when applicable
- Show before/after comparisons
- Highlight the specific changes needed
- Include relevant context around the fix

### 6. Common Pitfalls
- Identify similar errors that could occur
- Warn about related issues that might arise
- Suggest preventive measures
- Recommend best practices to avoid future errors

### 7. Debugging Improvements
- Suggest better logging strategies
- Recommend debugging techniques
- Propose monitoring improvements
- Advise on error handling enhancements

## Error Categories and Patterns

### Common Error Types

#### Null/Undefined Reference Errors
- **Example**: "Cannot read property 'x' of null"
- **Likely cause**: Object is null or undefined when accessed
- **Solution**: Add null checks or ensure proper initialization

#### Syntax Errors
- **Example**: "SyntaxError: Unexpected token"
- **Likely cause**: Missing brackets, semicolons, or incorrect syntax
- **Solution**: Check for missing or extra syntax elements

#### Type Errors
- **Example**: "TypeError: Cannot convert object to primitive value"
- **Likely cause**: Incorrect data type used in operation
- **Solution**: Verify data types and add type checking

#### Network/Connection Errors
- **Example**: "Connection refused" or "Timeout"
- **Likely cause**: Network issues, server down, or configuration problems
- **Solution**: Check network connectivity and server status

#### Database Errors
- **Example**: "SQL syntax error" or "Connection failed"
- **Likely cause**: Query issues or connection problems
- **Solution**: Verify query syntax and connection parameters

## Solution Quality Guidelines

### For Each Solution:
- Explain the reasoning behind the fix
- Describe the potential impact of the change
- Consider side effects and related implications
- Provide code examples when relevant
- Rank solutions by preference when multiple options exist

### Code Example Format:
```language
# Before (problematic code)
problematic_code_here

# After (fixed code)
fixed_code_here
```

### Error Explanation Format:
1. **Error Type**: [Type of error]
2. **Location**: [File and line if available]
3. **What Happened**: [Simple explanation of the issue]
4. **Why It Happened**: [Root cause analysis]
5. **How to Fix**: [Solution with reasoning]

## Common Debugging Strategies

### For Runtime Errors:
- Check variable values at the point of failure
- Verify input data types and values
- Look for null/undefined references
- Examine the call stack for context

### For Build/Compilation Errors:
- Check syntax and formatting
- Verify dependencies and imports
- Look for version conflicts
- Examine configuration files

### For Performance Issues:
- Identify bottlenecks in the code
- Check for memory leaks or resource issues
- Look for inefficient algorithms
- Consider database query optimization

## Communication Style

- Use clear, jargon-free language when explaining errors
- Provide actionable solutions rather than just identifying problems
- Include relevant code examples to illustrate fixes
- Acknowledge when multiple solutions exist and explain trade-offs
- Suggest preventive measures to avoid similar errors in the future