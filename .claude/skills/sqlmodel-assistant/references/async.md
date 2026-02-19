# SQLModel Async Patterns and Best Practices

This reference covers async patterns and best practices for using SQLModel in asynchronous applications.

## Async Session Management

### Basic Async Session Setup
```python
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as SQLAlchemyAsyncSession
from typing import AsyncGenerator
import asyncio

# Create async engine
async_engine = create_async_engine(
    "sqlite+aiosqlite:///async_example.db",
    echo=False  # Set to True for debugging
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session as a generator for dependency injection"""
    async with AsyncSession(async_engine) as session:
        yield session

# Context manager approach
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions"""
    async with AsyncSession(async_engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Async CRUD Operations
```python
from sqlmodel import select
from typing import List, Optional

async def create_hero_async(session: AsyncSession, hero: Hero) -> Hero:
    """Create a hero asynchronously"""
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    return hero

async def get_heroes_async(session: AsyncSession) -> List[Hero]:
    """Get all heroes asynchronously"""
    statement = select(Hero)
    result = await session.exec(statement)
    return result.all()

async def get_hero_by_id_async(session: AsyncSession, hero_id: int) -> Optional[Hero]:
    """Get a hero by ID asynchronously"""
    statement = select(Hero).where(Hero.id == hero_id)
    return await session.exec(statement).first()

async def update_hero_async(session: AsyncSession, hero_id: int, hero_data: dict) -> Optional[Hero]:
    """Update a hero asynchronously"""
    hero = await session.get(Hero, hero_id)
    if hero:
        for key, value in hero_data.items():
            setattr(hero, key, value)
        await session.add(hero)
        await session.commit()
        await session.refresh(hero)
    return hero

async def delete_hero_async(session: AsyncSession, hero_id: int) -> bool:
    """Delete a hero asynchronously"""
    hero = await session.get(Hero, hero_id)
    if hero:
        await session.delete(hero)
        await session.commit()
        return True
    return False
```

## Advanced Async Patterns

### Async Context Managers with Error Handling
```python
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

@asynccontextmanager
async def transactional_session() -> AsyncGenerator[AsyncSession, None]:
    """Async session with automatic transaction management"""
    async with AsyncSession(async_engine) as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logging.error(f"Transaction failed: {e}")
            raise
        finally:
            await session.close()

@asynccontextmanager
async def read_only_session() -> AsyncGenerator[AsyncSession, None]:
    """Async session for read-only operations"""
    async with AsyncSession(async_engine) as session:
        # Set session to read-only mode
        await session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        try:
            yield session
        finally:
            await session.close()
```

### Async Relationship Loading
```python
from sqlalchemy.orm import selectinload, joinedload

async def get_heroes_with_teams_async(session: AsyncSession) -> List[Hero]:
    """Get heroes with teams using async eager loading"""
    statement = select(Hero).options(selectinload(Hero.team))
    result = await session.exec(statement)
    return result.all()

async def get_teams_with_heroes_async(session: AsyncSession) -> List[Team]:
    """Get teams with heroes using async joined loading"""
    statement = select(Team).options(joinedload(Team.heroes))
    result = await session.exec(statement)
    return result.all()

async def get_complex_relationships_async(session: AsyncSession) -> List[Team]:
    """Get complex relationships with multiple levels"""
    statement = (
        select(Team)
        .options(
            selectinload(Team.heroes)
            .selectinload(Hero.items)  # Assuming Hero has items relationship
        )
    )
    result = await session.exec(statement)
    return result.all()
```

## Async Performance Optimization

### Concurrent Operations
```python
import asyncio
from typing import List, Tuple

async def get_multiple_heroes_async(session: AsyncSession, hero_ids: List[int]) -> List[Hero]:
    """Get multiple heroes concurrently"""
    async def get_single_hero(hero_id: int) -> Optional[Hero]:
        return await session.get(Hero, hero_id)

    # Create tasks for concurrent execution
    tasks = [get_single_hero(hero_id) for hero_id in hero_ids]
    heroes = await asyncio.gather(*tasks)
    return [h for h in heroes if h is not None]

