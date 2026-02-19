# SQLModel Performance Optimization

This reference covers strategies and best practices for optimizing SQLModel-based applications.

## Query Optimization

### Efficient Query Patterns
```python
from sqlmodel import select, func
from sqlalchemy import and_, or_
from typing import List

def get_heroes_with_teams_efficient(session) -> List[dict]:
    """Efficient query that selects only needed fields"""
    statement = select(
        Hero.id,
        Hero.name,
        Hero.secret_name,
        Team.name.label("team_name")
    ).join(Team, isouter=True)

    results = session.exec(statement).all()
    return [{"id": r.id, "name": r.name, "secret_name": r.secret_name, "team": r.team_name} for r in results]

def get_heroes_with_count(session) -> int:
    """Efficient count query without loading all records"""
    statement = select(func.count(Hero.id))
    return session.exec(statement).one()

def get_heroes_with_pagination(session, offset: int = 0, limit: int = 10) -> List[Hero]:
    """Efficient paginated query"""
    statement = select(Hero).offset(offset).limit(limit)
    return session.exec(statement).all()

def get_heroes_with_multiple_filters(session, name_pattern: str = None, min_age: int = None, team_id: int = None) -> List[Hero]:
    """Efficient query with dynamic filters"""
    statement = select(Hero)

    conditions = []
    if name_pattern:
        conditions.append(Hero.name.contains(name_pattern))
    if min_age is not None:
        conditions.append(Hero.age >= min_age)
    if team_id is not None:
        conditions.append(Hero.team_id == team_id)

    if conditions:
        statement = statement.where(and_(*conditions))

    return session.exec(statement).all()
```

### Subquery Optimization
```python
def get_heroes_from_top_teams(session, top_n: int = 5) -> List[Hero]:
    """Get heroes from teams with the most heroes"""
    from sqlalchemy import func

    # Subquery to find top teams
    top_teams_subq = (
        select(Team.id)
        .join(Hero)
        .group_by(Team.id)
        .order_by(func.count(Hero.id).desc())
        .limit(top_n)
        .subquery()
    )

    # Main query
    statement = select(Hero).where(Hero.team_id.in_(select(top_teams_subq.c.id)))
    return session.exec(statement).all()

def get_heroes_with_power_above_average(session) -> List[Hero]:
    """Get heroes with power level above average"""
    avg_power_subq = (
        select(func.avg(Hero.power_level)).where(Hero.power_level.is_not(None))
    ).scalar_subquery()

    statement = select(Hero).where(Hero.power_level > avg_power_subq)
    return session.exec(statement).all()
```

## Indexing Strategies

### Proper Index Usage
```python
from sqlmodel import SQLModel, Field
from sqlalchemy import Index
from typing import Optional

class OptimizedHero(SQLModel, table=True):
    __table_args__ = (
        # Composite index for common query patterns
        Index('idx_hero_team_age', 'team_id', 'age'),
        # Index for frequently searched fields
        Index('idx_hero_name', 'name'),
        # Partial index for active records
        Index('idx_active_heroes', 'id', postgresql_where=Hero.is_active.is_(True)),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # Single column index
    secret_name: str
    age: int = Field(index=True)
    power_level: float = Field(index=True)
    is_active: bool = Field(default=True, index=True)

    # Foreign key with index
    team_id: Optional[int] = Field(default=None, foreign_key="team.id", index=True)

class OptimizedPost(SQLModel, table=True):
    __table_args__ = (
        # Composite index for date-based queries
        Index('idx_post_status_date', 'status', 'created_at'),
        # Index for author queries
        Index('idx_post_author', 'author_id'),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    status: str = Field(default="draft", index=True)  # Query frequently by status
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Foreign key with index
    author_id: int = Field(foreign_key="user.id", index=True)
```

## Eager Loading and N+1 Prevention

