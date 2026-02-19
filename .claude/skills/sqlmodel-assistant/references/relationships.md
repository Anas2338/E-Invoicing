# Advanced SQLModel Relationships and Patterns

This reference covers advanced relationship patterns and techniques for SQLModel.

## Complex Relationship Scenarios

### Self-Referencing Models
```python
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None

    # Self-referencing relationships
    parent_id: Optional[int] = Field(default=None, foreign_key="category.id")
    parent: Optional["Category"] = Relationship(
        sa_relationship_kwargs={"remote_side": "Category.id"},
        back_populates="children"
    )
    children: List["Category"] = Relationship(back_populates="parent")

    # Relationship to products in this category
    products: List["Product"] = Relationship(back_populates="category")

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float

    # Foreign key to category
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    category: Optional[Category] = Relationship(back_populates="products")
```

### Polymorphic Associations
```python
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, Union, Literal
from pydantic import BaseModel

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # Generic foreign key approach
    taggable_type: str  # 'Article' or 'Image'
    taggable_id: int    # ID of the associated record

class Article(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    # Relationship to tags for this article
    tags: List[Tag] = Relationship()

class Image(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    alt_text: str
    # Relationship to tags for this image
    tags: List[Tag] = Relationship()
```

### Complex Many-to-Many with Payload
```python
from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime

class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str

    # Many-to-many relationship through enrollment
    courses: List["Course"] = Relationship(
        back_populates="students",
        link_model="Enrollment"
    )

class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    code: str

    # Many-to-many relationship through enrollment
    students: List[Student] = Relationship(
        back_populates="courses",
        link_model="Enrollment"
    )

class Enrollment(SQLModel, table=True):
    student_id: Optional[int] = Field(
        default=None, foreign_key="student.id", primary_key=True
    )
    course_id: Optional[int] = Field(
        default=None, foreign_key="course.id", primary_key=True
    )
    enrollment_date: datetime = Field(default_factory=datetime.utcnow)
    grade: Optional[str] = None
    # Additional fields specific to the enrollment relationship
    semester: str
    year: int
```

## Advanced Query Patterns

### Join Queries
```python
from sqlmodel import select, and_, or_
from typing import List

def get_heroes_with_teams(session) -> List[Hero]:
    """Get heroes with their teams using join"""
    statement = (
        select(Hero)
        .join(Team, isouter=True)  # Left outer join
        .where(Hero.age > 18)
    )
    return session.exec(statement).all()

def get_teams_with_heroes_count(session) -> List[dict]:
    """Get teams with count of heroes"""
    from sqlalchemy import func

    statement = (
        select(
            Team.name,
            func.count(Hero.id).label("hero_count")
        )
        .select_from(Team)
        .join(Hero, isouter=True)
        .group_by(Team.id)
    )
    results = session.exec(statement).all()
    return [{"name": row[0], "hero_count": row[1]} for row in results]

def complex_query_with_filters(session, team_name: str = None, min_age: int = None) -> List[Hero]:
    """Complex query with dynamic filters"""
    statement = select(Hero).join(Team, isouter=True)

    conditions = []
    if team_name:
        conditions.append(Team.name == team_name)
    if min_age is not None:
        conditions.append(Hero.age >= min_age)

    if conditions:
        statement = statement.where(and_(*conditions))

    return session.exec(statement).all()
```

### Subquery Patterns
```python
def get_heroes_on_most_powerful_team(session) -> List[Hero]:
    """Get heroes from the team with the highest average power level"""
    from sqlalchemy import func

    # Subquery to find the team with highest average age (as proxy for power)
    avg_age_subquery = (
        select(Team.id, func.avg(Hero.age).label("avg_age"))
        .join(Hero)
        .group_by(Team.id)
        .subquery()
    )

    # Find team with max average age
    max_avg_team = (
        select(avg_age_subquery.c.id)
        .order_by(avg_age_subquery.c.avg_age.desc())
        .limit(1)
    )

    # Get heroes from that team
    statement = select(Hero).where(Hero.team_id.in_(max_avg_team))
    return session.exec(statement).all()
```

## Performance Optimization Techniques

### Eager Loading Strategies
```python
from sqlalchemy.orm import selectinload, joinedload

def get_heroes_with_teams_eager(session) -> List[Hero]:
    """Get heroes with teams using eager loading to prevent N+1"""
    statement = select(Hero).options(selectinload(Hero.team))
    return session.exec(statement).all()

def get_teams_with_heroes_joined(session) -> List[Team]:
    """Get teams with heroes using joined load"""
    statement = select(Team).options(joinedload(Team.heroes))
    return session.exec(statement).all()

def complex_eager_loading(session) -> List[Team]:
    """Complex eager loading with multiple levels"""
    statement = (
        select(Team)
        .options(
            selectinload(Team.heroes).selectinload(Hero.items)
        )
    )
    return session.exec(statement).all()
```

### Batch Operations
```python
def create_multiple_heroes(session, heroes_data: List[dict]) -> List[Hero]:
    """Efficiently create multiple heroes in a single operation"""
    heroes = [Hero(**data) for data in heroes_data]

    for hero in heroes:
        session.add(hero)

    session.commit()

    # Refresh to get IDs
    for hero in heroes:
        session.refresh(hero)

    return heroes

def bulk_update_heroes(session, updates: List[dict]) -> int:
    """Bulk update multiple heroes"""
    from sqlalchemy import update

    updated_count = 0
    for update_data in updates:
        hero_id = update_data.pop('id')
        stmt = (
            update(Hero)
            .where(Hero.id == hero_id)
            .values(**update_data)
        )
        result = session.exec(stmt)
        updated_count += result.rowcount

    session.commit()
    return updated_count

def bulk_delete_heroes(session, hero_ids: List[int]) -> int:
    """Bulk delete multiple heroes"""
    from sqlalchemy import delete

    stmt = delete(Hero).where(Hero.id.in_(hero_ids))
    result = session.exec(stmt)
    session.commit()

    return result.rowcount
```