async def get_heroes_and_teams_async(session: AsyncSession) -> Tuple[List[Hero], List[Team]]:
    """Get heroes and teams concurrently"""
    async def get_heroes():
        statement = select(Hero)
        result = await session.exec(statement)
        return result.all()

    async def get_teams():
        statement = select(Team)
        result = await session.exec(statement)
        return result.all()

    heroes, teams = await asyncio.gather(get_heroes(), get_teams())
    return heroes, teams

async def batch_create_heroes_async(session: AsyncSession, heroes_data: List[dict]) -> List[Hero]:
    """Efficiently create multiple heroes asynchronously"""
    heroes = [Hero(**data) for data in heroes_data]

    for hero in heroes:
        session.add(hero)

    await session.commit()

    # Refresh to get IDs
    for hero in heroes:
        await session.refresh(hero)

    return heroes
```

### Async Batch Operations
```python
async def bulk_update_heroes_async(session: AsyncSession, updates: List[dict]) -> int:
    """Bulk update heroes asynchronously"""
    from sqlalchemy import update

    total_updated = 0
    for update_data in updates:
        hero_id = update_data.pop('id')
        stmt = update(Hero).where(Hero.id == hero_id).values(**update_data)
        result = await session.exec(stmt)
        total_updated += result.rowcount

    await session.commit()
    return total_updated

async def bulk_delete_heroes_async(session: AsyncSession, hero_ids: List[int]) -> int:
    """Bulk delete heroes asynchronously"""
    from sqlalchemy import delete

    if not hero_ids:
        return 0

    stmt = delete(Hero).where(Hero.id.in_(hero_ids))
    result = await session.exec(stmt)
    await session.commit()

    return result.rowcount

async def bulk_upsert_heroes_async(session: AsyncSession, heroes_data: List[dict]) -> int:
    """Bulk upsert (insert or update) heroes asynchronously"""
    # For PostgreSQL
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    import sqlalchemy as sa

    try:
        stmt = pg_insert(Hero).values(heroes_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['name'],  # Assuming 'name' is a conflict column
            set_={k: sa.text(f'excluded.{k}') for k in heroes_data[0].keys() if k != 'name'}
        )
        await session.exec(stmt)
        await session.commit()
        return len(heroes_data)
    except Exception:
        # Fallback to individual operations for other databases
        upserted_count = 0
        for hero_data in heroes_data:
            existing = await session.exec(
                select(Hero).where(Hero.name == hero_data['name'])
            ).first()

            if existing:
                # Update existing
                for key, value in hero_data.items():
                    setattr(existing, key, value)
                session.add(existing)
            else:
                # Create new
                hero = Hero(**hero_data)
                session.add(hero)

            upserted_count += 1

        await session.commit()
        return upserted_count
```

## Async with FastAPI Integration

### FastAPI Dependency
```python
from fastapi import Depends, FastAPI
from typing import AsyncGenerator

app = FastAPI()

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(async_engine) as session:
        try:
            yield session
        finally:
            await session.close()

# Example FastAPI routes
@app.post("/heroes/", response_model=Hero)
async def create_hero_endpoint(hero: Hero, session: AsyncSession = Depends(get_session)):
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    return hero

@app.get("/heroes/", response_model=List[Hero])
async def get_heroes_endpoint(session: AsyncSession = Depends(get_session)):
    statement = select(Hero)
    result = await session.exec(statement)
    return result.all()

@app.get("/heroes/{hero_id}", response_model=Hero)
async def get_hero_endpoint(hero_id: int, session: AsyncSession = Depends(get_session)):
    hero = await session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero
```

### Async Service Layer
```python
from fastapi import HTTPException
from typing import List, Optional