### Relationship Loading Strategies
```python
from sqlalchemy.orm import selectinload, joinedload, lazyload

def get_heroes_with_teams_selectin(session) -> List[Hero]:
    """Use selectinload to prevent N+1 queries for collections"""
    statement = select(Hero).options(selectinload(Hero.team))
    return session.exec(statement).all()

def get_teams_with_heroes_joined(session) -> List[Team]:
    """Use joinedload for single relationships"""
    statement = select(Team).options(joinedload(Team.heroes))
    return session.exec(statement).all()

def get_complex_eager_loading(session) -> List[Team]:
    """Complex eager loading with multiple levels"""
    statement = (
        select(Team)
        .options(
            selectinload(Team.heroes)
            .selectinload(Hero.items)  # Assuming Hero has items relationship
        )
    )
    return session.exec(statement).all()

def get_heroes_without_eager_loading(session) -> List[Hero]:
    """Example of what NOT to do - will cause N+1"""
    heroes = session.exec(select(Hero)).all()
    # This will cause N+1 if you access hero.team for each hero
    return heroes

def get_heroes_with_teams_efficiently(session) -> List[dict]:
    """Better approach - get related data in one query"""
    statement = (
        select(Hero, Team)
        .join(Team, isouter=True)
        .options(lazyload('*'))  # Don't load other relationships
    )
    results = session.exec(statement).all()

    return [
        {
            "hero": {
                "id": hero.id,
                "name": hero.name,
                "secret_name": hero.secret_name
            },
            "team": {
                "id": team.id,
                "name": team.name
            } if team else None
        }
        for hero, team in results
    ]
```

## Batch Operations

### Bulk Operations
```python
def bulk_create_heroes(session, heroes_data: List[dict]) -> List[Hero]:
    """Efficiently create multiple heroes"""
    heroes = [Hero(**data) for data in heroes_data]

    # Add all at once
    for hero in heroes:
        session.add(hero)

    session.commit()

    # Refresh to get IDs
    for hero in heroes:
        session.refresh(hero)

    return heroes

def bulk_update_heroes(session, updates: List[dict]) -> int:
    """Bulk update heroes using raw SQL for better performance"""
    from sqlalchemy import update

    total_updated = 0
    for update_data in updates:
        hero_id = update_data.pop('id')
        stmt = update(Hero).where(Hero.id == hero_id).values(**update_data)
        result = session.exec(stmt)
        total_updated += result.rowcount

    session.commit()
    return total_updated

def bulk_delete_heroes(session, hero_ids: List[int]) -> int:
    """Bulk delete heroes"""
    from sqlalchemy import delete

    if not hero_ids:
        return 0

    stmt = delete(Hero).where(Hero.id.in_(hero_ids))
    result = session.exec(stmt)
    session.commit()

    return result.rowcount

def bulk_upsert_heroes(session, heroes_data: List[dict],
                      conflict_columns: List[str] = ['name']) -> int:
    """Bulk upsert (insert or update) heroes"""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    import sqlalchemy as sa

    # Get the appropriate insert function based on dialect
    dialect = session.bind.dialect.name
    if dialect == 'postgresql':
        stmt = pg_insert(Hero)
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_={k: sa.text(f'excluded.{k}') for k in heroes_data[0].keys() if k not in conflict_columns}
        )
    else:
        # For SQLite, implement merge logic manually
        updated_count = 0
        for hero_data in heroes_data:
            stmt = select(Hero).where(
                and_(*[getattr(Hero, col) == hero_data[col] for col in conflict_columns])
            )
            existing = session.exec(stmt).first()

            if existing:
                # Update existing
                for key, value in hero_data.items():
                    setattr(existing, key, value)
                session.add(existing)
                updated_count += 1
            else:
                # Create new
                hero = Hero(**hero_data)
                session.add(hero)

        session.commit()
        return updated_count

    # Execute the upsert
    session.exec(stmt, heroes_data)
    session.commit()
    return len(heroes_data)
```

## Connection Pooling and Session Management

### Optimized Session Usage
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from sqlmodel import Session
from contextlib import contextmanager
from typing import Generator

def create_optimized_engine(database_url: str):
    """Create an optimized database engine with proper pooling"""
    return create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=20,  # Number of connections to maintain
        max_overflow=30,  # Additional connections beyond pool_size
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set to True for debugging
        connect_args={
            "timeout": 30,  # Connection timeout
            "check_same_thread": False  # For SQLite
        }
    )

