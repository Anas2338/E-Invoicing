"""
Excel upload API endpoints.
"""
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
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
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_automation_db)],
    main_db: Annotated[Session, Depends(get_db)],
    user_id: str = Depends(require_automation_access)
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

    # Initialize services
    excel_service = ExcelService(db)
    automation_service = AutomationService(db)

    # Note: Concurrent upload check removed to allow multiple uploads per user

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

        # Store invoices in database
        stored_invoices = automation_service.store_invoices_from_excel(
            user_id=user_uuid,
            session_id=upload_session.id,
            invoices=invoices
        )

        # Check current time for expiration check
        from datetime import datetime
        from src.services.fbr_client import FBRClient
        from src.schemas.fbr import FBREnvironment
        from src.models.user import User

        now = datetime.utcnow()
        current_date = now.date()
        current_time = now.time()

        # Get user's FBR credentials from main database
        user = main_db.get(User, user_uuid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if user has FBR credentials configured
        user_fbr_token = user.fbr_sandbox_token if user.fbr_environment == "SANDBOX" else user.fbr_production_token
        if not user_fbr_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FBR credentials not configured. Please configure your FBR {user.fbr_environment} credentials in settings."
            )

        # Process each invoice: check expiration first, then validate locally, then validate with FBR
        validation_service = ValidationService()
        fbr_client = FBRClient()

        validated_count = 0
        failed_count = 0
        expired_count = 0

        try:
            for invoice in stored_invoices:
                # Check if invoice is already expired
                is_expired = False
                if invoice.scheduled_date < current_date:
                    is_expired = True
                elif invoice.scheduled_date == current_date and invoice.scheduled_time < current_time:
                    is_expired = True

                if is_expired:
                    # Mark as expired, skip validation
                    invoice.status = AutomationInvoiceStatus.EXPIRED
                    invoice.validation_errors = "Scheduled time is in the past"
                    expired_count += 1
                else:
                    # Step 1: Local validation
                    is_valid_locally, validation_errors = validation_service.validate_invoice_locally(invoice.invoice_data)

                    if not is_valid_locally:
                        # Mark as PENDING with validation errors (user can retry)
                        invoice.status = AutomationInvoiceStatus.PENDING
                        invoice.validation_errors = f"Validation failed: {str(validation_errors)}"
                        failed_count += 1
                    else:
                        # Step 2: FBR validation (only if local validation passed)
                        try:
                            # Use user's FBR environment preference
                            environment = FBREnvironment.SANDBOX if user.fbr_environment == "SANDBOX" else FBREnvironment.PRODUCTION

                            # DRY RUN MODE - Simulate FBR validation without actual API call
                            if settings.dry_run:
                                import random
                                import time

                                logger.info(f"[DRY RUN] Simulating FBR validation for invoice {invoice.invoice_number}")

                                # Simulate 98% validation success rate (2% random failures for testing)
                                is_valid_fbr = random.random() < 0.98

                                if is_valid_fbr:
                                    fbr_response = {
                                        "dated": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "validationResponse": {
                                            "statusCode": "00",
                                            "status": "Valid",
                                            "error": "",
                                            "invoiceStatuses": [{
                                                "itemSNo": "1",
                                                "statusCode": "00",
                                                "status": "Valid",
                                                "invoiceNo": "",
                                                "errorCode": "",
                                                "error": ""
                                            }]
                                        }
                                    }
                                    reference_number = None
                                    logger.info(f"[DRY RUN] Simulated validation SUCCESS for invoice {invoice.invoice_number}")
                                else:
                                    # Simulate random validation error
                                    error_scenarios = [
                                        {"code": "0052", "msg": "HS Code does not match with provided sale type"},
                                        {"code": "0078", "msg": "Valid Item Sr. No. is mandatory where SRO/Schedule No. is provided"}
                                    ]
                                    error = random.choice(error_scenarios)
                                    fbr_response = {
                                        "dated": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "validationResponse": {
                                            "statusCode": "01",
                                            "status": "Invalid",
                                            "error": f"[{error['code']}] {error['msg']}",
                                            "invoiceStatuses": []
                                        }
                                    }
                                    reference_number = None
                                    logger.warning(f"[DRY RUN] Simulated validation FAILURE for invoice {invoice.invoice_number}: {error['msg']}")
                            else:
                                # REAL MODE - Actual FBR API call
                                is_valid_fbr, fbr_response, reference_number = await fbr_client.validate_invoice_with_user_credentials(
                                    invoice_data=invoice.invoice_data,
                                    environment=environment,
                                    fbr_token=user_fbr_token
                                )

                            if is_valid_fbr:
                                # Mark as validated and ready for posting
                                invoice.status = AutomationInvoiceStatus.VALIDATED
                                invoice.fbr_response = fbr_response
                                validated_count += 1
                            else:
                                # Mark as PENDING with FBR validation errors (user can retry)
                                invoice.status = AutomationInvoiceStatus.PENDING
                                invoice.validation_errors = f"FBR validation failed: {str(fbr_response)}"
                                invoice.fbr_response = fbr_response
                                failed_count += 1

                        except Exception as e:
                            # FBR API call failed (network error, timeout, etc.) - mark as PENDING
                            invoice.status = AutomationInvoiceStatus.PENDING
                            invoice.validation_errors = f"FBR validation error: {str(e)}"
                            failed_count += 1

                db.add(invoice)

            db.commit()
        finally:
            # Always close the FBR client
            await fbr_client.client.aclose()

        # Update session status to completed
        upload_session.processing_status = "completed"
        upload_session.processed_rows = len(invoices)
        db.add(upload_session)
        db.commit()

        # Build detailed response message
        message_parts = [f"Excel file uploaded and validated with FBR."]
        if validated_count > 0:
            message_parts.append(f"{validated_count} invoice(s) validated and ready for posting.")
        if failed_count > 0:
            message_parts.append(f"{failed_count} invoice(s) failed validation.")
        if expired_count > 0:
            message_parts.append(f"{expired_count} invoice(s) expired (scheduled time in the past).")

        return ExcelUploadResponse(
            session_id=upload_session.id,
            total_rows=len(invoices),
            message=" ".join(message_parts)
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