class AsyncHeroService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_hero(self, hero_data: dict) -> Hero:
        hero = Hero(**hero_data)
        self.session.add(hero)
        await self.session.commit()
        await self.session.refresh(hero)
        return hero

    async def get_hero_by_id(self, hero_id: int) -> Optional[Hero]:
        hero = await self.session.get(Hero, hero_id)
        return hero

    async def get_heroes(self, skip: int = 0, limit: int = 100) -> List[Hero]:
        statement = select(Hero).offset(skip).limit(limit)
        result = await self.session.exec(statement)
        return result.all()

    async def update_hero(self, hero_id: int, hero_data: dict) -> Optional[Hero]:
        hero = await self.session.get(Hero, hero_id)
        if not hero:
            return None

        for key, value in hero_data.items():
            setattr(hero, key, value)

        self.session.add(hero)
        await self.session.commit()
        await self.session.refresh(hero)
        return hero

    async def delete_hero(self, hero_id: int) -> bool:
        hero = await self.session.get(Hero, hero_id)
        if not hero:
            return False

        await self.session.delete(hero)
        await self.session.commit()
        return True

# Usage in FastAPI
@app.post("/heroes/", response_model=Hero)
async def create_hero_endpoint(
    hero_data: dict,
    session: AsyncSession = Depends(get_session)
):
    service = AsyncHeroService(session)
    return await service.create_hero(hero_data)

@app.get("/heroes/{hero_id}", response_model=Hero)
async def get_hero_endpoint(
    hero_id: int,
    session: AsyncSession = Depends(get_session)
):
    service = AsyncHeroService(session)
    hero = await service.get_hero_by_id(hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero
```

## Async Streaming and Pagination

### Async Pagination
```python
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

async def get_paginated_heroes_async(
    session: AsyncSession,
    page: int = 1,
    size: int = 10
) -> PaginatedResponse[Hero]:
    """Get paginated heroes asynchronously"""
    offset = (page - 1) * size

    # Get total count
    count_statement = select(func.count(Hero.id))
    total = await session.exec(count_statement).one()

    # Get paginated results
    statement = select(Hero).offset(offset).limit(size)
    items = await session.exec(statement).all()

    pages = (total + size - 1) // size  # Ceiling division

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )
```

### Async Streaming Results
```python
from typing import AsyncIterator

async def stream_heroes_async(session: AsyncSession, batch_size: int = 100) -> AsyncIterator[Hero]:
    """Stream heroes asynchronously in batches"""
    offset = 0
    while True:
        statement = select(Hero).offset(offset).limit(batch_size)
        batch = await session.exec(statement).all()

        if not batch:
            break

        for hero in batch:
            yield hero

        offset += batch_size

async def process_all_heroes_async(session: AsyncSession):
    """Process all heroes asynchronously with streaming"""
    async for hero in stream_heroes_async(session):
        # Process each hero
        print(f"Processing hero: {hero.name}")
        # Perform async operations on the hero
        await update_hero_power_level(session, hero.id)
```

## Async Error Handling and Retry Logic

### Async Error Handling
```python
import asyncio
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import Optional, Callable, Any

async def execute_with_retry_async(
    func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
) -> Any:
    """Execute async function with retry logic"""
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except (OperationalError, IntegrityError) as e:
            last_exception = e
            if attempt >= max_retries:
                break

            await asyncio.sleep(delay * (backoff ** attempt))

    raise last_exception

async def safe_create_hero_async(session: AsyncSession, hero: Hero) -> Optional[Hero]:
    """Create hero with retry logic for transient errors"""
    async def _create():
        session.add(hero)
        await session.commit()
        await session.refresh(hero)
        return hero

    try:
        return await execute_with_retry_async(_create)
    except Exception as e:
        await session.rollback()
        raise e
```

### Async Transaction Management
```python
from typing import Callable, Any

async def run_in_transaction_async(
    session: AsyncSession,
    operation: Callable[[AsyncSession], Any]
) -> Any:
    """Run an operation in a transaction with proper error handling"""
    try:
        result = await operation(session)
        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise

