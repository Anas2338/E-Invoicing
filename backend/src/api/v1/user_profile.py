"""
API endpoints for managing user profile including FBR credentials and saved products.
Provides a unified interface for profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from uuid import UUID
import logging
from datetime import datetime, time

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user import User
from src.models.user_saved_product import UserSavedProduct
from src.utils.encryption import get_encryption_service
from src.services.auto_posting_service import AutoPostingService
from src.schemas.auto_posting import (
    AutoPostingConfig,
    AutoPostingConfigUpdate,
    EmergencyPauseResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


class UserProfileResponse(BaseModel):
    """Response model for user profile"""
    id: str
    email: str
    name: Optional[str]
    fbr_seller_ntn: Optional[str]
    fbr_business_name: Optional[str]
    fbr_seller_province: Optional[str]
    fbr_seller_address: Optional[str]
    fbr_environment: Optional[str]
    has_fbr_token: bool
    saved_products_count: int
    invoice_prefix: Optional[str]
    invoice_start_number: Optional[int]
    invoice_padding: Optional[int]
    invoice_include_year: Optional[bool]


class UserProfileUpdate(BaseModel):
    """Request model for updating user profile"""
    name: Optional[str] = None
    fbr_seller_ntn: Optional[str] = None
    fbr_business_name: Optional[str] = None
    fbr_seller_province: Optional[str] = None
    fbr_seller_address: Optional[str] = None


class InvoiceSettingsUpdate(BaseModel):
    """Request model for updating invoice numbering settings"""
    invoice_prefix: Optional[str] = None
    invoice_start_number: Optional[int] = None
    invoice_padding: Optional[int] = None
    invoice_include_year: Optional[bool] = None


@router.get("/profile", response_model=Dict[str, Any])
async def get_user_profile(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get complete user profile including FBR credentials and saved products count.

    Returns:
        User profile with business information and saved products count
    """
    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Count saved products
        saved_products_count = db.query(UserSavedProduct).filter(
            UserSavedProduct.user_id == UUID(user_id),
            UserSavedProduct.is_active == 1
        ).count()

        # Count validated products
        validated_products_count = db.query(UserSavedProduct).filter(
            UserSavedProduct.user_id == UUID(user_id),
            UserSavedProduct.is_active == 1,
            UserSavedProduct.fbr_validated == True
        ).count()

        # Check if user has FBR token
        has_fbr_token = bool(user.fbr_sandbox_token or user.fbr_production_token or user.fbr_access_token)

        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "fbr_seller_ntn": user.fbr_seller_ntn,
            "fbr_business_name": user.fbr_business_name,
            "fbr_seller_province": user.fbr_seller_province,
            "fbr_seller_address": user.fbr_seller_address,
            "fbr_environment": user.fbr_environment,
            "has_fbr_token": has_fbr_token,
            "saved_products_count": saved_products_count,
            "validated_products_count": validated_products_count,
            "invoice_prefix": user.invoice_prefix or 'INV-',
            "invoice_start_number": user.invoice_start_number or 1,
            "invoice_padding": user.invoice_padding or 4,
            "invoice_include_year": user.invoice_include_year or False,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile"
        )


