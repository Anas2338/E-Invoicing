# FastAPI Documentation Reference

This file contains detailed information about FastAPI patterns, APIs, and best practices that should be referenced when working with FastAPI code.

## Application Setup

### Basic Application
```python
from fastapi import FastAPI

app = FastAPI(
    title="My API",
    description="This is my API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

### Application with Lifespan
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    # Initialize resources (database connections, etc.)
    yield
    # Shutdown
    print("Shutting down...")
    # Clean up resources

app = FastAPI(lifespan=lifespan)
```

## Path Operations

### HTTP Methods
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items")          # GET
@app.post("/items")         # POST
@app.put("/items/{id}")     # PUT
@app.delete("/items/{id}")  # DELETE
@app.patch("/items/{id}")   # PATCH
@app.options("/items")      # OPTIONS
@app.head("/items")         # HEAD
@app.trace("/items")        # TRACE
```

### Path Parameters
```python
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

# Multiple path parameters
@app.get("/users/{user_id}/items/{item_id}")
async def read_user_item(user_id: int, item_id: str):
    return {"user_id": user_id, "item_id": item_id}

# Path parameters with valid values
from enum import Enum

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    if model_name == ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}
    return {"model_name": model_name, "message": "LeCNN all the way"}
```

### Query Parameters
```python
from typing import Union

@app.get("/items/")
async def read_items(
    item_id: Union[int, None] = None,
    q: Union[str, None] = None,
    skip: int = 0,
    limit: int = 100
):
    return {"item_id": item_id, "q": q, "skip": skip, "limit": limit}

# Query parameters with validation
from typing import Union
from fastapi import Query

@app.get("/items/")
async def read_items(
    q: Union[str, None] = Query(
        default=None,
        min_length=3,
        max_length=50,
        pattern="^fixedquery$"
    )
):
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results
```

### Request Body
```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: Union[str, None] = None
    price: float
    tax: Union[float, None] = None

@app.post("/items/")
async def create_item(item: Item):
    return item

# Multiple parameters (path, query, body)
@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item, q: Union[str, None] = None):
    result = {"item_id": item_id, **item.model_dump()}
    if q:
        result.update({"q": q})
    return result
```

## Pydantic Models

### Basic Models
```python
from pydantic import BaseModel, Field
from typing import Union

class Item(BaseModel):
    name: str
    description: Union[str, None] = Field(default=None, title="Description")
    price: float = Field(gt=0, description="Price must be greater than zero")
    tax: Union[float, None] = None

class User(BaseModel):
    username: str
    full_name: Union[str, None] = None
```

### Nested Models
```python
class User(BaseModel):
    username: str
    email: Union[str, None] = None

class Item(BaseModel):
    name: str
    description: Union[str, None] = None
    owner: User

@app.post("/items/", response_model=Item)
async def create_item_with_owner(item: Item):
    return item
```

### Model Config and Validation
```python
from pydantic import BaseModel, Field, validator, ConfigDict

class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Forbid extra fields

    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    description: Union[str, None] = None

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty or just spaces')
        return v
```

## Response Models

### Response Model Declaration
```python
from fastapi import FastAPI
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: Union[str, None] = None
    price: float
    tax: Union[float, None] = None

class ItemResponse(BaseModel):
    name: str
    description: Union[str, None] = None
    price: float
    # tax is excluded from response

@app.post("/items/", response_model=ItemResponse)
async def create_item(item: Item) -> ItemResponse:
    return item  # FastAPI will filter based on response_model
```

### Response Model with Attributes
```python
class UserIn(BaseModel):
    username: str
    password: str
    email: str

class UserOut(BaseModel):
    username: str
    email: str
    # password is excluded from response

@app.post("/user/", response_model=UserOut)
async def create_user(user: UserIn) -> UserOut:
    return user
```

## Dependencies

### Simple Dependencies
```python
from fastapi import Depends

async def common_parameters(q: Union[str, None] = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    return commons

@app.get("/users/")
async def read_users(commons: dict = Depends(common_parameters)):
    return commons
```

### Class Dependencies
```python
class CommonQueryParams:
    def __init__(self, q: Union[str, None] = None, skip: int = 0, limit: int = 100):
        self.q = q
        self.skip = skip
        self.limit = limit

@app.get("/items/")
async def read_items(commons: CommonQueryParams = Depends(CommonQueryParams)):
    return commons
```

### Sub-dependencies
```python
from fastapi import Header, HTTPException

async def verify_token(x_token: str = Header(...)):
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")
    return x_token

async def verify_key(x_key: str = Header(...)):
    if x_key != "fake-super-secret-key":
        raise HTTPException(status_code=400, detail="X-Key header invalid")
    return x_key

@app.get("/items/")
async def read_items(token: str = Depends(verify_token), key: str = Depends(verify_key)):
    return [{"item": "Foo"}, {"item": "Bar"}]
```

## Security

### OAuth2 Password Flow
```python
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

# Security scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def authenticate_user(username: str, password: str):
    user = await get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
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

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

## Routers

### Basic Router
```python
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def read_items():
    return [{"name": "Portal Gun", "owner": "Rick"}]

@router.get("/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

@router.put("/{item_id}")
async def update_item(item_id: int):
    return {"item_id": item_id, "name": "Updated name"}

# Include router in main app
app.include_router(router)
```

### Multiple Routers
```python
from fastapi import FastAPI
from .routers import users, items

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(items.router, prefix="/items", tags=["items"])
```

## Middleware

### CORS Middleware
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Don't use this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Custom Middleware
```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Custom-Header"] = "Custom Value"
        return response

app.add_middleware(CustomHeaderMiddleware)
```

## Background Tasks

```python
from fastapi import BackgroundTasks

def send_email_task(email: str, message: str):
    # Simulate sending an email
    print(f"Sending email to {email}: {message}")

@app.post("/send-email")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email_task, email, "Your notification message")
    return {"message": "Notification sent in the background"}
```

## Static Files

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

## Testing

### Basic Test
```python
from fastapi.testclient import TestClient

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}
```

## Error Handling

### Custom Exception Handlers
```python
from fastapi import Request
from fastapi.responses import JSONResponse

class UnicornException(Exception):
    def __init__(self, name: str):
        self.name = name

@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something wrong."}
    )
```

### HTTPException
```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id == 3:
        raise HTTPException(status_code=418, detail="Item not found")
    return {"item_id": item_id}
```

## Database Integration

### Async Database Example (using databases + SQLAlchemy Core)
```python
import databases
import sqlalchemy
from fastapi import FastAPI

DATABASE_URL = "sqlite:///./test.db"
database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

notes = sqlalchemy.Table(
    "notes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("title", sqlalchemy.String(50)),
    sqlalchemy.Column("content", sqlalchemy.String(500)),
)

engine = sqlalchemy.create_engine(DATABASE_URL)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/notes/")
async def read_notes(skip: int = 0, take: int = 20):
    query = notes.select().offset(skip).limit(take)
    return await database.fetch_all(query)
```

## Async Best Practices

### Async Database Operations
```python
import asyncpg

async def get_user_by_id(user_id: int) -> Union[dict, None]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        query = "SELECT * FROM users WHERE id = $1"
        user = await conn.fetchrow(query, user_id)
        return dict(user) if user else None
    finally:
        await conn.close()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Async HTTP Requests
```python
import httpx

async def fetch_external_data(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

@app.get("/external-data")
async def get_external_data():
    data = await fetch_external_data("https://api.example.com/data")
    return data
```

## Configuration and Settings

### Settings with Pydantic
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "FastAPI Application"
    admin_email: str
    database_url: str
    secret_key: str
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

### Environment Variables
```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
```