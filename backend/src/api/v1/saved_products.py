"""
API endpoints for managing user's saved products.
Allows users to save commonly used HS codes and product descriptions
for quick invoice creation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from uuid import UUID
import logging
from datetime import datetime
import pandas as pd
import io

from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.user_saved_product import UserSavedProduct
from src.models.fbr_master_data import FBRHSCode, FBRTransactionType, FBRUOM, FBRUOM

router = APIRouter()
logger = logging.getLogger(__name__)


class SavedProductCreate(BaseModel):
    """Request model for creating a saved product"""
    item_code: str
    item_name: str
    hs_code: str
    product_description: str
    default_uom: Optional[str] = None
    default_rate: Optional[str] = None
    default_sale_type: Optional[str] = None
    transaction_type: Optional[str] = None
    sro_schedule_no: Optional[str] = None
    sro_item_serial_no: Optional[str] = None


class SavedProductUpdate(BaseModel):
    """Request model for updating a saved product"""
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    hs_code: Optional[str] = None
    product_description: Optional[str] = None
    default_uom: Optional[str] = None
    default_rate: Optional[str] = None
    default_sale_type: Optional[str] = None
    transaction_type: Optional[str] = None
    sro_schedule_no: Optional[str] = None
    sro_item_serial_no: Optional[str] = None
    is_active: Optional[int] = None


class SavedProductResponse(BaseModel):
    """Response model for saved product"""
    id: int
    item_code: str
    item_name: str
    hs_code: str
    product_description: str
    default_uom: Optional[str]
    default_rate: Optional[str]
    default_sale_type: Optional[str]
    transaction_type: Optional[str]
    sro_schedule_no: Optional[str]
    sro_item_serial_no: Optional[str]
    is_active: int
    fbr_validated: bool
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
            UserSavedProduct.created_at
        ).all()

        result = []
        for product in products:
            result.append({
                "id": product.id,
                "item_code": product.item_code,
                "item_name": product.item_name,
                "hs_code": product.hs_code,
                "product_description": product.product_description,
                "default_uom": product.default_uom,
                "default_rate": product.default_rate,
                "default_sale_type": product.default_sale_type,
                "transaction_type": product.transaction_type,
                "sro_schedule_no": product.sro_schedule_no,
                "sro_item_serial_no": product.sro_item_serial_no,
                "is_active": product.is_active,
                "fbr_validated": product.fbr_validated,
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
            "item_code": product.item_code,
            "item_name": product.item_name,
            "hs_code": product.hs_code,
            "product_description": product.product_description,
            "default_uom": product.default_uom,
            "default_rate": product.default_rate,
            "default_sale_type": product.default_sale_type,
            "transaction_type": product.transaction_type,
            "sro_schedule_no": product.sro_schedule_no,
            "sro_item_serial_no": product.sro_item_serial_no,
            "is_active": product.is_active,
            "fbr_validated": product.fbr_validated,
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
        # Validate item_code is not empty
        if not product.item_code or not product.item_code.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item code is required and cannot be empty"
            )

        # Validate item_name is not empty
        if not product.item_name or not product.item_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item name is required and cannot be empty"
            )

        # Format HS code: normalize to 8 digits with dot (1234.5678)
        hs_code_cleaned = product.hs_code.replace('.', '').replace(' ', '')

        # Pad to 8 digits if needed
        if len(hs_code_cleaned) == 7:
            hs_code_cleaned = hs_code_cleaned + '0'
        elif len(hs_code_cleaned) == 6:
            hs_code_cleaned = hs_code_cleaned + '00'
        elif len(hs_code_cleaned) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid HS code '{product.hs_code}' - must be at least 6 digits"
            )
        elif len(hs_code_cleaned) > 8:
            hs_code_cleaned = hs_code_cleaned[:8]

        # Format with dot: 1234.5678
        hs_code_formatted = f"{hs_code_cleaned[:4]}.{hs_code_cleaned[4:]}"

        # Validate HS code against FBR master data
        fbr_hs_code = db.query(FBRHSCode).filter(
            FBRHSCode.code == hs_code_formatted
        ).first()

        fbr_validated = False

        if not fbr_hs_code:
            logger.warning(f"User {user_id} attempted to save invalid HS code: {hs_code_formatted}")
        else:
            # HS code exists in FBR master data - mark as validated
            # User can use their own product description
            fbr_validated = True
            logger.info(f"User {user_id} saved FBR-validated HS code: {hs_code_formatted}")

        new_product = UserSavedProduct(
            user_id=UUID(user_id),
            item_code=product.item_code.strip(),
            item_name=product.item_name.strip(),
            hs_code=hs_code_formatted,
            product_description=product.product_description,
            default_uom=product.default_uom,
            default_rate=product.default_rate,
            default_sale_type=product.default_sale_type,
            transaction_type=product.transaction_type,
            sro_schedule_no=product.sro_schedule_no,
            sro_item_serial_no=product.sro_item_serial_no,
            is_active=1,
            fbr_validated=fbr_validated
        )

        db.add(new_product)
        db.commit()
        db.refresh(new_product)

        logger.info(f"User {user_id} created saved product: {new_product.id} (validated: {fbr_validated})")

        return {
            "id": new_product.id,
            "item_code": new_product.item_code,
            "item_name": new_product.item_name,
            "hs_code": new_product.hs_code,
            "product_description": new_product.product_description,
            "default_uom": new_product.default_uom,
            "default_rate": new_product.default_rate,
            "default_sale_type": new_product.default_sale_type,
            "transaction_type": new_product.transaction_type,
            "sro_schedule_no": new_product.sro_schedule_no,
            "sro_item_serial_no": new_product.sro_item_serial_no,
            "is_active": new_product.is_active,
            "fbr_validated": new_product.fbr_validated,
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
        if product_update.item_code is not None:
            if not product_update.item_code.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Item code cannot be empty"
                )
            product.item_code = product_update.item_code.strip()
        if product_update.item_name is not None:
            if not product_update.item_name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Item name cannot be empty"
                )
            product.item_name = product_update.item_name.strip()
        if product_update.hs_code is not None:
            # Format HS code: normalize to 8 digits with dot (1234.5678)
            hs_code_cleaned = product_update.hs_code.replace('.', '').replace(' ', '')

            # Pad to 8 digits if needed
            if len(hs_code_cleaned) == 7:
                hs_code_cleaned = hs_code_cleaned + '0'
            elif len(hs_code_cleaned) == 6:
                hs_code_cleaned = hs_code_cleaned + '00'
            elif len(hs_code_cleaned) < 6:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid HS code '{product_update.hs_code}' - must be at least 6 digits"
                )
            elif len(hs_code_cleaned) > 8:
                hs_code_cleaned = hs_code_cleaned[:8]

            # Format with dot: 1234.5678
            product.hs_code = f"{hs_code_cleaned[:4]}.{hs_code_cleaned[4:]}"
        if product_update.product_description is not None:
            product.product_description = product_update.product_description
        if product_update.default_uom is not None:
            product.default_uom = product_update.default_uom
        if product_update.default_rate is not None:
            product.default_rate = product_update.default_rate
        if product_update.default_sale_type is not None:
            product.default_sale_type = product_update.default_sale_type
        if product_update.transaction_type is not None:
            product.transaction_type = product_update.transaction_type
        if product_update.sro_schedule_no is not None:
            product.sro_schedule_no = product_update.sro_schedule_no
        if product_update.sro_item_serial_no is not None:
            product.sro_item_serial_no = product_update.sro_item_serial_no
        if product_update.is_active is not None:
            product.is_active = product_update.is_active

        # Re-validate if HS code or description changed
        if product_update.hs_code is not None or product_update.product_description is not None:
            fbr_hs_code = db.query(FBRHSCode).filter(
                FBRHSCode.code == product.hs_code
            ).first()

            if not fbr_hs_code:
                product.fbr_validated = False
            else:
                # HS code exists in FBR master data - mark as validated
                # User can use their own product description
                product.fbr_validated = True

        db.commit()
        db.refresh(product)

        logger.info(f"User {user_id} updated saved product: {product_id}")

        return {
            "id": product.id,
            "item_code": product.item_code,
            "item_name": product.item_name,
            "hs_code": product.hs_code,
            "product_description": product.product_description,
            "default_uom": product.default_uom,
            "default_rate": product.default_rate,
            "default_sale_type": product.default_sale_type,
            "transaction_type": product.transaction_type,
            "sro_schedule_no": product.sro_schedule_no,
            "sro_item_serial_no": product.sro_item_serial_no,
            "is_active": product.is_active,
            "fbr_validated": product.fbr_validated,
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
    hard_delete: bool = True,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Delete a saved product (hard delete by default).

    Args:
        product_id: ID of the saved product to delete
        hard_delete: If False, soft-delete by setting is_active=0 (default: True)

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


@router.post("/saved-products/bulk-delete")
async def bulk_delete_saved_products(
    product_ids: List[int],
    hard_delete: bool = True,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Delete multiple saved products in bulk (hard delete by default).

    Args:
        product_ids: List of product IDs to delete
        hard_delete: If False, soft-delete by setting is_active=0 (default: True)

    Returns:
        Success message with count
    """
    try:
        if not product_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No product IDs provided"
            )

        # Get all products that belong to the user
        products = db.query(UserSavedProduct).filter(
            UserSavedProduct.id.in_(product_ids),
            UserSavedProduct.user_id == UUID(user_id)
        ).all()

        if not products:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No products found"
            )

        deleted_count = len(products)

        if hard_delete:
            # Permanently delete all
            for product in products:
                db.delete(product)
            message = f"Permanently deleted {deleted_count} product(s)"
        else:
            # Soft delete all
            for product in products:
                product.is_active = 0
            message = f"Deactivated {deleted_count} product(s)"

        db.commit()

        logger.info(f"User {user_id} bulk deleted {deleted_count} saved products (hard_delete={hard_delete})")

        return {"message": message, "deleted_count": deleted_count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk deleting saved products: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete saved products: {str(e)}"
        )


