"""
API endpoints for managing user's saved UOMs.
Allows users to save UOMs from FBR master data for quick invoice creation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel
from uuid import UUID
import logging
from datetime import datetime

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user_saved_uom import UserSavedUOM

router = APIRouter()
logger = logging.getLogger(__name__)


class SavedUOMCreate(BaseModel):
    """Request model for creating a saved UOM"""
    uom_code: str
    uom_name: str


class SavedUOMUpdate(BaseModel):
    """Request model for updating a saved UOM"""
    uom_code: str
    uom_name: str


@router.get("/saved-uoms", response_model=List[Dict[str, Any]])
async def get_saved_uoms(
    active_only: bool = True,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get user's saved UOMs.

    Args:
        active_only: If True, only return active UOMs (default: True)

    Returns:
        List of saved UOMs
    """
    try:
        query = db.query(UserSavedUOM).filter(
            UserSavedUOM.user_id == UUID(user_id)
        )

        if active_only:
            query = query.filter(UserSavedUOM.is_active == 1)

        uoms = query.order_by(
            UserSavedUOM.display_order,
            UserSavedUOM.created_at
        ).all()

        result = []
        for uom in uoms:
            result.append({
                "id": uom.id,
                "uom_code": uom.uom_code,
                "uom_name": uom.uom_name,
                "created_at": uom.created_at.isoformat() if uom.created_at else None,
                "updated_at": uom.updated_at.isoformat() if uom.updated_at else None
            })

        return result

    except Exception as e:
        logger.error(f"Error fetching saved UOMs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved UOMs"
        )


@router.post("/saved-uoms", response_model=Dict[str, Any])
async def create_saved_uom(
    uom_data: SavedUOMCreate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Create a new saved UOM.

    Args:
        uom_data: UOM data

    Returns:
        Created saved UOM
    """
    try:
        new_uom = UserSavedUOM(
            user_id=UUID(user_id),
            uom_code=uom_data.uom_code,
            uom_name=uom_data.uom_name,
            is_active=1
        )

        db.add(new_uom)
        db.commit()
        db.refresh(new_uom)

        logger.info(f"User {user_id} created saved UOM: {new_uom.id}")

        return {
            "id": new_uom.id,
            "uom_code": new_uom.uom_code,
            "uom_name": new_uom.uom_name,
            "created_at": new_uom.created_at.isoformat() if new_uom.created_at else None,
            "updated_at": new_uom.updated_at.isoformat() if new_uom.updated_at else None
        }

    except Exception as e:
        logger.error(f"Error creating saved UOM: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create saved UOM: {str(e)}"
        )


@router.put("/saved-uoms/{uom_id}", response_model=Dict[str, Any])
async def update_saved_uom(
    uom_id: int,
    uom_update: SavedUOMUpdate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update a saved UOM.

    Args:
        uom_id: ID of the saved UOM to update
        uom_update: Updated UOM data

    Returns:
        Updated saved UOM
    """
    try:
        uom = db.query(UserSavedUOM).filter(
            UserSavedUOM.id == uom_id,
            UserSavedUOM.user_id == UUID(user_id)
        ).first()

        if not uom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved UOM not found"
            )

        # Update UOM
        uom.uom_code = uom_update.uom_code
        uom.uom_name = uom_update.uom_name
        uom.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(uom)

        logger.info(f"User {user_id} updated saved UOM: {uom_id}")

        return {
            "id": uom.id,
            "uom_code": uom.uom_code,
            "uom_name": uom.uom_name,
            "created_at": uom.created_at.isoformat() if uom.created_at else None,
            "updated_at": uom.updated_at.isoformat() if uom.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating saved UOM: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update saved UOM: {str(e)}"
        )


@router.delete("/saved-uoms/{uom_id}")
async def delete_saved_uom(
    uom_id: int,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Delete a saved UOM (soft delete).

    Args:
        uom_id: ID of the saved UOM to delete

    Returns:
        Success message
    """
    try:
        uom = db.query(UserSavedUOM).filter(
            UserSavedUOM.id == uom_id,
            UserSavedUOM.user_id == UUID(user_id)
        ).first()

        if not uom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved UOM not found"
            )

        # Soft delete
        uom.is_active = 0
        uom.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"User {user_id} deleted saved UOM: {uom_id}")

        return {"message": "Saved UOM deactivated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting saved UOM: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete saved UOM: {str(e)}"
        )
