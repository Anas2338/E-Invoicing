from contextlib import asynccontextmanager
from typing import Union, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .routers import users

# Database simulation
fake_db = []

# Models
class Item(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0)
    tax: Optional[float] = Field(None, ge=0)

class ItemResponse(Item):
    id: int

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    # Initialize resources (database connections, etc.)
    yield
    # Shutdown
    print("Shutting down...")
    # Clean up resources

# FastAPI app initialization
app = FastAPI(
    title="FastAPI Example API",
    description="This is an example API built with FastAPI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Don't use this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)

# Routes
@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI example API"}

@app.get("/items/", response_model=list[ItemResponse])
async def read_items(skip: int = 0, limit: int = 100):
    return fake_db[skip:skip + limit]

@app.get("/items/{item_id}", response_model=ItemResponse)
async def read_item(item_id: int):
    if item_id < 0 or item_id >= len(fake_db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return fake_db[item_id]

@app.post("/items/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    item_id = len(fake_db)
    item_response = ItemResponse(id=item_id, **item.model_dump())
    fake_db.append(item_response)
    return item_response

@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: int, item: Item):
    if item_id < 0 or item_id >= len(fake_db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    updated_item = ItemResponse(id=item_id, **item.model_dump())
    fake_db[item_id] = updated_item
    return updated_item

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int):
    if item_id < 0 or item_id >= len(fake_db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    fake_db.pop(item_id)
    return

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)