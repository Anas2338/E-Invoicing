"""
API endpoints for managing user's saved products.
Allows users to save commonly used HS codes and product descriptions
for quick invoice creation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from uuid import UUID
import logging
from datetime import datetime

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user_saved_product import UserSavedProduct
from src.models.fbr_master_data import FBRHSCode

router = APIRouter()
logger = logging.getLogger(__name__)


class SavedProductCreate(BaseModel):
    """Request model for creating a saved product"""
    hs_code: str
    product_description: str
    default_uom: Optional[str] = None
    default_rate: Optional[str] = None
    default_sale_type: Optional[str] = "01"
    default_unit_price: Optional[float] = None
    display_order: Optional[int] = 0


class SavedProductUpdate(BaseModel):
    """Request model for updating a saved product"""
    hs_code: Optional[str] = None
    product_description: Optional[str] = None
    default_uom: Optional[str] = None
    default_rate: Optional[str] = None
    default_sale_type: Optional[str] = None
    default_unit_price: Optional[float] = None
    display_order: Optional[int] = None
    is_active: Optional[int] = None


class SavedProductResponse(BaseModel):
    """Response model for saved product"""
    id: int
    hs_code: str
    product_description: str
    default_uom: Optional[str]
    default_rate: Optional[str]
    default_sale_type: Optional[str]
    default_unit_price: Optional[float]
    display_order: int
    is_active: int
    fbr_validated: bool
    fbr_validation_date: Optional[str]
    fbr_validation_error: Optional[str]
    created_at: str
    updated_at: str


@router.get("/saved-products", response_model=List[Dict[str, Any]])
async def get_saved_products(
    active_only: bool = True,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get user's saved products.

    Args:
        active_only: If True, only return active products (default: True)

    Returns:
        List of saved products
    """
    try:
        query = db.query(UserSavedProduct).filter(
            UserSavedProduct.user_id == UUID(user_id)
        )

        if active_only:
            query = query.filter(UserSavedProduct.is_active == 1)

        products = query.order_by(
            UserSavedProduct.display_order,
            UserSavedProduct.created_at
        ).all()

        result = []
        for product in products:
            result.append({
                "id": product.id,
                "hs_code": product.hs_code,
                "product_description": product.product_description,
                "default_uom": product.default_uom,
                "default_rate": product.default_rate,
                "default_sale_type": product.default_sale_type,
                "default_unit_price": float(product.default_unit_price) if product.default_unit_price else None,
                "display_order": product.display_order,
                "is_active": product.is_active,
                "fbr_validated": product.fbr_validated,
                "fbr_validation_date": product.fbr_validation_date.isoformat() if product.fbr_validation_date else None,
                "fbr_validation_error": product.fbr_validation_error,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            })

        return result

    except Exception as e:
        logger.error(f"Error fetching saved products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved products"
        )


