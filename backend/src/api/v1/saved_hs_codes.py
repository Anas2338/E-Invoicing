"""
API endpoints for managing user's saved HS codes.
Allows users to save HS codes separately for quick invoice creation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel
from uuid import UUID
import logging
from datetime import datetime

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user_saved_hs_code import UserSavedHSCode
from src.models.fbr_master_data import FBRHSCode

router = APIRouter()
logger = logging.getLogger(__name__)


class SavedHSCodeCreate(BaseModel):
    """Request model for creating a saved HS code"""
    hs_code: str


class SavedHSCodeUpdate(BaseModel):
    """Request model for updating a saved HS code"""
    hs_code: str


@router.get("/saved-hs-codes", response_model=List[Dict[str, Any]])
async def get_saved_hs_codes(
    active_only: bool = True,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get user's saved HS codes.

    Args:
        active_only: If True, only return active HS codes (default: True)

    Returns:
        List of saved HS codes
    """
    try:
        query = db.query(UserSavedHSCode).filter(
            UserSavedHSCode.user_id == UUID(user_id)
        )

        if active_only:
            query = query.filter(UserSavedHSCode.is_active == 1)

        hs_codes = query.order_by(
            UserSavedHSCode.display_order,
            UserSavedHSCode.created_at
        ).all()

        result = []
        for hs_code in hs_codes:
            # Fetch FBR description for this HS code
            fbr_hs_code = db.query(FBRHSCode).filter(
                FBRHSCode.code == hs_code.hs_code
            ).first()

            fbr_description = fbr_hs_code.description if fbr_hs_code else None

            result.append({
                "id": hs_code.id,
                "hs_code": hs_code.hs_code,
                "fbr_description": fbr_description,
                "fbr_validated": hs_code.fbr_validated,
                "fbr_validation_date": hs_code.fbr_validation_date.isoformat() if hs_code.fbr_validation_date else None,
                "fbr_validation_error": hs_code.fbr_validation_error,
                "created_at": hs_code.created_at.isoformat() if hs_code.created_at else None,
                "updated_at": hs_code.updated_at.isoformat() if hs_code.updated_at else None
            })

        return result

    except Exception as e:
        logger.error(f"Error fetching saved HS codes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved HS codes"
        )


@router.post("/saved-hs-codes", response_model=Dict[str, Any])
async def create_saved_hs_code(
    hs_code_data: SavedHSCodeCreate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Create a new saved HS code with FBR validation.
    Validates HS code against FBR master data.

    Args:
        hs_code_data: HS code data

    Returns:
        Created saved HS code with validation status
    """
    try:
        # Validate HS code against FBR master data
        fbr_hs_code = db.query(FBRHSCode).filter(
            FBRHSCode.code == hs_code_data.hs_code
        ).first()

        fbr_validated = False
        fbr_validation_error = None

        if not fbr_hs_code:
            fbr_validation_error = f"HS Code '{hs_code_data.hs_code}' not found in FBR master data"
            logger.warning(f"User {user_id} attempted to save invalid HS code: {hs_code_data.hs_code}")
        else:
            # HS code exists in FBR master data - mark as validated
            fbr_validated = True
            logger.info(f"User {user_id} saved FBR-validated HS code: {hs_code_data.hs_code}")

        new_hs_code = UserSavedHSCode(
            user_id=UUID(user_id),
            hs_code=hs_code_data.hs_code,
            is_active=1,
            fbr_validated=fbr_validated,
            fbr_validation_date=datetime.utcnow() if fbr_validated else None,
            fbr_validation_error=fbr_validation_error
        )

        db.add(new_hs_code)
        db.commit()
        db.refresh(new_hs_code)

        logger.info(f"User {user_id} created saved HS code: {new_hs_code.id} (validated: {fbr_validated})")

        return {
            "id": new_hs_code.id,
            "hs_code": new_hs_code.hs_code,
            "fbr_validated": new_hs_code.fbr_validated,
            "fbr_validation_date": new_hs_code.fbr_validation_date.isoformat() if new_hs_code.fbr_validation_date else None,
            "fbr_validation_error": new_hs_code.fbr_validation_error,
            "created_at": new_hs_code.created_at.isoformat() if new_hs_code.created_at else None,
            "updated_at": new_hs_code.updated_at.isoformat() if new_hs_code.updated_at else None
        }

    except Exception as e:
        logger.error(f"Error creating saved HS code: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create saved HS code: {str(e)}"
        )


@router.put("/saved-hs-codes/{hs_code_id}", response_model=Dict[str, Any])
async def update_saved_hs_code(
    hs_code_id: int,
    hs_code_update: SavedHSCodeUpdate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update a saved HS code.

    Args:
        hs_code_id: ID of the saved HS code to update
        hs_code_update: Updated HS code data

    Returns:
        Updated saved HS code
    """
    try:
        hs_code = db.query(UserSavedHSCode).filter(
            UserSavedHSCode.id == hs_code_id,
            UserSavedHSCode.user_id == UUID(user_id)
        ).first()

        if not hs_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved HS code not found"
            )

        # Update HS code
        hs_code.hs_code = hs_code_update.hs_code
        hs_code.updated_at = datetime.utcnow()

        # Re-validate against FBR master data
        fbr_hs_code = db.query(FBRHSCode).filter(
            FBRHSCode.code == hs_code.hs_code
        ).first()

        if not fbr_hs_code:
            hs_code.fbr_validated = False
            hs_code.fbr_validation_error = f"HS Code '{hs_code.hs_code}' not found in FBR master data"
            hs_code.fbr_validation_date = None
        else:
            # HS code exists in FBR master data - mark as validated
            hs_code.fbr_validated = True
            hs_code.fbr_validation_date = datetime.utcnow()
            hs_code.fbr_validation_error = None

        db.commit()
        db.refresh(hs_code)

        logger.info(f"User {user_id} updated saved HS code: {hs_code_id}")

        return {
            "id": hs_code.id,
            "hs_code": hs_code.hs_code,
            "fbr_validated": hs_code.fbr_validated,
            "fbr_validation_date": hs_code.fbr_validation_date.isoformat() if hs_code.fbr_validation_date else None,
            "fbr_validation_error": hs_code.fbr_validation_error,
            "created_at": hs_code.created_at.isoformat() if hs_code.created_at else None,
            "updated_at": hs_code.updated_at.isoformat() if hs_code.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating saved HS code: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update saved HS code: {str(e)}"
        )


@router.delete("/saved-hs-codes/{hs_code_id}")
async def delete_saved_hs_code(
    hs_code_id: int,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Delete a saved HS code (soft delete).

    Args:
        hs_code_id: ID of the saved HS code to delete

    Returns:
        Success message
    """
    try:
        hs_code = db.query(UserSavedHSCode).filter(
            UserSavedHSCode.id == hs_code_id,
            UserSavedHSCode.user_id == UUID(user_id)
        ).first()

        if not hs_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved HS code not found"
            )

        # Soft delete
        hs_code.is_active = 0
        hs_code.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"User {user_id} deleted saved HS code: {hs_code_id}")

        return {"message": "Saved HS code deactivated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting saved HS code: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete saved HS code: {str(e)}"
        )