## Custom Constraints and Validation

### Model-Level Constraints
```python
from sqlmodel import SQLModel, Field, create_engine
from typing import Optional
from pydantic import validator, root_validator
from sqlalchemy import CheckConstraint, UniqueConstraint

class Hero(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("age > 0", name="positive_age_check"),
        CheckConstraint("power_level >= 0 AND power_level <= 100", name="valid_power_level_check"),
        UniqueConstraint("name", "secret_identity", name="unique_name_secret_combo"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=100)
    secret_identity: str = Field(min_length=1, max_length=100)
    age: int = Field(gt=0)
    power_level: float = Field(ge=0, le=100)

    @validator('name')
    def name_must_not_be_secret(cls, v):
        if v.lower() == 'secret':
            raise ValueError('Name cannot be "secret"')
        return v

    @root_validator
    def validate_power_level_based_on_age(cls, values):
        age = values.get('age')
        power_level = values.get('power_level')

        if age and power_level and age < 18 and power_level > 50:
            raise ValueError('Young heroes cannot have very high power levels')

        return values
```

### Custom Indexes
```python
from sqlalchemy import Index

class Article(SQLModel, table=True):
    __table_args__ = (
        # Composite index
        Index('idx_author_created', 'author_id', 'created_at'),
        # Partial index (where clause)
        Index('idx_published_articles', 'status', postgresql_where=Column('status') == 'published'),
        # Functional index
        Index('idx_title_lower', 'title', postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'}),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)  # Single column index
    content: str
    author_id: int = Field(index=True)  # Index for foreign key
    status: str = Field(default="draft", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

## Advanced Session Management

### Context Managers for Sessions
```python
from contextlib import contextmanager
from typing import Generator

@contextmanager
def get_db_session(engine) -> Generator[Session, None, None]:
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

def use_session_with_context(engine, hero_data: dict) -> Hero:
    """Use session with context manager"""
    with get_db_session(engine) as session:
        hero = Hero(**hero_data)
        session.add(hero)
        # Commit happens automatically in the context manager
        return hero
```

### Transaction Management
```python
from sqlalchemy.exc import IntegrityError

def transfer_hero_between_teams(session: Session, hero_id: int, new_team_id: int):
    """Transfer a hero between teams in a transaction"""
    try:
        hero = session.get(Hero, hero_id)
        if not hero:
            raise ValueError(f"Hero with ID {hero_id} not found")

        old_team_id = hero.team_id

        # Update hero's team
        hero.team_id = new_team_id
        session.add(hero)

        # Log the transfer (in the same transaction)
        transfer_log = TransferLog(
            hero_id=hero_id,
            from_team_id=old_team_id,
            to_team_id=new_team_id,
            transfer_date=datetime.utcnow()
        )
        session.add(transfer_log)

        session.commit()
        return hero

    except IntegrityError:
        session.rollback()
        raise ValueError("Transfer would violate database constraints")
    except Exception:
        session.rollback()
        raise

class TransferLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hero_id: int
    from_team_id: Optional[int]
    to_team_id: int
    transfer_date: datetime
```

## Complete Example: Blog Application
```python
from sqlmodel import SQLModel, Field, Relationship, create_engine, Session
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index

class User(SQLModel, table=True):
    __table_args__ = (
        Index('idx_user_email', 'email', unique=True),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, min_length=3, max_length=50)
    email: str = Field(index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    posts: List["Post"] = Relationship(back_populates="author")
    comments: List["Comment"] = Relationship(back_populates="author")

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    is_active: bool = Field(default=True)

    # Relationship
    posts: List["Post"] = Relationship(back_populates="category")

class Post(SQLModel, table=True):
    __table_args__ = (
        Index('idx_post_status_date', 'status', 'created_at'),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, max_length=200)
    content: str
    status: str = Field(default="draft", index=True)  # draft, published, archived
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Foreign keys
    author_id: int = Field(foreign_key="user.id", index=True)
    category_id: Optional[int] = Field(default=None, foreign_key="category.id", index=True)

    # Relationships
    author: User = Relationship(back_populates="posts")
    category: Optional[Category] = Relationship(back_populates="posts")
    comments: List["Comment"] = Relationship(back_populates="post")

class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_approved: bool = Field(default=False)

    # Foreign keys
    post_id: int = Field(foreign_key="post.id", index=True)
    author_id: int = Field(foreign_key="user.id", index=True)

    # Relationships
    post: Post = Relationship(back_populates="comments")
    author: User = Relationship(back_populates="comments")

# Engine setup
def setup_blog_database(database_url: str):
    engine = create_engine(database_url)
    SQLModel.metadata.create_all(engine)
    return engine

# Example usage
def create_sample_blog_data(engine):
    with Session(engine) as session:
        # Create a user
        user = User(username="johndoe", email="john@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # Create a category
        category = Category(name="Technology", description="Tech articles")
        session.add(category)
        session.commit()
        session.refresh(category)

        # Create a post
        post = Post(
            title="Introduction to SQLModel",
            content="SQLModel is a great ORM...",
            author_id=user.id,
            category_id=category.id,
            status="published"
        )
        session.add(post)
        session.commit()

        return post
```