# SQLModel Assistant Skill

This skill provides comprehensive guidance for designing and using SQLModel models to build robust, scalable database-backed applications.

## Overview

The SQLModel Assistant skill helps users:

1. Convert database schemas, data models, or feature descriptions into correct SQLModel classes and relationships
2. Generate proper table definitions, indexes, and constraints
3. Show how to perform CRUD operations using SQLModel and SQLAlchemy
4. Provide best practices for migrations, performance, and data integrity
5. Include examples for common patterns (relationships, joins, async sessions)
6. Warn when incorrect or deprecated SQLModel or SQLAlchemy usage is detected

## Files Structure

```
sqlmodel-assistant/
├── SKILL.md                    # Main skill definition and instructions
├── scripts/
│   └── generate_sqlmodel.py    # Helper script for SQLModel generation
├── references/
│   ├── relationships.md        # Advanced relationship patterns
│   ├── migrations.md           # Migration strategies and best practices
│   ├── performance.md          # Performance optimization techniques
│   └── async.md                # Async patterns and usage
├── assets/
│   └── basic-model-template.md # Basic SQLModel implementation template
├── package_skill.py           # Script to package the skill
└── README.md                  # This file
```

## Usage

This skill is designed to be used automatically by Claude when a user asks about SQLModel topics. The skill will trigger when Claude detects requests related to:

- Converting database schemas to SQLModel classes
- Designing proper table structures with relationships and constraints
- Implementing CRUD operations with SQLModel
- Following migration, performance, and data integrity best practices
- Working with relationships, joins, and async sessions
- Identifying and fixing incorrect SQLModel/SQLAlchemy usage

## Features

- **Model Generation**: Convert schema descriptions to SQLModel classes
- **Relationship Handling**: Proper relationship definitions and patterns
- **CRUD Operations**: Complete examples for create, read, update, delete
- **Migration Support**: Alembic integration and migration patterns
- **Performance Optimization**: Query optimization and indexing strategies
- **Async Support**: Async session management and patterns
- **Validation**: Best practice validation and deprecation warnings

## Best Practices Covered

1. **Model Design**: Proper use of Optional types, indexing, constraints, and validation
2. **Session Management**: Context managers, transaction handling, and session scope
3. **Performance**: Eager loading, batch operations, and query optimization
4. **Migrations**: Alembic setup, migration patterns, and deployment strategies
5. **Async Patterns**: Async session usage, concurrent operations, and error handling

## Contributing

This skill is designed to evolve with SQLModel. Contributions are welcome for:

- Additional model patterns and relationships
- Updated migration strategies
- New performance optimization techniques
- Improved async patterns
- Additional reference materials