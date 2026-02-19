# SQLModel Basic Template

This template provides a basic structure for implementing SQLModel models with common patterns.

## Basic Model Structure

```python
from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional
from datetime import datetime

# Define a basic model
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Create database and tables
sqlite_file = "database.db"
sqlite_url = f"sqlite:///{sqlite_file}"
engine = create_engine(sqlite_url)

# Create tables
from sqlmodel import SQLModel
SQLModel.metadata.create_all(engine)

# Basic CRUD operations
def create_user(db_session: Session, user: User) -> User:
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def get_user(db_session: Session, user_id: int) -> Optional[User]:
    return db_session.get(User, user_id)

def get_users(db_session: Session) -> list[User]:
    from sqlmodel import select
    statement = select(User)
    results = db_session.exec(statement)
    return results.all()

def update_user(db_session: Session, user_id: int, user_data: dict) -> Optional[User]:
    user = db_session.get(User, user_id)
    if user:
        for key, value in user_data.items():
            setattr(user, key, value)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user

def delete_user(db_session: Session, user_id: int) -> bool:
    user = db_session.get(User, user_id)
    if user:
        db_session.delete(user)
        db_session.commit()
        return True
    return False
```

## Model with Relationships

```python
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List

# Parent model
class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str

    # Relationship to child model
    heroes: List["Hero"] = Relationship(back_populates="team")

# Child model
class Hero(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: Optional[int] = Field(default=None)

    # Foreign key to parent
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")

    # Relationship back to parent
    team: Optional[Team] = Relationship(back_populates="heroes")
```

## Async Operations Template

```python
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from typing import Optional, List

# Async engine
async_engine = create_async_engine("sqlite+aiosqlite:///async.db")

async def create_user_async(session: AsyncSession, user: User) -> User:
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def get_user_async(session: AsyncSession, user_id: int) -> Optional[User]:
    return await session.get(User, user_id)

async def get_users_async(session: AsyncSession) -> List[User]:
    from sqlmodel import select
    statement = select(User)
    result = await session.exec(statement)
    return result.all()
```

## Advanced Field Types

```python
from sqlmodel import SQLModel, Field
from typing import Optional, List
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime, date
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, Date, Numeric

class AdvancedModel(SQLModel, table=True):
    # Auto-generated UUID primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Various field types
    name: str = Field(sa_type=String(100))
    description: str = Field(sa_type=Text)
    age: int
    salary: Decimal = Field(sa_type=Numeric(10, 2))
    birth_date: date
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Boolean field
    is_verified: bool = Field(default=False)

    # Large integer
    big_number: int = Field(sa_type=BigInteger)

    # Indexed field
    email: str = Field(index=True, sa_type=String(255))

    # Unique constraint
    username: str = Field(unique=True, sa_type=String(50))

    # Field with check constraint
    rating: float = Field(ge=0, le=10)  # Greater than or equal to 0, less than or equal to 10
```

## Validation Example

```python
from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import validator, root_validator

class ValidatedModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(regex=r'^[^@]+@[^@]+\.[^@]+$')  # Basic email validation
    age: int = Field(ge=0, le=150)  # Age between 0 and 150
    password: str = Field(min_length=8)  # Password at least 8 characters

    @validator('name')
    def name_must_not_be_admin(cls, v):
        if v.lower() == 'admin':
            raise ValueError('Name cannot be admin')
        return v

    @root_validator
    def validate_password_confirmation(cls, values):
        password = values.get('password')
        confirm_password = values.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise ValueError('Password and confirmation must match')

        return values
```

## Session Management Template

```python
from contextlib import contextmanager
from typing import Generator

@contextmanager
def get_session_context(engine) -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Usage example
def example_usage(engine):
    with get_session_context(engine) as session:
        # Perform database operations
        user = User(username="test", email="test@example.com")
        session.add(user)
        # Commit happens automatically in context manager
```