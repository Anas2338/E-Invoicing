---
name: fastapi-docs-assistant
description: Assists with writing FastAPI applications using the latest official FastAPI documentation. Activates automatically when writing or modifying FastAPI code, provides accurate API usage, best practices (async-first, Pydantic v2, dependency injection), and avoids deprecated APIs.
---

# FastAPI Documentation Assistant

This skill provides guidance for developing FastAPI applications using the latest official FastAPI documentation and best practices.

## When to Use This Skill

Use this skill when working with FastAPI code, including:
- Creating new FastAPI applications or features
- Modifying existing FastAPI code
- Implementing API endpoints with proper async design
- Setting up Pydantic models and validation
- Configuring dependency injection
- Adding middleware and lifespan events
- Updating deprecated FastAPI patterns

## Core Guidelines

### 1. Async-First Design

Always prefer async functions for I/O-bound operations:
- Use `async def` for endpoint functions that perform I/O
- Use `await` for database queries, HTTP requests, and file operations
- Use `asyncio` for concurrent operations
- Avoid blocking operations in async endpoints

```python
# Good: Async endpoint
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await database.fetch_user(user_id)
    return user

# Avoid: Synchronous endpoint for I/O operations
@app.get("/users/{user_id}")
def get_user(user_id: int):  # Avoid sync for I/O
    user = database.fetch_user(user_id)  # Blocking operation
    return user
```

### 2. Pydantic v2 Models

Use Pydantic v2 for data validation and serialization:
- Define request/response models using Pydantic v2 syntax
- Use `model_config` instead of `Config` class
- Use `@computed_field` for computed properties
- Leverage field validation with `Field` constraints

```python
from pydantic import BaseModel, Field, computed_field
from typing import Optional

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: Optional[int] = Field(None, ge=0, le=150)

class UserResponse(UserCreate):
    id: int

    @computed_field
    @property
    def is_adult(self) -> bool:
        return self.age is not None and self.age >= 18
```

### 3. Dependency Injection

Use FastAPI's dependency injection system:
- Create reusable dependencies with `Depends()`
- Use class-based or function-based dependencies
- Implement security dependencies for authentication/authorization
- Use `Security()` for advanced security schemes

```python
from fastapi import Depends, HTTPException, status
from typing import Annotated

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user(username)
    if user is None:
        raise credentials_exception
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]

@app.get("/users/me")
async def read_users_me(current_user: CurrentUser):
    return current_user
```

### 4. Routers and Application Structure

Organize endpoints using APIRouter:
- Group related endpoints in separate routers
- Use consistent prefix and tags
- Include proper documentation for each endpoint
- Handle error responses appropriately

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "User not found"}}
)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """Get a user by ID."""
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    """Create a new user."""
    created_user = await create_new_user(user)
    return created_user

app.include_router(router)
```

### 5. Middleware and Lifespan Events

Implement middleware and lifespan events properly:
- Use middleware for cross-cutting concerns (logging, authentication)
- Implement lifespan events for startup/shutdown tasks
- Handle resource cleanup in lifespan events

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    yield
    # Shutdown
    await close_database()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 6. Error Handling

Use proper error handling with HTTPException:
- Raise HTTPException for client errors
- Use custom exception handlers when needed
- Provide meaningful error messages
- Follow HTTP status code conventions

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

@app.exception_handler(UserNotFoundException)
async def user_not_found_handler(request: Request, exc: UserNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"message": "User not found", "user_id": exc.user_id}
    )

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await fetch_user(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )
    return user
```

## Avoiding Deprecated Patterns

### Do Not Use:
- Synchronous endpoints for I/O operations
- Pydantic v1 syntax in new code
- Manual JSON serialization/deserialization
- Global application state without proper dependency injection
- Outdated FastAPI features (if any have been deprecated)

### Instead Use:
- Async/await for I/O operations
- Pydantic v2 models and validation
- FastAPI's built-in JSON handling
- Dependency injection system
- Current FastAPI best practices

## Security Best Practices

- Use OAuth2 with Password flow or JWT tokens for authentication
- Validate and sanitize all input data
- Implement rate limiting for public endpoints
- Use HTTPS in production
- Never expose sensitive information in error messages
- Use environment variables for secrets

## Performance Considerations

- Use async functions for I/O-bound operations
- Implement proper database connection pooling
- Use caching for expensive operations
- Implement pagination for list endpoints
- Use background tasks for non-critical operations

```python
from fastapi import BackgroundTasks

def send_notification_email(email: str, message: str):
    # Simulate sending email
    time.sleep(5)  # This would be an async operation in real code
    print(f"Email sent to {email}: {message}")

@app.post("/send-notification")
async def send_notification(
    email: str,
    message: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(send_notification_email, email, message)
    return {"message": "Notification scheduled"}
```

## Common Patterns and Examples

### Complete API with Dependencies

```python
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import asyncpg

class Item(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=200)
    price: float = Field(..., gt=0)

class ItemResponse(Item):
    id: int

# Dependency
async def get_db_connection():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

@app.post("/items/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item: Item,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    query = "INSERT INTO items(name, description, price) VALUES($1, $2, $3) RETURNING id"
    item_id = await conn.fetchval(query, item.name, item.description, item.price)
    return ItemResponse(id=item_id, **item.model_dump())

@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    query = "SELECT id, name, description, price FROM items WHERE id = $1"
    row = await conn.fetchrow(query, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse(**dict(row))
```