@router.get("/saved-products/debug-hscode/{hs_code}")
async def debug_hscode(
    hs_code: str,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Debug endpoint to check HS code in FBR database.
    Shows what variations exist and helps troubleshoot validation issues.
    """
    try:
        # Clean the input
        cleaned = hs_code.replace('.', '').replace(' ', '')

        # Try different variations
        variations = [
            cleaned,
            cleaned + '0' if len(cleaned) == 7 else cleaned,
            cleaned + '00' if len(cleaned) == 6 else cleaned,
            cleaned[:8] if len(cleaned) > 8 else cleaned,
        ]

        results = {}
        for var in set(variations):
            found = db.query(FBRHSCode).filter(FBRHSCode.code == var).first()
            results[var] = {
                "exists": found is not None,
                "description": found.description if found else None
            }

        # Also search for similar codes
        similar = db.query(FBRHSCode).filter(
            FBRHSCode.code.like(f"{cleaned[:4]}%")
        ).limit(10).all()

        return {
            "input": hs_code,
            "cleaned": cleaned,
            "variations_checked": results,
            "similar_codes": [{"code": s.code, "description": s.description} for s in similar]
        }

    except Exception as e:
        logger.error(f"Error debugging HS code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to debug HS code: {str(e)}"
        )


@router.get("/saved-products/template/download")
async def download_template(
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Download Excel template for bulk upload of saved items.

    Returns:
        Excel file with template columns and reference data
    """
    try:
        # Get first transaction type from database for sample data
        sample_transaction_type = db.query(FBRTransactionType).first()
        transaction_type_name = sample_transaction_type.name if sample_transaction_type else 'Goods'

        # Create template DataFrame with column headers
        template_data = {
            'item_code': ['ITEM-001', 'ITEM-002'],
            'item_name': ['Sample Item 1', 'Sample Item 2'],
            'hs_code': ['8471.3000', '8517.6200'],
            'product_description': ['Sample product description 1', 'Sample product description 2'],
            'default_uom': ['PCS', 'PCS'],
            'default_rate': ['18', '18'],
            'transaction_type': [transaction_type_name, transaction_type_name],
            'sro_schedule_no': ['', ''],
            'sro_item_serial_no': ['', '']
        }

        df = pd.DataFrame(template_data)

        # Get all transaction types for reference sheet
        all_transaction_types = db.query(FBRTransactionType).order_by(FBRTransactionType.code).all()
        transaction_types_data = {
            'Code': [tt.code for tt in all_transaction_types],
            'Name': [tt.name.strip() for tt in all_transaction_types]  # Trim spaces for clean display
        }
        df_transaction_types = pd.DataFrame(transaction_types_data)

        # Get all UOMs for reference sheet
        all_uoms = db.query(FBRUOM).order_by(FBRUOM.code).all()
        uoms_data = {
            'Code': [uom.code for uom in all_uoms],
            'Name': [uom.name.strip() for uom in all_uoms]
        }
        df_uoms = pd.DataFrame(uoms_data)

        # Create Excel file in memory with multiple sheets
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write main template
            df.to_excel(writer, index=False, sheet_name='Saved Items')

            # Write transaction types reference
            df_transaction_types.to_excel(writer, index=False, sheet_name='Transaction Types')

            # Write UOMs reference
            df_uoms.to_excel(writer, index=False, sheet_name='UOMs')

            # Format main sheet
            worksheet = writer.sheets['Saved Items']
            worksheet.column_dimensions['A'].width = 15
            worksheet.column_dimensions['B'].width = 25
            worksheet.column_dimensions['C'].width = 15
            worksheet.column_dimensions['D'].width = 40
            worksheet.column_dimensions['E'].width = 15
            worksheet.column_dimensions['F'].width = 15
            worksheet.column_dimensions['G'].width = 30
            worksheet.column_dimensions['H'].width = 20
            worksheet.column_dimensions['I'].width = 20

            # Format transaction types sheet
            worksheet_tt = writer.sheets['Transaction Types']
            worksheet_tt.column_dimensions['A'].width = 10
            worksheet_tt.column_dimensions['B'].width = 50

            # Format UOMs sheet
            worksheet_uom = writer.sheets['UOMs']
            worksheet_uom.column_dimensions['A'].width = 10
            worksheet_uom.column_dimensions['B'].width = 50

        output.seek(0)

        logger.info(f"User {user_id} downloaded saved items template")

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=saved_items_template.xlsx"
            }
        )

    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate template: {str(e)}"
        )