async def transfer_hero_async(
    session: AsyncSession,
    hero_id: int,
    new_team_id: int
) -> Hero:
    """Transfer hero between teams in a transaction"""
    async def _transfer(session: AsyncSession):
        hero = await session.get(Hero, hero_id)
        if not hero:
            raise ValueError(f"Hero with ID {hero_id} not found")

        old_team_id = hero.team_id
        hero.team_id = new_team_id

        # Log the transfer
        transfer_log = TransferLog(
            hero_id=hero_id,
            from_team_id=old_team_id,
            to_team_id=new_team_id
        )
        session.add(transfer_log)

        await session.refresh(hero)
        return hero

    return await run_in_transaction_async(session, _transfer)

class TransferLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hero_id: int
    from_team_id: Optional[int]
    to_team_id: int
    transfer_date: datetime = Field(default_factory=datetime.utcnow)
```

## Complete Async Example

```python
from sqlmodel import SQLModel, Field, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from typing import Optional, List
import asyncio
import logging

class AsyncHero(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: Optional[int] = Field(default=None)
    power_level: float = Field(default=50.0)

class AsyncTeam(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str

    # Foreign key to Hero
    hero_id: Optional[int] = Field(default=None, foreign_key="asyncteam.id")

class AsyncHeroService:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True
        )
        self.logger = logging.getLogger(__name__)

    async def init_db(self):
        """Initialize the database with tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def create_hero(self, hero_data: dict) -> AsyncHero:
        """Create a hero asynchronously"""
        async with AsyncSession(self.engine) as session:
            hero = AsyncHero(**hero_data)
            session.add(hero)
            await session.commit()
            await session.refresh(hero)
            return hero

    async def get_heroes(self, limit: int = 100) -> List[AsyncHero]:
        """Get heroes asynchronously"""
        async with AsyncSession(self.engine) as session:
            statement = select(AsyncHero).limit(limit)
            result = await session.exec(statement)
            return result.all()

    async def get_hero_by_name(self, name: str) -> Optional[AsyncHero]:
        """Get hero by name asynchronously"""
        async with AsyncSession(self.engine) as session:
            statement = select(AsyncHero).where(AsyncHero.name == name)
            return await session.exec(statement).first()

    async def update_hero_power(self, hero_id: int, new_power: float) -> Optional[AsyncHero]:
        """Update hero power level asynchronously"""
        async with AsyncSession(self.engine) as session:
            hero = await session.get(AsyncHero, hero_id)
            if hero:
                hero.power_level = new_power
                await session.add(hero)
                await session.commit()
                await session.refresh(hero)
            return hero

    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

async def main():
    """Example usage of async SQLModel service"""
    service = AsyncHeroService("sqlite+aiosqlite:///async_example.db")

    try:
        # Initialize database
        await service.init_db()

        # Create heroes concurrently
        heroes_data = [
            {"name": "Superman", "secret_name": "Clark Kent", "age": 30, "power_level": 100},
            {"name": "Batman", "secret_name": "Bruce Wayne", "age": 35, "power_level": 90},
            {"name": "Wonder Woman", "secret_name": "Diana Prince", "age": 28, "power_level": 95}
        ]

        created_heroes = []
        for hero_data in heroes_data:
            hero = await service.create_hero(hero_data)
            created_heroes.append(hero)
            print(f"Created hero: {hero.name}")

        # Get all heroes
        heroes = await service.get_heroes()
        print(f"Retrieved {len(heroes)} heroes")

        # Update a hero's power
        if created_heroes:
            updated_hero = await service.update_hero_power(created_heroes[0].id, 105.0)
            print(f"Updated hero power: {updated_hero.name} - {updated_hero.power_level}")

        # Find a specific hero
        batman = await service.get_hero_by_name("Batman")
        if batman:
            print(f"Found Batman: {batman.secret_name}")

    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())
```