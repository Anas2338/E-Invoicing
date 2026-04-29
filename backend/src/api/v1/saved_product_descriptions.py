"""
API endpoints for managing user's saved product descriptions.
Allows users to save product descriptions separately for quick invoice creation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel
from uuid import UUID
import logging
from datetime import datetime

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user_saved_product_description import UserSavedProductDescription

router = APIRouter()
logger = logging.getLogger(__name__)


class SavedProductDescriptionCreate(BaseModel):
    """Request model for creating a saved product description"""
    product_description: str


class SavedProductDescriptionUpdate(BaseModel):
    """Request model for updating a saved product description"""
    product_description: str


@router.get("/saved-product-descriptions", response_model=List[Dict[str, Any]])
async def get_saved_product_descriptions(
    active_only: bool = True,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get user's saved product descriptions.

    Args:
        active_only: If True, only return active descriptions (default: True)

    Returns:
        List of saved product descriptions
    """
    try:
        query = db.query(UserSavedProductDescription).filter(
            UserSavedProductDescription.user_id == UUID(user_id)
        )

        if active_only:
            query = query.filter(UserSavedProductDescription.is_active == 1)

        descriptions = query.order_by(
            UserSavedProductDescription.display_order,
            UserSavedProductDescription.created_at
        ).all()

        result = []
        for description in descriptions:
            result.append({
                "id": description.id,
                "product_description": description.product_description,
                "created_at": description.created_at.isoformat() if description.created_at else None,
                "updated_at": description.updated_at.isoformat() if description.updated_at else None
            })

        return result

    except Exception as e:
        logger.error(f"Error fetching saved product descriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved product descriptions"
        )


@router.post("/saved-product-descriptions", response_model=Dict[str, Any])
async def create_saved_product_description(
    description_data: SavedProductDescriptionCreate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Create a new saved product description.

    Args:
        description_data: Product description data

    Returns:
        Created saved product description
    """
    try:
        new_description = UserSavedProductDescription(
            user_id=UUID(user_id),
            product_description=description_data.product_description,
            is_active=1
        )

        db.add(new_description)
        db.commit()
        db.refresh(new_description)

        logger.info(f"User {user_id} created saved product description: {new_description.id}")

        return {
            "id": new_description.id,
            "product_description": new_description.product_description,
            "created_at": new_description.created_at.isoformat() if new_description.created_at else None,
            "updated_at": new_description.updated_at.isoformat() if new_description.updated_at else None
        }

    except Exception as e:
        logger.error(f"Error creating saved product description: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create saved product description: {str(e)}"
        )


@router.put("/saved-product-descriptions/{description_id}", response_model=Dict[str, Any])
async def update_saved_product_description(
    description_id: int,
    description_update: SavedProductDescriptionUpdate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update a saved product description.

    Args:
        description_id: ID of the saved product description to update
        description_update: Updated product description data

    Returns:
        Updated saved product description
    """
    try:
        description = db.query(UserSavedProductDescription).filter(
            UserSavedProductDescription.id == description_id,
            UserSavedProductDescription.user_id == UUID(user_id)
        ).first()

        if not description:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved product description not found"
            )

        # Update product description
        description.product_description = description_update.product_description
        description.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(description)

        logger.info(f"User {user_id} updated saved product description: {description_id}")

        return {
            "id": description.id,
            "product_description": description.product_description,
            "created_at": description.created_at.isoformat() if description.created_at else None,
            "updated_at": description.updated_at.isoformat() if description.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating saved product description: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update saved product description: {str(e)}"
        )


@router.delete("/saved-product-descriptions/{description_id}")
async def delete_saved_product_description(
    description_id: int,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Delete a saved product description (soft delete).

    Args:
        description_id: ID of the saved product description to delete

    Returns:
        Success message
    """
    try:
        description = db.query(UserSavedProductDescription).filter(
            UserSavedProductDescription.id == description_id,
            UserSavedProductDescription.user_id == UUID(user_id)
        ).first()

        if not description:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved product description not found"
            )

        # Soft delete
        description.is_active = 0
        description.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"User {user_id} deleted saved product description: {description_id}")

        return {"message": "Saved product description deactivated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting saved product description: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete saved product description: {str(e)}"
        )