@router.put("/profile", response_model=Dict[str, Any])
async def update_user_profile(
    profile_update: UserProfileUpdate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update user profile information.

    Args:
        profile_update: Updated profile data

    Returns:
        Updated user profile
    """
    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update fields if provided
        if profile_update.name is not None:
            user.name = profile_update.name
        if profile_update.fbr_seller_ntn is not None:
            user.fbr_seller_ntn = profile_update.fbr_seller_ntn
        if profile_update.fbr_business_name is not None:
            user.fbr_business_name = profile_update.fbr_business_name
        if profile_update.fbr_seller_province is not None:
            user.fbr_seller_province = profile_update.fbr_seller_province
        if profile_update.fbr_seller_address is not None:
            user.fbr_seller_address = profile_update.fbr_seller_address

        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        logger.info(f"User {user_id} updated profile")

        # Count saved products
        saved_products_count = db.query(UserSavedProduct).filter(
            UserSavedProduct.user_id == UUID(user_id),
            UserSavedProduct.is_active == 1
        ).count()

        validated_products_count = db.query(UserSavedProduct).filter(
            UserSavedProduct.user_id == UUID(user_id),
            UserSavedProduct.is_active == 1,
            UserSavedProduct.fbr_validated == True
        ).count()

        has_fbr_token = bool(user.fbr_sandbox_token or user.fbr_production_token or user.fbr_access_token)

        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "fbr_seller_ntn": user.fbr_seller_ntn,
            "fbr_business_name": user.fbr_business_name,
            "fbr_seller_province": user.fbr_seller_province,
            "fbr_seller_address": user.fbr_seller_address,
            "fbr_environment": user.fbr_environment,
            "has_fbr_token": has_fbr_token,
            "saved_products_count": saved_products_count,
            "validated_products_count": validated_products_count,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user profile: {str(e)}"
        )


@router.get("/profile/seller-info", response_model=Dict[str, Any])
async def get_seller_info_for_invoice(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get seller information pre-filled for invoice creation.
    Returns user's stored FBR seller details to auto-populate invoice forms.

    Returns:
        Seller information for invoice creation
    """
    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "seller_ntn_cnic": user.fbr_seller_ntn or "",
            "seller_business_name": user.fbr_business_name or "",
            "seller_province": user.fbr_seller_province or "",
            "seller_address": user.fbr_seller_address or "",
            "is_complete": all([
                user.fbr_seller_ntn,
                user.fbr_business_name,
                user.fbr_seller_province,
                user.fbr_seller_address
            ])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching seller info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch seller information"
        )