@router.post("/saved-products/upload")
async def upload_saved_products(
    file: UploadFile = File(...),
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Upload Excel file with saved items data.
    Parses the file and creates saved items in bulk.

    Args:
        file: Excel file with saved items data

    Returns:
        Summary of upload results (success count, errors)
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Please upload an Excel file (.xlsx or .xls)"
            )

        # Read Excel file
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Validate required columns
        required_columns = [
            'item_code', 'item_name', 'hs_code', 'product_description',
            'default_uom', 'default_rate', 'transaction_type'
        ]

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )

        # Pre-load all master data for faster lookups (optimization)
        all_uoms = {uom.code: uom for uom in db.query(FBRUOM).all()}
        all_uoms_by_name = {uom.name.strip().lower(): uom for uom in all_uoms.values()}

        all_transaction_types = {tt.code: tt for tt in db.query(FBRTransactionType).all()}
        all_transaction_types_by_name = {tt.name.strip().lower(): tt for tt in all_transaction_types.values()}

        all_hs_codes = {hs.code: hs for hs in db.query(FBRHSCode).all()}

        # Process each row
        success_count = 0
        error_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row['item_code']) or str(row['item_code']).strip() == '':
                    continue

                # Validate required fields
                # Cleanly convert Excel values — Pandas reads numbers as float (e.g. 19 -> 19.0)
                def _clean_excel_str(raw):
                    val = raw
                    if isinstance(val, float) and val == int(val):
                        val = int(val)
                    return str(val).strip()

                item_code = _clean_excel_str(row['item_code'])
                item_name = _clean_excel_str(row['item_name'])
                hs_code_input = _clean_excel_str(row['hs_code'])
                product_description = _clean_excel_str(row['product_description'])
                default_uom_input = _clean_excel_str(row['default_uom'])
                default_rate = _clean_excel_str(row['default_rate'])
                transaction_type_input = _clean_excel_str(row['transaction_type'])

                if not all([item_code, item_name, hs_code_input, product_description, default_uom_input, default_rate, transaction_type_input]):
                    errors.append(f"Row {index + 2}: Missing required fields")
                    error_count += 1
                    continue

                # Format HS code: normalize to 8 digits without dots (to match manual system)
                hs_code_cleaned = hs_code_input.replace('.', '').replace(' ', '')

                # Pad to 8 digits if needed
                if len(hs_code_cleaned) == 7:
                    hs_code_cleaned = hs_code_cleaned + '0'
                elif len(hs_code_cleaned) == 6:
                    hs_code_cleaned = hs_code_cleaned + '00'
                elif len(hs_code_cleaned) < 6:
                    errors.append(f"Row {index + 2}: Invalid HS code '{hs_code_input}' - must be at least 6 digits")
                    error_count += 1
                    continue
                elif len(hs_code_cleaned) > 8:
                    # Truncate to 8 digits if longer
                    hs_code_cleaned = hs_code_cleaned[:8]

                # Format with dot in middle: 1234.1234 (matches manual system and FBR database)
                hs_code_formatted = f"{hs_code_cleaned[:4]}.{hs_code_cleaned[4:]}"

                # Store WITH dots (to match manual system)
                hs_code_to_store = hs_code_formatted

                # For FBR validation, use the same format
                hs_code_for_validation = hs_code_formatted

                logger.debug(f"Row {index + 2}: HS Code input='{hs_code_input}' -> formatted='{hs_code_formatted}'")

                # Store exactly what's in the Excel file (no validation or conversion)
                default_uom_to_store = default_uom_input
                transaction_type_to_store = transaction_type_input

                # Validate HS code - use cached data
                fbr_hs_code = all_hs_codes.get(hs_code_for_validation)

                fbr_validated = False

                if not fbr_hs_code:
                    logger.warning(f"Row {index + 2}: HS Code validation failed - input='{hs_code_input}', searched='{hs_code_for_validation}'")
                else:
                    fbr_validated = True
                    logger.debug(f"Row {index + 2}: HS Code validated successfully - '{hs_code_for_validation}'")

                # Get optional fields
                sro_schedule_no = None
                sro_item_serial_no = None

                if 'sro_schedule_no' in df.columns and not pd.isna(row['sro_schedule_no']):
                    val = row['sro_schedule_no']
                    if isinstance(val, float) and val == int(val):
                        val = int(val)
                    sro_schedule_no = str(val).strip()

                if 'sro_item_serial_no' in df.columns and not pd.isna(row['sro_item_serial_no']):
                    sro_item_serial_no = _clean_excel_str(row['sro_item_serial_no'])

                # Create saved product
                new_product = UserSavedProduct(
                    user_id=UUID(user_id),
                    item_code=item_code,
                    item_name=item_name,
                    hs_code=hs_code_to_store,  # Store with dots (1234.5678 format)
                    product_description=product_description,
                    default_uom=default_uom_to_store,  # Store exactly what's in Excel
                    default_rate=default_rate,
                    default_sale_type=transaction_type_to_store,  # Store exactly what's in Excel
                    transaction_type=transaction_type_to_store,  # Store exactly what's in Excel
                    sro_schedule_no=sro_schedule_no,
                    sro_item_serial_no=sro_item_serial_no,
                    is_active=1,
                    fbr_validated=fbr_validated
                )

                db.add(new_product)
                success_count += 1

            except Exception as row_error:
                logger.error(f"Error processing row {index + 2}: {str(row_error)}")
                errors.append(f"Row {index + 2}: {str(row_error)}")
                error_count += 1

        # Commit all successful items
        if success_count > 0:
            db.commit()

        logger.info(f"User {user_id} uploaded {success_count} saved items with {error_count} errors")

        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors[:10],  # Return first 10 errors
            "total_errors": len(errors)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading saved products: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload saved products: {str(e)}"
        )
