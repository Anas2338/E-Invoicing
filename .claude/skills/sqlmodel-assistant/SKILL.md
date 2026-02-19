---
name: sqlmodel-assistant
description: Helps design and use SQLModel models for building database-backed applications. Converts database schemas, data models, or feature descriptions into correct SQLModel classes and relationships, generates proper table definitions, indexes, and constraints, shows how to perform CRUD operations using SQLModel and SQLAlchemy, provides best practices for migrations, performance, and data integrity, includes examples for common patterns (relationships, joins, async sessions), and warns when incorrect or deprecated SQLModel or SQLAlchemy usage is detected.
---

# SQLModel Assistant Skill

This skill provides comprehensive guidance for designing and using SQLModel models to build robust, scalable database-backed applications.

## When to Use This Skill

Use this skill when you need to:
- Convert database schemas, data models, or feature descriptions into SQLModel classes
- Design proper table structures with relationships, indexes, and constraints
- Implement CRUD operations using SQLModel and SQLAlchemy
- Follow best practices for migrations, performance, and data integrity
- Work with common patterns (relationships, joins, async sessions)
- Identify and fix incorrect or deprecated SQLModel/SQLAlchemy usage

## Core Components of SQLModel

### 1. Model Definition
- **SQLModel Base**: Inherits from `SQLModel` and `Base`
- **Field Types**: Proper use of `Field`, `Relationship`, and column types
- **Constraints**: Primary keys, foreign keys, unique constraints, indexes
- **Validation**: Pydantic-style validation with SQLModel

### 2. Relationships
- **One-to-Many**: Parent-child relationships using `Relationship`
- **Many-to-Many**: Junction tables with proper relationship definitions
- **One-to-One**: Direct foreign key relationships
- **Self-Referencing**: Models that reference themselves

### 3. Session Management
- **Sync Sessions**: Traditional synchronous database sessions
- **Async Sessions**: Asynchronous database sessions for async applications
- **Session Context Managers**: Proper resource management
- **Transaction Handling**: Atomic operations and error handling

## Basic SQLModel Pattern

```python
from sqlmodel import SQLModel, Field, Relationship, create_engine, Session
from typing import Optional, List
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint

# Define a model with relationships
class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=50)
    headquarters: str

    # Relationship to Hero model
    heroes: List["Hero"] = Relationship(back_populates="team")

class Hero(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: Optional[int] = Field(default=None)

    # Foreign key to Team
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")

    # Relationship back to Team
    team: Optional[Team] = Relationship(back_populates="heroes")

# Create engine and tables
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

# Create tables
SQLModel.metadata.create_all(engine)
```

## CRUD Operations Pattern

```python
from sqlmodel import select

# CREATE - Add new records
def create_hero(session: Session, hero: Hero) -> Hero:
    session.add(hero)
    session.commit()
    session.refresh(hero)
    return hero

# READ - Query records
def get_heroes(session: Session) -> List[Hero]:
    statement = select(Hero)
    result = session.exec(statement)
    return result.all()

def get_hero_by_name(session: Session, name: str) -> Optional[Hero]:
    statement = select(Hero).where(Hero.name == name)
    return session.exec(statement).first()

# UPDATE - Modify records
def update_hero(session: Session, hero_id: int, hero_data: dict) -> Optional[Hero]:
    hero = session.get(Hero, hero_id)
    if hero:
        for key, value in hero_data.items():
            setattr(hero, key, value)
        session.add(hero)
        session.commit()
        session.refresh(hero)
    return hero

# DELETE - Remove records
def delete_hero(session: Session, hero_id: int) -> bool:
    hero = session.get(Hero, hero_id)
    if hero:
        session.delete(hero)
        session.commit()
        return True
    return False
```

## Best Practices

