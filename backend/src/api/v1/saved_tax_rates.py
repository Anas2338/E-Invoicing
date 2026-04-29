"""
API endpoints for managing user's saved tax rates.
Allows users to save tax rates manually for quick invoice creation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from uuid import UUID
import logging
from datetime import datetime

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user_saved_tax_rate import UserSavedTaxRate

router = APIRouter()
logger = logging.getLogger(__name__)


class SavedTaxRateCreate(BaseModel):
    """Request model for creating a saved tax rate"""
    tax_rate: str
    description: Optional[str] = None


class SavedTaxRateUpdate(BaseModel):
    """Request model for updating a saved tax rate"""
    tax_rate: str
    description: Optional[str] = None


@router.get("/saved-tax-rates", response_model=List[Dict[str, Any]])
async def get_saved_tax_rates(
    active_only: bool = True,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get user's saved tax rates.

    Args:
        active_only: If True, only return active tax rates (default: True)

    Returns:
        List of saved tax rates
    """
    try:
        query = db.query(UserSavedTaxRate).filter(
            UserSavedTaxRate.user_id == UUID(user_id)
        )

        if active_only:
            query = query.filter(UserSavedTaxRate.is_active == 1)

        tax_rates = query.order_by(
            UserSavedTaxRate.display_order,
            UserSavedTaxRate.created_at
        ).all()

        result = []
        for tax_rate in tax_rates:
            result.append({
                "id": tax_rate.id,
                "tax_rate": tax_rate.tax_rate,
                "description": tax_rate.description,
                "created_at": tax_rate.created_at.isoformat() if tax_rate.created_at else None,
                "updated_at": tax_rate.updated_at.isoformat() if tax_rate.updated_at else None
            })

        return result

    except Exception as e:
        logger.error(f"Error fetching saved tax rates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved tax rates"
        )


@router.post("/saved-tax-rates", response_model=Dict[str, Any])
async def create_saved_tax_rate(
    tax_rate_data: SavedTaxRateCreate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Create a new saved tax rate.

    Args:
        tax_rate_data: Tax rate data

    Returns:
        Created saved tax rate
    """
    try:
        new_tax_rate = UserSavedTaxRate(
            user_id=UUID(user_id),
            tax_rate=tax_rate_data.tax_rate,
            description=tax_rate_data.description,
            is_active=1
        )

        db.add(new_tax_rate)
        db.commit()
        db.refresh(new_tax_rate)

        logger.info(f"User {user_id} created saved tax rate: {new_tax_rate.id}")

        return {
            "id": new_tax_rate.id,
            "tax_rate": new_tax_rate.tax_rate,
            "description": new_tax_rate.description,
            "created_at": new_tax_rate.created_at.isoformat() if new_tax_rate.created_at else None,
            "updated_at": new_tax_rate.updated_at.isoformat() if new_tax_rate.updated_at else None
        }

    except Exception as e:
        logger.error(f"Error creating saved tax rate: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create saved tax rate: {str(e)}"
        )


@router.put("/saved-tax-rates/{tax_rate_id}", response_model=Dict[str, Any])
async def update_saved_tax_rate(
    tax_rate_id: int,
    tax_rate_update: SavedTaxRateUpdate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update a saved tax rate.

    Args:
        tax_rate_id: ID of the saved tax rate to update
        tax_rate_update: Updated tax rate data

    Returns:
        Updated saved tax rate
    """
    try:
        tax_rate = db.query(UserSavedTaxRate).filter(
            UserSavedTaxRate.id == tax_rate_id,
            UserSavedTaxRate.user_id == UUID(user_id)
        ).first()

        if not tax_rate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved tax rate not found"
            )

        # Update tax rate
        tax_rate.tax_rate = tax_rate_update.tax_rate
        tax_rate.description = tax_rate_update.description
        tax_rate.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(tax_rate)

        logger.info(f"User {user_id} updated saved tax rate: {tax_rate_id}")

        return {
            "id": tax_rate.id,
            "tax_rate": tax_rate.tax_rate,
            "description": tax_rate.description,
            "created_at": tax_rate.created_at.isoformat() if tax_rate.created_at else None,
            "updated_at": tax_rate.updated_at.isoformat() if tax_rate.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating saved tax rate: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update saved tax rate: {str(e)}"
        )


@router.delete("/saved-tax-rates/{tax_rate_id}")
async def delete_saved_tax_rate(
    tax_rate_id: int,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Delete a saved tax rate (soft delete).

    Args:
        tax_rate_id: ID of the saved tax rate to delete

    Returns:
        Success message
    """
    try:
        tax_rate = db.query(UserSavedTaxRate).filter(
            UserSavedTaxRate.id == tax_rate_id,
            UserSavedTaxRate.user_id == UUID(user_id)
        ).first()

        if not tax_rate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved tax rate not found"
            )

        # Soft delete
        tax_rate.is_active = 0
        tax_rate.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"User {user_id} deleted saved tax rate: {tax_rate_id}")

        return {"message": "Saved tax rate deactivated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting saved tax rate: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete saved tax rate: {str(e)}"
        )