@router.put("/profile/invoice-settings", response_model=Dict[str, Any])
async def update_invoice_settings(
    settings_update: InvoiceSettingsUpdate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update invoice numbering settings for the user.

    Args:
        settings_update: Updated invoice settings

    Returns:
        Updated invoice settings
    """
    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update fields if provided
        if settings_update.invoice_prefix is not None:
            user.invoice_prefix = settings_update.invoice_prefix
        if settings_update.invoice_start_number is not None:
            user.invoice_start_number = settings_update.invoice_start_number
        if settings_update.invoice_padding is not None:
            user.invoice_padding = settings_update.invoice_padding
        if settings_update.invoice_include_year is not None:
            user.invoice_include_year = settings_update.invoice_include_year

        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        logger.info(f"User {user_id} updated invoice settings")

        return {
            "invoice_prefix": user.invoice_prefix or 'INV-',
            "invoice_start_number": user.invoice_start_number or 1,
            "invoice_padding": user.invoice_padding or 4,
            "invoice_include_year": user.invoice_include_year or False,
            "message": "Invoice settings updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating invoice settings: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update invoice settings: {str(e)}"
        )


@router.get("/profile/next-invoice-number", response_model=Dict[str, Any])
async def get_next_invoice_number(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Generate the next invoice number based on user's settings and latest invoice.

    Returns:
        Next invoice number to use
    """
    try:
        from src.models.invoice import Invoice
        from sqlalchemy import desc

        user = db.query(User).filter(User.id == UUID(user_id)).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get user's invoice settings
        prefix = user.invoice_prefix or 'INV-'
        start_number = user.invoice_start_number or 1
        padding = user.invoice_padding or 4
        include_year = user.invoice_include_year or False

        # Get the latest invoice for this user
        latest_invoice = db.query(Invoice).filter(
            Invoice.user_id == UUID(user_id),
            Invoice.is_deleted == False
        ).order_by(desc(Invoice.created_at)).first()

        if latest_invoice and latest_invoice.external_id:
            # Extract numeric part from the latest invoice number
            import re
            match = re.search(r'(\d+)$', latest_invoice.external_id)

            if match:
                last_number = int(match.group(1))
                next_number = last_number + 1
            else:
                # No numeric part found, use start number
                next_number = start_number
        else:
            # No previous invoices, use start number
            next_number = start_number

        # Format the invoice number
        padded_number = str(next_number).zfill(padding)

        if include_year:
            from datetime import datetime
            current_year = datetime.now().year
            invoice_number = f"{prefix}{current_year}-{padded_number}"
        else:
            invoice_number = f"{prefix}{padded_number}"

        return {
            "invoice_number": invoice_number,
            "next_number": next_number,
            "settings": {
                "prefix": prefix,
                "padding": padding,
                "include_year": include_year
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating next invoice number: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate next invoice number: {str(e)}"
        )


@router.get("/profile/auto-posting", response_model=Dict[str, Any])
async def get_auto_posting_config(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get user's auto-posting configuration.

    Returns:
        Auto-posting configuration including enabled status, time window, environment, and daily limit
    """
    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "auto_posting_enabled": user.auto_posting_enabled,
            "auto_posting_start_time": user.auto_posting_start_time.isoformat() if user.auto_posting_start_time else "09:00:00",
            "auto_posting_end_time": user.auto_posting_end_time.isoformat() if user.auto_posting_end_time else "18:00:00",
            "auto_posting_environment": user.auto_posting_environment or "SANDBOX",
            "auto_posting_daily_limit": user.auto_posting_daily_limit or 100,
            "auto_posting_paused_until": user.auto_posting_paused_until.isoformat() if user.auto_posting_paused_until else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching auto-posting config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch auto-posting configuration"
        )


@router.put("/profile/auto-posting", response_model=Dict[str, Any])
async def update_auto_posting_config(
    config_update: AutoPostingConfigUpdate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update user's auto-posting configuration.

    Args:
        config_update: Updated auto-posting configuration

    Returns:
        Updated auto-posting configuration
    """
    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Initialize service for validation
        service = AutoPostingService(db)

        # Validate environment switch (Sandbox → Production requires re-authentication)
        if config_update.auto_posting_environment is not None:
            if config_update.auto_posting_environment != user.auto_posting_environment:
                # Check if switching to Production
                if config_update.auto_posting_environment == "PRODUCTION":
                    # Verify user has Production FBR token
                    if not user.fbr_production_token:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Production FBR token required. Please configure your Production credentials first."
                        )

        # Validate time window
        start_time = config_update.auto_posting_start_time or user.auto_posting_start_time
        end_time = config_update.auto_posting_end_time or user.auto_posting_end_time
        is_valid, error_msg = service.validate_time_window(start_time, end_time)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Validate daily limit
        if config_update.auto_posting_daily_limit is not None:
            is_valid, error_msg = service.validate_daily_limit(config_update.auto_posting_daily_limit)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )

        # Validate environment
        if config_update.auto_posting_environment is not None:
            is_valid, error_msg = service.validate_environment(config_update.auto_posting_environment)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )

        # Update fields if provided
        if config_update.auto_posting_enabled is not None:
            user.auto_posting_enabled = config_update.auto_posting_enabled
        if config_update.auto_posting_start_time is not None:
            user.auto_posting_start_time = config_update.auto_posting_start_time
        if config_update.auto_posting_end_time is not None:
            user.auto_posting_end_time = config_update.auto_posting_end_time
        if config_update.auto_posting_environment is not None:
            user.auto_posting_environment = config_update.auto_posting_environment
        if config_update.auto_posting_daily_limit is not None:
            user.auto_posting_daily_limit = config_update.auto_posting_daily_limit
        if config_update.auto_posting_paused_until is not None:
            user.auto_posting_paused_until = config_update.auto_posting_paused_until

        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        # Log configuration changes
        changes_dict = config_update.dict(exclude_unset=True)
        logger.info(f"User {user_id} updated auto-posting configuration: {changes_dict}")

        return {
            "auto_posting_enabled": user.auto_posting_enabled,
            "auto_posting_start_time": user.auto_posting_start_time.isoformat() if user.auto_posting_start_time else "09:00:00",
            "auto_posting_end_time": user.auto_posting_end_time.isoformat() if user.auto_posting_end_time else "18:00:00",
            "auto_posting_environment": user.auto_posting_environment or "SANDBOX",
            "auto_posting_daily_limit": user.auto_posting_daily_limit or 100,
            "auto_posting_paused_until": user.auto_posting_paused_until.isoformat() if user.auto_posting_paused_until else None,
            "message": "Auto-posting configuration updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating auto-posting config: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update auto-posting configuration: {str(e)}"
        )


@router.post("/profile/auto-posting/emergency-pause", response_model=EmergencyPauseResponse)
async def emergency_pause_auto_posting(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Emergency pause auto-posting immediately.
    Disables auto-posting and requires manual re-enable.

    Returns:
        Confirmation of emergency pause
    """
    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Disable auto-posting
        user.auto_posting_enabled = False
        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        logger.warning(f"User {user_id} triggered emergency pause for auto-posting")

        return EmergencyPauseResponse(
            success=True,
            message="Auto-posting disabled. Please re-enable in profile settings when ready.",
            auto_posting_enabled=False
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during emergency pause: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause auto-posting: {str(e)}"
        )