@router.get("/saved-products/{product_id}", response_model=Dict[str, Any])
async def get_saved_product(
    product_id: int,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get a specific saved product by ID.

    Args:
        product_id: ID of the saved product

    Returns:
        Saved product details
    """
    try:
        product = db.query(UserSavedProduct).filter(
            UserSavedProduct.id == product_id,
            UserSavedProduct.user_id == UUID(user_id)
        ).first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved product not found"
            )

        return {
            "id": product.id,
            "hs_code": product.hs_code,
            "product_description": product.product_description,
            "default_uom": product.default_uom,
            "default_rate": product.default_rate,
            "default_sale_type": product.default_sale_type,
            "default_unit_price": float(product.default_unit_price) if product.default_unit_price else None,
            "display_order": product.display_order,
            "is_active": product.is_active,
            "fbr_validated": product.fbr_validated,
            "fbr_validation_date": product.fbr_validation_date.isoformat() if product.fbr_validation_date else None,
            "fbr_validation_error": product.fbr_validation_error,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching saved product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved product"
        )


@router.post("/saved-products", response_model=Dict[str, Any])
async def create_saved_product(
    product: SavedProductCreate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Create a new saved product with FBR validation.
    Validates HS code and product description against FBR master data.

    Args:
        product: Saved product data

    Returns:
        Created saved product with validation status
    """
    try:
        # Validate HS code against FBR master data
        fbr_hs_code = db.query(FBRHSCode).filter(
            FBRHSCode.code == product.hs_code
        ).first()

        fbr_validated = False
        fbr_validation_error = None

        if not fbr_hs_code:
            fbr_validation_error = f"HS Code '{product.hs_code}' not found in FBR master data"
            logger.warning(f"User {user_id} attempted to save invalid HS code: {product.hs_code}")
        else:
            # HS code exists in FBR master data - mark as validated
            # User can use their own product description
            fbr_validated = True
            logger.info(f"User {user_id} saved FBR-validated HS code: {product.hs_code}")

        new_product = UserSavedProduct(
            user_id=UUID(user_id),
            hs_code=product.hs_code,
            product_description=product.product_description,
            default_uom=product.default_uom,
            default_rate=product.default_rate,
            default_sale_type=product.default_sale_type,
            default_unit_price=product.default_unit_price,
            display_order=product.display_order,
            is_active=1,
            fbr_validated=fbr_validated,
            fbr_validation_date=datetime.utcnow() if fbr_validated else None,
            fbr_validation_error=fbr_validation_error
        )

        db.add(new_product)
        db.commit()
        db.refresh(new_product)

        logger.info(f"User {user_id} created saved product: {new_product.id} (validated: {fbr_validated})")

        return {
            "id": new_product.id,
            "hs_code": new_product.hs_code,
            "product_description": new_product.product_description,
            "default_uom": new_product.default_uom,
            "default_rate": new_product.default_rate,
            "default_sale_type": new_product.default_sale_type,
            "default_unit_price": float(new_product.default_unit_price) if new_product.default_unit_price else None,
            "display_order": new_product.display_order,
            "is_active": new_product.is_active,
            "fbr_validated": new_product.fbr_validated,
            "fbr_validation_date": new_product.fbr_validation_date.isoformat() if new_product.fbr_validation_date else None,
            "fbr_validation_error": new_product.fbr_validation_error,
            "created_at": new_product.created_at.isoformat() if new_product.created_at else None,
            "updated_at": new_product.updated_at.isoformat() if new_product.updated_at else None
        }

    except Exception as e:
        logger.error(f"Error creating saved product: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create saved product: {str(e)}"
        )


@router.put("/saved-products/{product_id}", response_model=Dict[str, Any])
async def update_saved_product(
    product_id: int,
    product_update: SavedProductUpdate,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update a saved product.

    Args:
        product_id: ID of the saved product to update
        product_update: Updated product data

    Returns:
        Updated saved product
    """
    try:
        product = db.query(UserSavedProduct).filter(
            UserSavedProduct.id == product_id,
            UserSavedProduct.user_id == UUID(user_id)
        ).first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved product not found"
            )

        # Update fields if provided
        if product_update.hs_code is not None:
            product.hs_code = product_update.hs_code
        if product_update.product_description is not None:
            product.product_description = product_update.product_description
        if product_update.default_uom is not None:
            product.default_uom = product_update.default_uom
        if product_update.default_rate is not None:
            product.default_rate = product_update.default_rate
        if product_update.default_sale_type is not None:
            product.default_sale_type = product_update.default_sale_type
        if product_update.default_unit_price is not None:
            product.default_unit_price = product_update.default_unit_price
        if product_update.display_order is not None:
            product.display_order = product_update.display_order
        if product_update.is_active is not None:
            product.is_active = product_update.is_active

        # Re-validate if HS code or description changed
        if product_update.hs_code is not None or product_update.product_description is not None:
            fbr_hs_code = db.query(FBRHSCode).filter(
                FBRHSCode.code == product.hs_code
            ).first()

            if not fbr_hs_code:
                product.fbr_validated = False
                product.fbr_validation_error = f"HS Code '{product.hs_code}' not found in FBR master data"
                product.fbr_validation_date = None
            else:
                # HS code exists in FBR master data - mark as validated
                # User can use their own product description
                product.fbr_validated = True
                product.fbr_validation_date = datetime.utcnow()
                product.fbr_validation_error = None

        db.commit()
        db.refresh(product)

        logger.info(f"User {user_id} updated saved product: {product_id}")

        return {
            "id": product.id,
            "hs_code": product.hs_code,
            "product_description": product.product_description,
            "default_uom": product.default_uom,
            "default_rate": product.default_rate,
            "default_sale_type": product.default_sale_type,
            "default_unit_price": float(product.default_unit_price) if product.default_unit_price else None,
            "display_order": product.display_order,
            "is_active": product.is_active,
            "fbr_validated": product.fbr_validated,
            "fbr_validation_date": product.fbr_validation_date.isoformat() if product.fbr_validation_date else None,
            "fbr_validation_error": product.fbr_validation_error,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating saved product: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update saved product: {str(e)}"
        )


@router.delete("/saved-products/{product_id}")
async def delete_saved_product(
    product_id: int,
    hard_delete: bool = False,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Delete a saved product (soft delete by default).

    Args:
        product_id: ID of the saved product to delete
        hard_delete: If True, permanently delete the product (default: False)

    Returns:
        Success message
    """
    try:
        product = db.query(UserSavedProduct).filter(
            UserSavedProduct.id == product_id,
            UserSavedProduct.user_id == UUID(user_id)
        ).first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved product not found"
            )

        if hard_delete:
            # Permanently delete
            db.delete(product)
            message = "Saved product permanently deleted"
        else:
            # Soft delete
            product.is_active = 0
            message = "Saved product deactivated"

        db.commit()

        logger.info(f"User {user_id} deleted saved product: {product_id} (hard_delete={hard_delete})")

        return {"message": message}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting saved product: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete saved product: {str(e)}"
        )


@router.post("/saved-products/reorder")
async def reorder_saved_products(
    product_ids: List[int],
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Reorder saved products.

    Args:
        product_ids: List of product IDs in desired order

    Returns:
        Success message
    """
    try:
        # Update display_order for each product
        for index, product_id in enumerate(product_ids):
            product = db.query(UserSavedProduct).filter(
                UserSavedProduct.id == product_id,
                UserSavedProduct.user_id == UUID(user_id)
            ).first()

            if product:
                product.display_order = index

        db.commit()

        logger.info(f"User {user_id} reordered saved products")

        return {"message": f"Reordered {len(product_ids)} products"}

    except Exception as e:
        logger.error(f"Error reordering saved products: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder saved products: {str(e)}"
        )