@contextmanager
def get_optimized_session(engine) -> Generator[Session, None, None]:
    """Context manager for optimized session usage"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def execute_batch_queries(engine, queries: List[str]):
    """Execute multiple queries efficiently"""
    with get_optimized_session(engine) as session:
        results = []
        for query in queries:
            result = session.exec(query)
            results.append(result)
        return results
```

## Async Performance Patterns

### Async Session Optimization
```python
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as SQLAlchemyAsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List

def create_optimized_async_engine(database_url: str):
    """Create an optimized async database engine"""
    return create_async_engine(
        database_url,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )

@asynccontextmanager
async def get_optimized_async_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for optimized session usage"""
    async with AsyncSession(engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_heroes_async_optimized(session: AsyncSession,
                                   limit: int = 100) -> List[Hero]:
    """Optimized async query"""
    statement = select(Hero).limit(limit)
    result = await session.exec(statement)
    return result.all()

async def get_multiple_entities_async(session: AsyncSession,
                                   hero_ids: List[int],
                                   team_ids: List[int]) -> tuple[List[Hero], List[Team]]:
    """Get multiple entity types efficiently in parallel"""
    import asyncio

    async def get_heroes_by_ids(ids: List[int]):
        stmt = select(Hero).where(Hero.id.in_(ids))
        result = await session.exec(stmt)
        return result.all()

    async def get_teams_by_ids(ids: List[int]):
        stmt = select(Team).where(Team.id.in_(ids))
        result = await session.exec(stmt)
        return result.all()

    heroes_task = get_heroes_by_ids(hero_ids)
    teams_task = get_teams_by_ids(team_ids)

    heroes, teams = await asyncio.gather(heroes_task, teams_task)
    return heroes, teams
```

## Caching Strategies

### Query Result Caching
```python
import functools
import time
from typing import Callable, Any
from hashlib import md5

def query_cache(expire_seconds: int = 300):
    """Decorator for caching query results"""
    def decorator(func: Callable) -> Callable:
        cache = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = md5(":".join(key_parts).encode()).hexdigest()

            # Check if result is in cache and not expired
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < expire_seconds:
                    return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result

        return wrapper
    return decorator

@query_cache(expire_seconds=60)  # Cache for 1 minute
def get_popular_heroes(session, limit: int = 10):
    """Get popular heroes with caching"""
    statement = (
        select(Hero)
        .order_by(Hero.popularity.desc())
        .limit(limit)
    )
    return session.exec(statement).all()
```

### Application-Level Caching
```python
from typing import Optional
import redis
import pickle
import json
from datetime import timedelta

class ApplicationCache:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
        except:
            return None
        return None

    def set(self, key: str, value: Any, expire: timedelta = timedelta(minutes=10)):
        """Set value in cache"""
        try:
            serialized = pickle.dumps(value)
            self.redis_client.setex(key, int(expire.total_seconds()), serialized)
            return True
        except:
            return False

    def get_or_set(self, key: str, getter_func: Callable,
                   expire: timedelta = timedelta(minutes=10)) -> Any:
        """Get from cache or set with result of getter function"""
        value = self.get(key)
        if value is not None:
            return value

        value = getter_func()
        self.set(key, value, expire)
        return value

# Usage example
cache = ApplicationCache()

def get_hero_with_cache(session, hero_id: int) -> Optional[Hero]:
    """Get hero with application-level caching"""
    cache_key = f"hero:{hero_id}"

    def fetch_hero():
        return session.get(Hero, hero_id)

    return cache.get_or_set(cache_key, fetch_hero, timedelta(minutes=5))
```

## Performance Monitoring

### Query Performance Tracking
```python
import time
import logging
from contextlib import contextmanager
from typing import Generator

class QueryProfiler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.slow_query_threshold = 1.0  # seconds

    @contextmanager
    def profile_query(self, operation_name: str = "query") -> Generator[None, None, None]:
        """Context manager to profile query execution time"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time

            if duration > self.slow_query_threshold:
                self.logger.warning(
                    f"SLOW QUERY: {operation_name} took {duration:.2f}s"
                )
            else:
                self.logger.debug(
                    f"Query {operation_name} took {duration:.2f}s"
                )

# Usage
profiler = QueryProfiler()

def get_heroes_with_profiling(session) -> List[Hero]:
    with profiler.profile_query("get_heroes"):
        statement = select(Hero)
        return session.exec(statement).all()
```

## Complete Performance-Optimized Example

```python
from sqlmodel import SQLModel, Field, create_engine, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from typing import Optional, List
import asyncio

class OptimizedHero(SQLModel, table=True):
    __table_args__ = (
        # Composite index for common queries
        Index('idx_hero_active_power', 'is_active', 'power_level'),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    secret_name: str
    age: int = Field(index=True)
    power_level: float = Field(index=True)
    is_active: bool = Field(default=True, index=True)
    popularity: int = Field(default=0, index=True)

class PerformanceOptimizedService:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.profiler = QueryProfiler()

    async def get_top_heroes(self, limit: int = 10) -> List[Hero]:
        """Get top heroes with optimized query"""
        async with AsyncSession(self.engine) as session:
            with self.profiler.profile_query("get_top_heroes"):
                statement = (
                    select(OptimizedHero)
                    .where(OptimizedHero.is_active == True)
                    .order_by(OptimizedHero.popularity.desc())
                    .limit(limit)
                )
                result = await session.exec(statement)
                return result.all()

    async def get_heroes_by_power_range(self, min_power: float, max_power: float) -> List[Hero]:
        """Get heroes within power range with optimized query"""
        async with AsyncSession(self.engine) as session:
            with self.profiler.profile_query("get_heroes_by_power_range"):
                statement = (
                    select(OptimizedHero)
                    .where(
                        OptimizedHero.is_active == True,
                        OptimizedHero.power_level >= min_power,
                        OptimizedHero.power_level <= max_power
                    )
                    .order_by(OptimizedHero.power_level.desc())
                )
                result = await session.exec(statement)
                return result.all()

    async def batch_create_heroes(self, heroes_data: List[dict]) -> List[Hero]:
        """Efficiently create multiple heroes in a batch"""
        async with AsyncSession(self.engine) as session:
            with self.profiler.profile_query("batch_create_heroes"):
                heroes = [OptimizedHero(**data) for data in heroes_data]

                for hero in heroes:
                    session.add(hero)

                await session.commit()

                # Refresh to get IDs
                for hero in heroes:
                    await session.refresh(hero)

                return heroes

    async def bulk_update_heroes(self, updates: List[dict]) -> int:
        """Bulk update heroes efficiently"""
        from sqlalchemy import update

        total_updated = 0
        async with AsyncSession(self.engine) as session:
            with self.profiler.profile_query("bulk_update_heroes"):
                for update_data in updates:
                    hero_id = update_data.pop('id')
                    stmt = update(OptimizedHero).where(
                        OptimizedHero.id == hero_id
                    ).values(**update_data)
                    result = await session.exec(stmt)
                    total_updated += result.rowcount

                await session.commit()

        return total_updated

    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

# Usage example
async def main():
    service = PerformanceOptimizedService("sqlite+aiosqlite:///optimized.db")

    try:
        # Create sample data
        heroes_data = [
            {"name": "Superman", "secret_name": "Clark Kent", "age": 30, "power_level": 100},
            {"name": "Batman", "secret_name": "Bruce Wayne", "age": 35, "power_level": 85},
            {"name": "Wonder Woman", "secret_name": "Diana Prince", "age": 28, "power_level": 95}
        ]

        created_heroes = await service.batch_create_heroes(heroes_data)
        print(f"Created {len(created_heroes)} heroes")

        # Get top heroes
        top_heroes = await service.get_top_heroes(5)
        print(f"Retrieved {len(top_heroes)} top heroes")

        # Update heroes in bulk
        updates = [
            {"id": created_heroes[0].id, "popularity": 1000},
            {"id": created_heroes[1].id, "popularity": 950}
        ]
        updated_count = await service.bulk_update_heroes(updates)
        print(f"Updated {updated_count} heroes")

    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())
```