### 1. Model Design
- **Use Optional for nullable fields**: Always use `Optional[type]` for nullable columns
- **Index frequently queried fields**: Add `index=True` to fields used in WHERE clauses
- **Define proper constraints**: Use `unique=True`, `nullable=False`, and custom constraints
- **Leverage Pydantic validation**: Use field validators and custom validation

### 2. Session Management
- **Use context managers**: Wrap sessions in `with` statements
- **Handle transactions properly**: Use try-catch blocks for transaction management
- **Minimize session scope**: Keep sessions as short-lived as possible
- **Choose appropriate session type**: Sync for traditional apps, Async for async apps

### 3. Performance Optimization
- **Use eager loading**: Prevent N+1 queries with proper relationship loading
- **Batch operations**: Use bulk operations for multiple records
- **Optimize queries**: Use specific SELECT fields instead of `SELECT *`
- **Index optimization**: Create proper indexes for query performance

## Common Patterns

### 1. Many-to-Many Relationship Pattern
```python
from sqlmodel import SQLModel, Field, Relationship
from typing import List

# Association table for many-to-many relationship
class HeroTeamLink(SQLModel, table=True):
    team_id: Optional[int] = Field(default=None, foreign_key="team.id", primary_key=True)
    hero_id: Optional[int] = Field(default=None, foreign_key="hero.id", primary_key=True)
    is_training: bool = False

# Models with many-to-many relationship
class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    headquarters: str

    # Many-to-many relationship
    heroes: List["Hero"] = Relationship(
        back_populates="teams",
        link_model=HeroTeamLink
    )

class Hero(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    secret_name: str

    # Many-to-many relationship
    teams: List[Team] = Relationship(
        back_populates="heroes",
        link_model=HeroTeamLink
    )
```

### 2. Async Session Pattern
```python
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from typing import AsyncGenerator

# Create async engine
async_sqlite_url = "sqlite+aiosqlite:///async_database.db"
async_engine = create_async_engine(async_sqlite_url)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(async_engine) as session:
        yield session

# Async CRUD operations
async def create_hero_async(session: AsyncSession, hero: Hero) -> Hero:
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    return hero

async def get_heroes_async(session: AsyncSession) -> List[Hero]:
    statement = select(Hero)
    result = await session.exec(statement)
    return result.all()
```

### 3. Migration Pattern
```python
from alembic.config import Config
from alembic import command
from sqlmodel import SQLModel

# Alembic configuration for SQLModel
def run_migrations():
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")

    # Generate migration
    command.revision(alembic_cfg, autogenerate=True, message="Auto-generated migration")

    # Apply migration
    command.upgrade(alembic_cfg, "head")

# Alternative: Use SQLModel's metadata for simple cases
def create_tables(engine):
    """Create all tables defined in SQLModel models"""
    SQLModel.metadata.create_all(engine)
```

## Warning: Deprecated or Incorrect Usage

### Common Mistakes to Avoid
1. **Incorrect relationship definition**: Don't forget `back_populates` in bidirectional relationships
2. **Missing Optional types**: Always use `Optional[type]` for nullable fields
3. **Improper session management**: Don't forget to commit transactions
4. **N+1 query problems**: Don't access related objects in loops without proper loading
5. **Unsafe raw SQL**: Always use parameterized queries

### Correct vs Incorrect Patterns
```python
# ❌ INCORRECT: Missing Optional type for nullable field
class Hero(SQLModel, table=True):
    id: int = Field(primary_key=True)  # Should be Optional[int]
    name: str
    age: int = Field(default=None)  # Should be Optional[int]

# ✅ CORRECT: Proper use of Optional types
class Hero(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    age: Optional[int] = Field(default=None)
```

## Complete Implementation Example

For a complete implementation with all best practices, see the references below.

## When to Consult References

- **Advanced Relationship Patterns**: See `references/relationships.md`
- **Migration Strategies**: See `references/migrations.md`
- **Performance Optimization**: See `references/performance.md`
- **Async Patterns**: See `references/async.md`
- **Security Best Practices**: See `references/security.md`