"""
Excel upload API endpoints.
"""
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from uuid import UUID
from typing import Annotated
from io import BytesIO
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from src.database.session import get_automation_db, get_db
from src.schemas.excel import ExcelUploadResponse, ExcelUploadStatusResponse
from src.services.excel_service import ExcelService
from src.services.automation_service import AutomationService
from src.services.validation_service import ValidationService
from src.services.background_validation_service import BackgroundValidationService
from src.models.automation_invoice import AutomationInvoiceStatus
from src.utils.excel_validator import ExcelValidator
from src.utils.secure_file_validator import SecureFileValidator
from src.api.middleware.auth_middleware import require_authentication
from src.middleware.rbac import require_automation_access
from src.config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Rate limiter: 5 uploads per hour per IP
limiter = Limiter(key_func=get_remote_address)


@router.get("/template/download")
async def download_template(
    db: Annotated[Session, Depends(get_automation_db)],
    user_id: str = Depends(require_automation_access)
):
    """
    Download Excel template with predefined headers.

    Returns:
        Excel file as streaming response
    """
    excel_service = ExcelService(db)
    template_file = excel_service.generate_excel_template()

    return StreamingResponse(
        template_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=invoice_template.xlsx"
        }
    )


@router.post("/excel/upload", response_model=ExcelUploadResponse)
@limiter.limit("5/hour")
async def upload_excel(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_automation_db)],
    main_db: Annotated[Session, Depends(get_db)],
    user_id: str = Depends(require_automation_access)
):
    """
    Upload filled Excel file for bulk invoice scheduling.

    Rate limit: 5 uploads per hour per IP address.
    File is parsed in memory and data stored directly in database.
    FBR validation happens in background - use /excel/status/{session_id} to track progress.

    Args:
        background_tasks: FastAPI background tasks
        file: Excel file upload
        db: Database session
        main_db: Main database session
        user_id: Authenticated user ID

    Returns:
        Upload response with session ID and total rows

    Raises:
        HTTPException: If validation fails or concurrent upload detected
    """
    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Initialize services
    excel_service = ExcelService(db)
    automation_service = AutomationService(db)

    try:
        # Read file content into memory
        file_content = await file.read()
        file_bytes = BytesIO(file_content)

        # SECURITY: Comprehensive file validation
        # Validates: extension, size, magic bytes, zip bombs, Excel structure, malicious content
        is_valid, error_message = SecureFileValidator.validate_file_comprehensive(
            file_bytes=file_bytes,
            filename=file.filename or ""
        )

        if not is_valid:
            logger.warning(f"File validation failed for user {user_id}: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        # Reset BytesIO position after validation
        file_bytes.seek(0)

        # Additional business logic validation (column structure, data format)
        is_valid, errors = ExcelValidator.validate_excel_file(file_bytes)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Excel file structure: {'; '.join(errors)}"
            )

        # Reset BytesIO position after validation
        file_bytes.seek(0)

        # Parse Excel file (in-memory)
        try:
            invoices = excel_service.parse_excel_file(file_bytes, user_uuid, main_db)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        if not invoices:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Excel file contains no valid invoice data"
            )

        # Create upload session (no file saving - data stored in DB only)
        upload_session = automation_service.create_upload_session(
            user_id=user_uuid,
            original_filename=file.filename,
            total_rows=len(invoices),
            file_path=None  # Not saving files to disk
        )

        # Store invoices in database with PENDING status (validation happens in background)
        stored_invoices = automation_service.store_invoices_from_excel(
            user_id=user_uuid,
            session_id=upload_session.id,
            invoices=invoices
        )

        # Get user's FBR credentials from main database
        from src.models.user import User
        user = main_db.get(User, user_uuid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get user's FBR production token
        user_fbr_token = user.fbr_production_token
        if not user_fbr_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FBR credentials not configured. Please configure your FBR production credentials in settings."
            )

        # Schedule background validation task (Production)
        background_tasks.add_task(
            BackgroundValidationService.validate_invoices_background,
            session_id=upload_session.id,
            user_id=user_uuid,
            fbr_token=user_fbr_token
        )

        logger.info(f"Excel upload successful for session {upload_session.id}. Background validation scheduled.")

        return ExcelUploadResponse(
            session_id=upload_session.id,
            total_rows=len(invoices),
            message=f"Excel file uploaded successfully with {len(invoices)} invoice(s). FBR validation is running in the background. Use the status endpoint to track progress."
        )

    except HTTPException as e:
        # Update session status to failed on HTTP exceptions
        try:
            if 'upload_session' in locals():
                upload_session.processing_status = "failed"
                upload_session.error_message = str(e.detail)
                db.add(upload_session)
                db.commit()
        except:
            pass  # Don't fail the error response if status update fails
        raise
    except Exception as e:
        # Update session status to failed on unexpected errors
        try:
            if 'upload_session' in locals():
                upload_session.processing_status = "failed"
                upload_session.error_message = str(e)
                db.add(upload_session)
                db.commit()
        except:
            pass  # Don't fail the error response if status update fails

        # Provide user-friendly error messages for common issues
        error_message = str(e)

        # Handle duplicate invoice number error
        if "duplicate key value violates unique constraint" in error_message and "idx_unique_invoice_per_user" in error_message:
            # Extract invoice number from error message if possible
            import re
            match = re.search(r'invoice_number\)=\([^,]+,\s*([^)]+)\)', error_message)
            invoice_num = match.group(1) if match else "one or more invoices"

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate invoice number detected: {invoice_num} already exists in your automation invoices. Please use unique invoice numbers or delete the existing invoice from the automation dashboard before uploading again."
            )

        # Handle other database errors
        if "psycopg2" in error_message or "sqlalchemy" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while processing your upload. Please try again or contact support if the issue persists."
            )

        # Generic error for other cases
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing upload: {str(e)}"
        )


