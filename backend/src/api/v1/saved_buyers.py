"""
API endpoints for managing user's saved buyers.
Provides CRUD operations and search functionality for buyer autocomplete.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user_saved_buyer import UserSavedBuyer

router = APIRouter()


# Pydantic schemas
class SavedBuyerCreate(BaseModel):
    buyer_ntn_cnic: str = Field(..., min_length=1, max_length=20)
    buyer_business_name: str = Field(..., min_length=1, max_length=255)
    buyer_province: Optional[str] = Field(None, max_length=100)
    buyer_address: Optional[str] = Field(None, max_length=500)
    buyer_registration_type: Optional[str] = Field(None, max_length=20)


class SavedBuyerUpdate(BaseModel):
    buyer_ntn_cnic: Optional[str] = Field(None, min_length=1, max_length=20)
    buyer_business_name: Optional[str] = Field(None, min_length=1, max_length=255)
    buyer_province: Optional[str] = Field(None, max_length=100)
    buyer_address: Optional[str] = Field(None, max_length=500)
    buyer_registration_type: Optional[str] = Field(None, max_length=20)
    is_active: Optional[int] = Field(None, ge=0, le=1)
    display_order: Optional[int] = Field(None, ge=0)


class SavedBuyerResponse(BaseModel):
    id: int
    user_id: UUID
    buyer_ntn_cnic: str
    buyer_business_name: str
    buyer_province: Optional[str]
    buyer_address: Optional[str]
    buyer_registration_type: Optional[str]
    is_active: int
    display_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/saved-buyers", response_model=List[SavedBuyerResponse])
async def get_saved_buyers(
    active_only: bool = Query(True, description="Return only active buyers"),
    search: Optional[str] = Query(None, description="Search by business name"),
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get all saved buyers for the current user.
    Supports filtering by active status and searching by business name.
    """
    query = db.query(UserSavedBuyer).filter(UserSavedBuyer.user_id == UUID(user_id))

    if active_only:
        query = query.filter(UserSavedBuyer.is_active == 1)

    if search:
        query = query.filter(UserSavedBuyer.buyer_business_name.ilike(f"%{search}%"))

    buyers = query.order_by(UserSavedBuyer.display_order, UserSavedBuyer.created_at.desc()).all()
    return buyers


@router.get("/saved-buyers/{buyer_id}", response_model=SavedBuyerResponse)
async def get_saved_buyer(
    buyer_id: int,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """Get a specific saved buyer by ID."""
    buyer = db.query(UserSavedBuyer).filter(
        UserSavedBuyer.id == buyer_id,
        UserSavedBuyer.user_id == UUID(user_id)
    ).first()

    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved buyer not found"
        )

    return buyer


@router.post("/saved-buyers", response_model=SavedBuyerResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_buyer(
    buyer_data: SavedBuyerCreate,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Create a new saved buyer for the current user.
    Checks for duplicates based on NTN/CNIC.
    """
    # Check if buyer with same NTN/CNIC already exists for this user
    existing = db.query(UserSavedBuyer).filter(
        UserSavedBuyer.user_id == UUID(user_id),
        UserSavedBuyer.buyer_ntn_cnic == buyer_data.buyer_ntn_cnic,
        UserSavedBuyer.is_active == 1
    ).first()

    if existing:
        # Update existing buyer instead of creating duplicate
        existing.buyer_business_name = buyer_data.buyer_business_name
        existing.buyer_province = buyer_data.buyer_province
        existing.buyer_address = buyer_data.buyer_address
        existing.buyer_registration_type = buyer_data.buyer_registration_type
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    # Get the next display order
    max_order = db.query(UserSavedBuyer).filter(
        UserSavedBuyer.user_id == UUID(user_id)
    ).count()

    new_buyer = UserSavedBuyer(
        user_id=UUID(user_id),
        buyer_ntn_cnic=buyer_data.buyer_ntn_cnic,
        buyer_business_name=buyer_data.buyer_business_name,
        buyer_province=buyer_data.buyer_province,
        buyer_address=buyer_data.buyer_address,
        buyer_registration_type=buyer_data.buyer_registration_type,
        is_active=1,
        display_order=max_order,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(new_buyer)
    db.commit()
    db.refresh(new_buyer)

    return new_buyer


@router.put("/saved-buyers/{buyer_id}", response_model=SavedBuyerResponse)
async def update_saved_buyer(
    buyer_id: int,
    buyer_data: SavedBuyerUpdate,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """Update an existing saved buyer."""
    buyer = db.query(UserSavedBuyer).filter(
        UserSavedBuyer.id == buyer_id,
        UserSavedBuyer.user_id == UUID(user_id)
    ).first()

    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved buyer not found"
        )

    # Update fields
    update_data = buyer_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(buyer, field, value)

    buyer.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(buyer)

    return buyer


@router.delete("/saved-buyers/{buyer_id}")
async def delete_saved_buyer(
    buyer_id: int,
    hard_delete: bool = Query(False, description="Permanently delete instead of soft delete"),
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """Delete a saved buyer (soft delete by default)."""
    buyer = db.query(UserSavedBuyer).filter(
        UserSavedBuyer.id == buyer_id,
        UserSavedBuyer.user_id == UUID(user_id)
    ).first()

    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved buyer not found"
        )

    if hard_delete:
        db.delete(buyer)
    else:
        buyer.is_active = 0
        buyer.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "Saved buyer deleted successfully"}
