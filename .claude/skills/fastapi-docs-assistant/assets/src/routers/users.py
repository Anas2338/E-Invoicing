from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr
from ..models import UserCreate, UserResponse, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "User not found"}},
)

# Simulated database
fake_users_db = []

@router.get("/", response_model=List[UserResponse])
async def read_users(skip: int = 0, limit: int = 100):
    return fake_users_db[skip:skip + limit]

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(user_id: int):
    if user_id < 0 or user_id >= len(fake_users_db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return fake_users_db[user_id]

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    user_id = len(fake_users_db)
    user_response = UserResponse(id=user_id, **user.model_dump(), is_active=True)
    fake_users_db.append(user_response)
    return user_response

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate):
    if user_id < 0 or user_id >= len(fake_users_db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update user data
    db_user = fake_users_db[user_id]
    update_data = user_update.model_dump(exclude_unset=True)
    updated_user = UserResponse(
        **{**db_user.model_dump(), **update_data}
    )
    fake_users_db[user_id] = updated_user
    return updated_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    if user_id < 0 or user_id >= len(fake_users_db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    fake_users_db.pop(user_id)
    return