@router.get("/excel/status/{session_id}", response_model=ExcelUploadStatusResponse)
async def get_upload_status(
    session_id: UUID,
    db: Annotated[Session, Depends(get_automation_db)],
    user_id: str = Depends(require_automation_access)
):
    """
    Check upload processing status with detailed validation statistics.

    Args:
        session_id: Upload session UUID
        db: Database session
        user_id: Authenticated user ID

    Returns:
        Upload status response with validation statistics

    Raises:
        HTTPException: If session not found or access denied
    """
    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Get upload session
    from src.models.excel_upload_session import ExcelUploadSession
    upload_session = db.get(ExcelUploadSession, session_id)
    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )

    # Verify user owns this session
    if upload_session.user_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get validation statistics by querying invoices
    from sqlmodel import select, func
    from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus

    # Count invoices by status
    validated_count = db.exec(
        select(func.count(AutomationInvoice.id)).where(
            AutomationInvoice.excel_upload_session_id == session_id,
            AutomationInvoice.status == AutomationInvoiceStatus.VALIDATED
        )
    ).one()

    failed_count = db.exec(
        select(func.count(AutomationInvoice.id)).where(
            AutomationInvoice.excel_upload_session_id == session_id,
            AutomationInvoice.status == AutomationInvoiceStatus.FAILED
        )
    ).one()

    expired_count = db.exec(
        select(func.count(AutomationInvoice.id)).where(
            AutomationInvoice.excel_upload_session_id == session_id,
            AutomationInvoice.status == AutomationInvoiceStatus.EXPIRED
        )
    ).one()

    pending_count = db.exec(
        select(func.count(AutomationInvoice.id)).where(
            AutomationInvoice.excel_upload_session_id == session_id,
            AutomationInvoice.status == AutomationInvoiceStatus.PENDING
        )
    ).one()

    # Calculate progress percentage
    progress_percentage = 0.0
    if upload_session.total_rows > 0:
        progress_percentage = (upload_session.processed_rows / upload_session.total_rows) * 100

    return ExcelUploadStatusResponse(
        session_id=upload_session.id,
        status=upload_session.processing_status,
        processed_rows=upload_session.processed_rows,
        total_rows=upload_session.total_rows,
        error_message=upload_session.error_message,
        validated_count=validated_count,
        failed_count=failed_count,
        expired_count=expired_count,
        pending_count=pending_count,
        progress_percentage=round(progress_percentage, 2)
    )
