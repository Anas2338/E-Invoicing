"""
Excel upload API endpoints.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from uuid import UUID
from typing import Annotated
from io import BytesIO
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.database.session import get_db
from src.schemas.excel import ExcelUploadResponse, ExcelUploadStatusResponse
from src.services.excel_service import ExcelService
from src.services.automation_service import AutomationService
from src.utils.excel_validator import ExcelValidator
from src.api.middleware.auth_middleware import require_authentication

router = APIRouter()

# Rate limiter: 5 uploads per hour per IP
limiter = Limiter(key_func=get_remote_address)


@router.get("/template/download")
async def download_template(
    db: Annotated[Session, Depends(get_db)]
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
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    user_id: str = Depends(require_authentication)
):
    """
    Upload filled Excel file for bulk invoice scheduling.

    Rate limit: 5 uploads per hour per IP address.
    File is parsed in memory and data stored directly in database.

    Args:
        file: Excel file upload
        db: Database session
        user_id: Authenticated user ID

    Returns:
        Upload response with session ID and total rows

    Raises:
        HTTPException: If validation fails or concurrent upload detected
    """
    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Validate file extension
    if not file.filename or not ExcelValidator.validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only .xlsx files are allowed."
        )

    # Initialize services
    excel_service = ExcelService(db)
    automation_service = AutomationService(db)

    # Check for concurrent upload
    existing_session = excel_service.check_concurrent_upload(user_uuid)
    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Previous upload still processing. Please wait for it to complete."
        )

    try:
        # Read file content into memory
        file_content = await file.read()
        file_bytes = BytesIO(file_content)

        # Validate file size (in-memory)
        try:
            ExcelValidator.validate_file_size(file_bytes)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Reset BytesIO position after size validation
        file_bytes.seek(0)

        # Validate Excel structure (in-memory)
        is_valid, errors = ExcelValidator.validate_excel_file(file_bytes)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Excel file: {'; '.join(errors)}"
            )

        # Reset BytesIO position after validation
        file_bytes.seek(0)

        # Parse Excel file (in-memory)
        try:
            invoices = excel_service.parse_excel_file(file_bytes)
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

        # Create upload session (no file_path - in-memory parsing)
        upload_session = automation_service.create_upload_session(
            user_id=user_uuid,
            original_filename=file.filename,
            total_rows=len(invoices),
            file_path=None  # No file storage
        )

        # Store invoices in database
        automation_service.store_invoices_from_excel(
            user_id=user_uuid,
            session_id=upload_session.id,
            invoices=invoices
        )

        # Mark past invoices as expired
        automation_service.mark_past_invoices_as_expired(
            user_id=user_uuid,
            session_id=upload_session.id
        )

        # Update session status to completed
        upload_session.processing_status = "completed"
        upload_session.processed_rows = len(invoices)
        db.add(upload_session)
        db.commit()

        return ExcelUploadResponse(
            session_id=upload_session.id,
            total_rows=len(invoices),
            message=f"Excel file uploaded successfully. {len(invoices)} invoices scheduled for processing."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing upload: {str(e)}"
        )


@router.get("/excel/status/{session_id}", response_model=ExcelUploadStatusResponse)
async def get_upload_status(
    session_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user_id: str = Depends(require_authentication)
):
    """
    Check upload processing status.

    Args:
        session_id: Upload session UUID
        db: Database session
        user_id: Authenticated user ID

    Returns:
        Upload status response

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

    return ExcelUploadStatusResponse(
        session_id=upload_session.id,
        status=upload_session.processing_status,
        processed_rows=upload_session.processed_rows,
        total_rows=upload_session.total_rows,
        error_message=upload_session.error_message
    )
