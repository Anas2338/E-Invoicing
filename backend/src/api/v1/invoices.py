from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional, Annotated
from uuid import UUID
from datetime import date
from io import BytesIO
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.database.session import get_db
from src.services.invoice_service import InvoiceService, get_user_environment_filter
from src.services.fbr_service import fbr_service
from src.services.auto_posting_service import AutoPostingService
from src.services.pdf_service import PDFService
from src.utils.manual_excel_helper import generate_manual_excel_template, parse_excel_for_manual_invoice
from src.schemas.invoice import (
    InvoiceCreate, InvoiceResponse, InvoiceUpdate, InvoiceListResponse,
    InvoiceFilter, UnifiedInvoiceListResponse
)
from src.schemas.auto_posting import ManualPostingRequest, ManualPostingResponse, PostingStatusResponse
from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session, get_pagination_params
from src.models.user import User
from src.models.invoice import Invoice, InvoiceStatus
from src.models.fbr_response import FBRResponse
from src.utils.rate_limits import RateLimits
from src.utils.secure_file_validator import SecureFileValidator
from src.utils.excel_validator import ExcelValidator
from src.services.bulk_operation_service import BulkOperationService
from src.schemas.bulk_operation import (
    BulkValidateRequest,
    BulkPostRequest,
    BulkOperationResponse,
    BulkOperationStatusResponse,
    BulkOperationError,
    ActiveBulkTasksResponse,
)
from src.models.bulk_operation import (
    BulkOperationTask,
    BulkOperationType,
    BulkOperationStatus,
)


logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/", response_model=InvoiceResponse)
@limiter.limit(RateLimits.INVOICE_CREATE)
def create_invoice(
    request: Request,
    invoice_create: InvoiceCreate,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Create a new invoice in draft status.
    Rate limit: 30 invoices per hour.
    """
    service = InvoiceService()

    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Create the invoice
    db_invoice = service.create_invoice(db, invoice_create, user_uuid)

    # Convert to response model
    return InvoiceResponse(
        id=db_invoice.id,
        external_id=db_invoice.external_id,
        user_id=db_invoice.user_id,
        invoice_type=db_invoice.invoice_type,
        invoice_date=db_invoice.invoice_date,
        transaction_type_id=db_invoice.transaction_type_id,
        seller_ntn_cnic=db_invoice.seller_ntn_cnic,
        seller_business_name=db_invoice.seller_business_name,
        seller_province=db_invoice.seller_province,
        seller_address=db_invoice.seller_address,
        buyer_ntn_cnic=db_invoice.buyer_ntn_cnic,
        buyer_business_name=db_invoice.buyer_business_name,
        buyer_province=db_invoice.buyer_province,
        buyer_address=db_invoice.buyer_address,
        buyer_registration_type=db_invoice.buyer_registration_type,
        invoice_ref_no=db_invoice.invoice_ref_no,
        scenario_id=db_invoice.scenario_id,
        items=db_invoice.items,
        environment=db_invoice.environment,
        status=db_invoice.status,
        created_at=db_invoice.created_at,
        updated_at=db_invoice.updated_at,
        validated_at=db_invoice.validated_at,
        posted_at=db_invoice.posted_at,
        fbr_reference_number=db_invoice.fbr_reference_number,
        validation_errors=db_invoice.validation_errors,
    )


@router.get("/excel/template/download")
def download_manual_excel_template(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Download Excel template for manual invoice upload.
    Template includes dropdown validations on invoice_type, buyer_province,
    buyer_registration_type, and income_tax columns — values are fetched
    from FBR master data.
    """
    from src.models.fbr_master_data import FBRInvoiceType, FBRProvince

    # Fetch master data for dropdowns
    invoice_types = [
        t.name for t in db.query(FBRInvoiceType).all()
    ] or ["Sale Invoice", "Debit Note"]

    provinces = [
        p.name for p in db.query(FBRProvince).all()
    ] or [
        "PUNJAB", "SINDH", "KPK", "BALOCHISTAN",
        "ISLAMABAD", "GILGIT BALTISTAN", "AZAD JAMMU KASHMIR"
    ]

    template_file = generate_manual_excel_template(
        invoice_types=invoice_types,
        provinces=provinces,
    )

    return StreamingResponse(
        template_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=bulk_invoice_template.xlsx"
        }
    )


@router.post("/excel/upload")
@limiter.limit("5/hour")
async def upload_manual_excel(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Upload Excel file to create manual invoices in bulk.
    Each row creates a draft invoice directly in the main database.
    Validates invoice_date is today or previous date (no future dates allowed).

    Rate limit: 5 uploads per hour.
    """
    user_uuid = UUID(user_id)

    # Read file content
    file_content = await file.read()
    file_bytes = BytesIO(file_content)

    # Security validation
    is_valid, error_message = SecureFileValidator.validate_file_comprehensive(
        file_bytes=file_bytes,
        filename=file.filename or ""
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    file_bytes.seek(0)

    # Manual Excel structure validation (uses MANUAL_REQUIRED_COLUMNS)
    is_valid, errors = ExcelValidator.validate_manual_excel_file(file_bytes)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Excel file structure: {'; '.join(errors)}"
        )

    file_bytes.seek(0)

    # Parse Excel file for manual invoices
    try:
        invoice_data_list = parse_excel_for_manual_invoice(file_bytes, user_uuid, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not invoice_data_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Excel file contains no valid invoice data"
        )

    # Create invoices in the main database
    invoice_service = InvoiceService()
    created_invoices = []
    errors_list = []

    for invoice_data in invoice_data_list:
        try:
            # Convert dict to InvoiceCreate schema
            invoice_create = InvoiceCreate(**invoice_data)
            db_invoice = invoice_service.create_invoice(db, invoice_create, user_uuid)
            created_invoices.append({
                "id": str(db_invoice.id),
                "external_id": db_invoice.external_id,
                "invoice_type": db_invoice.invoice_type,
                "status": db_invoice.status.value if hasattr(db_invoice.status, 'value') else str(db_invoice.status),
            })
        except Exception as e:
            errors_list.append({
                "invoice_number": invoice_data.get("external_id", "unknown"),
                "error": str(e)
            })

    return {
        "success": True,
        "message": f"Created {len(created_invoices)} invoice(s) from Excel file.",
        "total_created": len(created_invoices),
        "total_failed": len(errors_list),
        "invoices": created_invoices,
        "errors": errors_list if errors_list else None
    }


@router.get("/unified-history", response_model=UnifiedInvoiceListResponse)
def get_unified_invoice_history(
    request: Request,
    user_id: str = Depends(require_authentication),
    source: Optional[str] = Query(None, description="Filter by source: manual, automation"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[date] = Query(None, description="Filter by date from"),
    date_to: Optional[date] = Query(None, description="Filter by date to"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100000, ge=1, description="Items per page"),
    db = Depends(get_database_session)
):
    """
    Get unified list of manual and automated invoices with source indicators.

    Combines invoices from both the manual invoice system and automation system
    into a single paginated list with clear source indicators.
    """
    service = InvoiceService()

    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Determine environment filter based on user's available FBR tokens
    user = db.get(User, user_uuid)
    environment_filter = get_user_environment_filter(user) if user else None

    # Get unified invoice history
    invoices, total = service.get_unified_invoice_history(
        db=db,
        user_id=user_uuid,
        source=source,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        environment=environment_filter
    )

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return UnifiedInvoiceListResponse(
        invoices=invoices,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/buyers-from-history")
def get_buyers_from_invoice_history(
    request: Request,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    search: Optional[str] = Query(None, description="Search buyer by name or NTN/CNIC")
):
    """
    Get unique buyers from user's invoice history.
    Returns distinct buyer information from all invoices created by the user.

    This eliminates the need for a separate saved_buyers table by extracting
    buyer data directly from existing invoices.
    """
    try:
        user_uuid = UUID(user_id)

        # Determine environment filter based on user's available FBR tokens
        user = db.get(User, user_uuid)
        env_filter = get_user_environment_filter(user) if user else None

        # Get all invoices for this user with buyer information
        from sqlmodel import select

        statement = select(Invoice).where(
            Invoice.user_id == user_uuid,
            Invoice.is_deleted == False,
            Invoice.buyer_business_name.isnot(None),
            Invoice.buyer_business_name != ''
        )

        # Apply environment filter
        if env_filter:
            statement = statement.where(Invoice.environment == env_filter)

        # Apply search filter if provided
        if search and search.strip():
            search_term = f"%{search.strip().lower()}%"
            statement = statement.where(
                (Invoice.buyer_business_name.ilike(search_term)) |
                (Invoice.buyer_ntn_cnic.ilike(search_term))
            )

        invoices = db.exec(statement).all()

        # Extract unique buyers manually
        buyers_dict = {}
        for invoice in invoices:
            # Create a unique key based on buyer information
            key = (
                invoice.buyer_ntn_cnic or "",
                invoice.buyer_business_name or "",
                invoice.buyer_province or "",
                invoice.buyer_address or "",
                invoice.buyer_registration_type or "Registered"
            )

            # Keep the most recent occurrence
            if key not in buyers_dict or invoice.created_at > buyers_dict[key]['last_used']:
                buyers_dict[key] = {
                    "buyer_ntn_cnic": invoice.buyer_ntn_cnic or "",
                    "buyer_business_name": invoice.buyer_business_name or "",
                    "buyer_province": invoice.buyer_province or "",
                    "buyer_address": invoice.buyer_address or "",
                    "buyer_registration_type": invoice.buyer_registration_type or "Registered",
                    "last_used": invoice.created_at
                }

        # Convert to list and sort by most recent
        result = sorted(
            buyers_dict.values(),
            key=lambda x: x['last_used'],
            reverse=True
        )[:50]  # Limit to 50 most recent

        # Convert datetime to ISO format
        for buyer in result:
            buyer['last_used'] = buyer['last_used'].isoformat() if buyer['last_used'] else None

        logger.info(f"Retrieved {len(result)} unique buyers from invoice history for user {user_id}")

        return result

    except Exception as e:
        logger.error(f"Error fetching buyers from invoice history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch buyers from history: {str(e)}"
        )


@router.post("/bulk-pdf")
async def generate_bulk_pdf(
    request: Request,
    invoice_ids: List[UUID],
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Generate a single PDF containing multiple invoices.

    Args:
        invoice_ids: List of invoice IDs to include in the PDF

    Returns:
        StreamingResponse with PDF file
    """
    user_uuid = UUID(user_id)

    if not invoice_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No invoice IDs provided"
        )

    if len(invoice_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate PDF for more than 50 invoices at once (got {len(invoice_ids)})"
        )

    # Fetch all invoices and verify ownership
    invoices = []
    for invoice_id in invoice_ids:
        invoice = db.get(Invoice, invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice {invoice_id} not found"
            )

        if invoice.user_id != user_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to access invoice {invoice_id}"
            )

        invoices.append(invoice)

    # Generate bulk PDF
    pdf_service = PDFService()
    try:
        pdf_bytes = pdf_service.generate_batch_pdf(invoices)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to generate bulk PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF"
        )

    # Generate filename with timestamp
    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"invoices_bulk_{timestamp}.pdf"

    # Return streaming response
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get an invoice by its ID.
    """
    service = InvoiceService()

    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Get the invoice
    db_invoice = service.get_invoice_by_id(db, invoice_id, user_uuid)

    if not db_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Normalize TRANSFERRED to VALIDATED (transferred invoices are validated)
    display_status = db_invoice.status
    if display_status == InvoiceStatus.TRANSFERRED:
        display_status = InvoiceStatus.VALIDATED

    # Convert to response model
    return InvoiceResponse(
        id=db_invoice.id,
        external_id=db_invoice.external_id,
        user_id=db_invoice.user_id,
        invoice_type=db_invoice.invoice_type,
        invoice_date=db_invoice.invoice_date,
        transaction_type_id=db_invoice.transaction_type_id,
        seller_ntn_cnic=db_invoice.seller_ntn_cnic,
        seller_business_name=db_invoice.seller_business_name,
        seller_province=db_invoice.seller_province,
        seller_address=db_invoice.seller_address,
        buyer_ntn_cnic=db_invoice.buyer_ntn_cnic,
        buyer_business_name=db_invoice.buyer_business_name,
        buyer_province=db_invoice.buyer_province,
        buyer_address=db_invoice.buyer_address,
        buyer_registration_type=db_invoice.buyer_registration_type,
        invoice_ref_no=db_invoice.invoice_ref_no,
        scenario_id=db_invoice.scenario_id,
        items=db_invoice.items,
        environment=db_invoice.environment,
        status=display_status,
        created_at=db_invoice.created_at,
        updated_at=db_invoice.updated_at,
        validated_at=db_invoice.validated_at,
        posted_at=db_invoice.posted_at,
        fbr_reference_number=db_invoice.fbr_reference_number,
        validation_errors=db_invoice.validation_errors,
        # Automation source fields omitted
    )


@router.get("/{invoice_id}/adjacent")
def get_adjacent_invoice(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get the previous and next invoice IDs for navigation.
    """
    service = InvoiceService()
    user_uuid = UUID(user_id)
    result = service.get_adjacent_invoices(db, invoice_id, user_uuid)
    return result


@router.get("/", response_model=InvoiceListResponse)
def list_invoices(
    filters: InvoiceFilter = Depends(),
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    List invoices with optional filtering and pagination.
    """
    service = InvoiceService()

    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Determine environment filter based on user's available FBR tokens
    user = db.get(User, user_uuid)
    environment_override = get_user_environment_filter(user) if user else None

    # Get invoices with filters
    invoices = service.get_invoices_by_user(db, user_uuid, filters, environment_override)

    # Get total count for pagination
    total_count = service.get_invoice_count(db, user_uuid, filters, environment_override)

    # Calculate pagination info
    total_pages = (total_count + filters.size - 1) // filters.size

    # Convert to response models (normalizing TRANSFERRED to VALIDATED)
    invoice_responses = [
        InvoiceResponse(
            id=inv.id,
            external_id=inv.external_id,
            user_id=inv.user_id,
            invoice_type=inv.invoice_type,
            invoice_date=inv.invoice_date,
            transaction_type_id=inv.transaction_type_id,
            seller_ntn_cnic=inv.seller_ntn_cnic,
            seller_business_name=inv.seller_business_name,
            seller_province=inv.seller_province,
            seller_address=inv.seller_address,
            buyer_ntn_cnic=inv.buyer_ntn_cnic,
            buyer_business_name=inv.buyer_business_name,
            buyer_province=inv.buyer_province,
            buyer_address=inv.buyer_address,
            buyer_registration_type=inv.buyer_registration_type,
            invoice_ref_no=inv.invoice_ref_no,
            scenario_id=inv.scenario_id,
            items=inv.items,
            environment=inv.environment,
            status=InvoiceStatus.VALIDATED if inv.status == InvoiceStatus.TRANSFERRED else inv.status,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            validated_at=inv.validated_at,
            posted_at=inv.posted_at,
            fbr_reference_number=inv.fbr_reference_number,
            validation_errors=inv.validation_errors,
            # Automation source fields omitted
        )
        for inv in invoices
    ]

    return InvoiceListResponse(
        data=invoice_responses,
        total=total_count,
        page=filters.page,
        size=filters.size,
        total_pages=total_pages
    )


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    request: Request,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update an existing invoice.
    """
    service = InvoiceService()

    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Parse the request body directly as dict
    import json
    raw_body = await request.body()
    body_data = json.loads(raw_body)

    # Create InvoiceUpdate from the parsed data for validation
    invoice_update = InvoiceUpdate(**body_data)

    # Update the invoice using the raw body data (already validated by InvoiceUpdate)
    updated_invoice = service.update_invoice_from_dict(db, invoice_id, body_data, user_uuid)

    if not updated_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Convert to response model
    return InvoiceResponse(
        id=updated_invoice.id,
        external_id=updated_invoice.external_id,
        user_id=updated_invoice.user_id,
        invoice_type=updated_invoice.invoice_type,
        invoice_date=updated_invoice.invoice_date,
        transaction_type_id=updated_invoice.transaction_type_id,
        seller_ntn_cnic=updated_invoice.seller_ntn_cnic,
        seller_business_name=updated_invoice.seller_business_name,
        seller_province=updated_invoice.seller_province,
        seller_address=updated_invoice.seller_address,
        buyer_ntn_cnic=updated_invoice.buyer_ntn_cnic,
        buyer_business_name=updated_invoice.buyer_business_name,
        buyer_province=updated_invoice.buyer_province,
        buyer_address=updated_invoice.buyer_address,
        buyer_registration_type=updated_invoice.buyer_registration_type,
        invoice_ref_no=updated_invoice.invoice_ref_no,
        scenario_id=updated_invoice.scenario_id,
        items=updated_invoice.items,
        environment=updated_invoice.environment,
        status=updated_invoice.status,
        created_at=updated_invoice.created_at,
        updated_at=updated_invoice.updated_at,
        validated_at=updated_invoice.validated_at,
        posted_at=updated_invoice.posted_at,
        fbr_reference_number=updated_invoice.fbr_reference_number,
        validation_errors=updated_invoice.validation_errors,
        # Automation source fields omitted
    )


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Mark an invoice as deleted (soft delete).
    """
    service = InvoiceService()

    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Attempt to delete the invoice
    success = service.delete_invoice(db, invoice_id, user_uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    return {"message": "Invoice marked as deleted"}


@router.get("/{invoice_id}/history")
def get_invoice_history(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get an invoice with its complete history including FBR responses.
    """
    service = InvoiceService()

    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Get the invoice with history
    result = service.get_invoice_with_history(db, invoice_id, user_uuid)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    return result


@router.patch("/{invoice_id}/status")
def update_invoice_status(
    invoice_id: UUID,
    status_update: InvoiceUpdate,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Update the status of an invoice.
    """
    service = InvoiceService()

    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Validate the status transition
    if status_update.status:
        invoice = service.get_invoice_by_id(db, invoice_id, user_uuid)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        if not service.validate_invoice_transition(invoice.status, status_update.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition: {invoice.status} -> {status_update.status}"
            )

    # Update the invoice status
    updated_invoice = service.update_invoice_status(
        db,
        invoice_id,
        status_update.status,
        user_uuid
    )

    if not updated_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Convert to response model
    return InvoiceResponse(
        id=updated_invoice.id,
        external_id=updated_invoice.external_id,
        user_id=updated_invoice.user_id,
        invoice_type=updated_invoice.invoice_type,
        invoice_date=updated_invoice.invoice_date,
        transaction_type_id=updated_invoice.transaction_type_id,
        seller_ntn_cnic=updated_invoice.seller_ntn_cnic,
        seller_business_name=updated_invoice.seller_business_name,
        seller_province=updated_invoice.seller_province,
        seller_address=updated_invoice.seller_address,
        buyer_ntn_cnic=updated_invoice.buyer_ntn_cnic,
        buyer_business_name=updated_invoice.buyer_business_name,
        buyer_province=updated_invoice.buyer_province,
        buyer_address=updated_invoice.buyer_address,
        buyer_registration_type=updated_invoice.buyer_registration_type,
        invoice_ref_no=updated_invoice.invoice_ref_no,
        scenario_id=updated_invoice.scenario_id,
        items=updated_invoice.items,
        environment=updated_invoice.environment,
        status=updated_invoice.status,
        created_at=updated_invoice.created_at,
        updated_at=updated_invoice.updated_at,
        validated_at=updated_invoice.validated_at,
        posted_at=updated_invoice.posted_at,
        fbr_reference_number=updated_invoice.fbr_reference_number,
        validation_errors=updated_invoice.validation_errors,
        # Automation source fields omitted
    )


@router.post("/{invoice_id}/validate")
async def validate_invoice_with_fbr(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Validate an invoice with FBR Digital Invoicing System.
    Invoice must be in DRAFT or FAILED status.
    """
    service = InvoiceService()
    user_uuid = UUID(user_id)

    # Get the invoice
    invoice = service.get_invoice_by_id(db, invoice_id, user_uuid)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if invoice is in DRAFT or FAILED status (allow retry for failed invoices)
    if invoice.status != InvoiceStatus.DRAFT and invoice.status != InvoiceStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only DRAFT or FAILED invoices can be validated. Current status: {invoice.status}"
        )

    # Get user's FBR access token from database based on environment
    user = db.get(User, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Select the appropriate encrypted token based on invoice environment
    encrypted_token = None
    if invoice.environment == "SANDBOX":
        encrypted_token = user.fbr_sandbox_token or user.fbr_access_token
        if not encrypted_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FBR Sandbox token not configured. Please update your profile with FBR Sandbox credentials."
            )
    else:  # PRODUCTION
        encrypted_token = user.fbr_production_token or user.fbr_access_token
        if not encrypted_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FBR Production token not configured. Please update your profile with FBR Production credentials."
            )

    # Decrypt the token before using it
    from src.utils.encryption import get_encryption_service
    encryption_service = get_encryption_service()

    try:
        access_token = encryption_service.decrypt(encrypted_token)
    except Exception as decrypt_error:
        error_type = type(decrypt_error).__name__
        error_msg = str(decrypt_error)
        logger.error(f"Failed to decrypt FBR token for user {user_uuid}: {error_type}: {error_msg}")
        logger.error(f"Encrypted token length: {len(encrypted_token) if encrypted_token else 0}")
        logger.error(f"Encrypted token preview: {encrypted_token[:50] if encrypted_token and len(encrypted_token) > 50 else encrypted_token}")

        # Clear the corrupted token from database
        if invoice.environment == "SANDBOX":
            user.fbr_sandbox_token = None
        else:
            user.fbr_production_token = None

        db.add(user)
        db.commit()

        # Return 400 error asking user to reconfigure token with detailed error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FBR {invoice.environment.title()} token decryption failed ({error_type}: {error_msg}). Token has been cleared. Please update your profile with valid FBR credentials."
        )

    try:
        # Call FBR validation API
        logger.info(f"Validating invoice {invoice_id} with FBR")
        fbr_response, fbr_request_payload = await fbr_service.validate_invoice(invoice, access_token, db=db)

        # Parse the response
        is_valid, error_message, item_errors = fbr_service.parse_validation_response(fbr_response)

        if is_valid:
            # Update invoice status to VALIDATED
            updated_invoice = service.update_invoice_status(
                db, invoice_id, InvoiceStatus.VALIDATED, user_uuid
            )

            logger.info(f"Invoice {invoice_id} validated successfully")

            return {
                "success": True,
                "message": "Invoice validated successfully",
                "invoice": InvoiceResponse(
                    id=updated_invoice.id,
                    external_id=updated_invoice.external_id,
                    user_id=updated_invoice.user_id,
                    invoice_type=updated_invoice.invoice_type,
                    invoice_date=updated_invoice.invoice_date,
                    transaction_type_id=updated_invoice.transaction_type_id,
                    seller_ntn_cnic=updated_invoice.seller_ntn_cnic,
                    seller_business_name=updated_invoice.seller_business_name,
                    seller_province=updated_invoice.seller_province,
                    seller_address=updated_invoice.seller_address,
                    buyer_ntn_cnic=updated_invoice.buyer_ntn_cnic,
                    buyer_business_name=updated_invoice.buyer_business_name,
                    buyer_province=updated_invoice.buyer_province,
                    buyer_address=updated_invoice.buyer_address,
                    buyer_registration_type=updated_invoice.buyer_registration_type,
                    invoice_ref_no=updated_invoice.invoice_ref_no,
                    scenario_id=updated_invoice.scenario_id,
                    items=updated_invoice.items,
                    environment=updated_invoice.environment,
                    status=updated_invoice.status,
                    created_at=updated_invoice.created_at,
                    updated_at=updated_invoice.updated_at,
                    validated_at=updated_invoice.validated_at,
                    posted_at=updated_invoice.posted_at,
                    fbr_reference_number=updated_invoice.fbr_reference_number,
                    validation_errors=updated_invoice.validation_errors,
                    # Automation source fields omitted
                ),
                "fbr_response": fbr_response,
                "fbr_request_payload": fbr_request_payload
            }
        else:
            # Store validation errors
            invoice.validation_errors = {
                "error": error_message,
                "item_errors": item_errors
            }
            db.add(invoice)
            db.commit()

            logger.warning(f"Invoice {invoice_id} validation failed: {error_message}")

            return {
                "success": False,
                "message": error_message,
                "errors": item_errors,
                "fbr_response": fbr_response,
                "fbr_request_payload": fbr_request_payload
            }

    except Exception as e:
        logger.error(f"Error validating invoice {invoice_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate invoice: {str(e)}"
        )


@router.post("/{invoice_id}/post")
async def post_invoice_to_fbr(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Post a validated invoice to FBR Digital Invoicing System.
    Invoice must be in VALIDATED status.
    """
    service = InvoiceService()
    user_uuid = UUID(user_id)

    # Get the invoice
    invoice = service.get_invoice_by_id(db, invoice_id, user_uuid)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if invoice is in VALIDATED status
    if invoice.status != InvoiceStatus.VALIDATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice must be in VALIDATED status to post. Current status: {invoice.status}"
        )

    # Get user's FBR access token from database based on environment
    user = db.get(User, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Select the appropriate encrypted token based on invoice environment
    encrypted_token = None
    if invoice.environment == "SANDBOX":
        encrypted_token = user.fbr_sandbox_token or user.fbr_access_token
        if not encrypted_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FBR Sandbox token not configured. Please update your profile with FBR Sandbox credentials."
            )
    else:  # PRODUCTION
        encrypted_token = user.fbr_production_token or user.fbr_access_token
        if not encrypted_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FBR Production token not configured. Please update your profile with FBR Production credentials."
            )

    # Decrypt the token before using it
    from src.utils.encryption import get_encryption_service
    encryption_service = get_encryption_service()

    try:
        access_token = encryption_service.decrypt(encrypted_token)
    except Exception as decrypt_error:
        error_type = type(decrypt_error).__name__
        error_msg = str(decrypt_error)
        logger.error(f"Failed to decrypt FBR token for user {user_uuid}: {error_type}: {error_msg}")
        logger.error(f"Encrypted token length: {len(encrypted_token) if encrypted_token else 0}")
        logger.error(f"Encrypted token preview: {encrypted_token[:50] if encrypted_token and len(encrypted_token) > 50 else encrypted_token}")

        # Clear the corrupted token from database
        if invoice.environment == "SANDBOX":
            user.fbr_sandbox_token = None
        else:
            user.fbr_production_token = None

        db.add(user)
        db.commit()

        # Return 400 error asking user to reconfigure token with detailed error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FBR {invoice.environment.title()} token decryption failed ({error_type}: {error_msg}). Token has been cleared. Please update your profile with valid FBR credentials."
        )

    try:
        # Call FBR posting API
        logger.info(f"Posting invoice {invoice_id} to FBR")
        fbr_response = await fbr_service.post_invoice(invoice, access_token, db=db)

        # Parse the response
        is_success, fbr_invoice_number, error_message = fbr_service.parse_posting_response(fbr_response)

        if is_success:
            from datetime import datetime
            # Update invoice status to POSTED and store FBR reference number
            invoice.status = InvoiceStatus.POSTED
            invoice.fbr_reference_number = fbr_invoice_number
            invoice.posted_at = datetime.utcnow()
            db.add(invoice)
            db.commit()
            db.refresh(invoice)

            logger.info(f"Invoice {invoice_id} posted successfully. FBR Number: {fbr_invoice_number}")

            return {
                "success": True,
                "message": "Invoice posted successfully",
                "fbr_invoice_number": fbr_invoice_number,
                "invoice": InvoiceResponse(
                    id=invoice.id,
                    external_id=invoice.external_id,
                    user_id=invoice.user_id,
                    invoice_type=invoice.invoice_type,
                    invoice_date=invoice.invoice_date,
                    transaction_type_id=invoice.transaction_type_id,
                    seller_ntn_cnic=invoice.seller_ntn_cnic,
                    seller_business_name=invoice.seller_business_name,
                    seller_province=invoice.seller_province,
                    seller_address=invoice.seller_address,
                    buyer_ntn_cnic=invoice.buyer_ntn_cnic,
                    buyer_business_name=invoice.buyer_business_name,
                    buyer_province=invoice.buyer_province,
                    buyer_address=invoice.buyer_address,
                    buyer_registration_type=invoice.buyer_registration_type,
                    invoice_ref_no=invoice.invoice_ref_no,
                    scenario_id=invoice.scenario_id,
                    items=invoice.items,
                    environment=invoice.environment,
                    status=invoice.status,
                    created_at=invoice.created_at,
                    updated_at=invoice.updated_at,
                    validated_at=invoice.validated_at,
                    posted_at=invoice.posted_at,
                    fbr_reference_number=invoice.fbr_reference_number,
                    validation_errors=invoice.validation_errors,
                    # Automation source fields omitted
                ),
                "fbr_response": fbr_response
            }
        else:
            # Update status to FAILED
            invoice.status = InvoiceStatus.FAILED
            invoice.validation_errors = {
                "error": error_message
            }
            db.add(invoice)
            db.commit()

            logger.warning(f"Invoice {invoice_id} posting failed: {error_message}")

            return {
                "success": False,
                "message": error_message,
                "fbr_response": fbr_response
            }

    except Exception as e:
        logger.error(f"Error posting invoice {invoice_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to post invoice: {str(e)}"
        )



async def manual_post_to_fbr(
    invoice_id: UUID,
    request_data: ManualPostingRequest,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Manually post invoice to FBR regardless of auto-posting settings.

    This endpoint allows users to manually post individual invoices at any time,
    even if auto-posting is disabled or outside the configured time window.
    The invoice will count toward the daily limit.
    """
    user_uuid = UUID(user_id)
    auto_posting_service = AutoPostingService(db)

    # Get the invoice
    invoice = db.get(Invoice, invoice_id)
    if not invoice or invoice.user_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if invoice is in VALIDATED status
    if invoice.status != InvoiceStatus.VALIDATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice must be in VALIDATED status to post. Current status: {invoice.status}"
        )

    # Get user
    user = db.get(User, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check daily limit (warn but allow override)
    from datetime import datetime
    remaining = auto_posting_service.get_daily_limit_remaining(user, datetime.utcnow())
    daily_limit_warning = remaining <= 0

    if daily_limit_warning and not request_data.override_daily_limit:
        return ManualPostingResponse(
            success=False,
            message=f"Daily limit reached ({user.auto_posting_daily_limit} invoices). Set override_daily_limit=true to post anyway.",
            invoice_id=str(invoice_id),
            daily_limit_warning=True
        )

    # Check for duplicate posting
    if invoice.status == InvoiceStatus.FBR_POSTING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already being posted"
        )

    try:
        # Update status to FBR_POSTING
        invoice.status = InvoiceStatus.FBR_POSTING
        db.add(invoice)
        db.commit()

        # Get FBR token based on user's auto-posting environment
        fbr_token = (
            user.fbr_production_token
            if user.auto_posting_environment == "PRODUCTION"
            else user.fbr_sandbox_token
        )

        if not fbr_token:
            raise ValueError(
                f"No FBR token configured for {user.auto_posting_environment} environment"
            )

        # Decrypt token
        from src.utils.encryption import get_encryption_service
        encryption_service = get_encryption_service()
        access_token = encryption_service.decrypt(fbr_token)

        # Post to FBR
        fbr_response = await fbr_service.post_invoice(invoice, access_token, db=db)
        is_success, fbr_invoice_number, error_message = fbr_service.parse_posting_response(fbr_response)

        if is_success:
            # Success - update invoice
            invoice.status = InvoiceStatus.FBR_POSTED
            invoice.fbr_posted_at = datetime.utcnow()
            invoice.fbr_reference_number = fbr_invoice_number
            invoice.fbr_retry_count = 0
            db.add(invoice)
            db.commit()

            # Create success log
            auto_posting_service.create_posting_log(
                user_id=user_uuid,
                invoice_id=invoice_id,
                action='manual',
                result='success',
                environment=user.auto_posting_environment
            )

            # Increment daily counter
            auto_posting_service.increment_daily_counter(
                user_uuid,
                datetime.utcnow(),
                user.auto_posting_start_time,
                user.auto_posting_end_time
            )

            logger.info(f"Manually posted invoice {invoice_id} to FBR")

            return ManualPostingResponse(
                success=True,
                message="Invoice posted successfully",
                invoice_id=str(invoice_id),
                fbr_reference_number=fbr_invoice_number,
                daily_limit_warning=daily_limit_warning
            )
        else:
            # FBR returned error
            invoice.status = InvoiceStatus.FBR_FAILED
            invoice.fbr_posting_error = error_message
            invoice.fbr_retry_count += 1
            db.add(invoice)
            db.commit()

            # Create failure log
            auto_posting_service.create_posting_log(
                user_id=user_uuid,
                invoice_id=invoice_id,
                action='manual',
                result='failure',
                environment=user.auto_posting_environment,
                error_details={'error': error_message}
            )

            logger.error(f"FBR rejected manual post of invoice {invoice_id}: {error_message}")

            return ManualPostingResponse(
                success=False,
                message=error_message,
                invoice_id=str(invoice_id),
                error_details={'error': error_message},
                daily_limit_warning=daily_limit_warning
            )

    except Exception as e:
        # Network failure or error
        invoice.status = InvoiceStatus.FBR_FAILED
        invoice.fbr_posting_error = str(e)
        db.add(invoice)
        db.commit()

        # Create failure log
        auto_posting_service.create_posting_log(
            user_id=user_uuid,
            invoice_id=invoice_id,
            action='manual',
            result='failure',
            environment=user.auto_posting_environment,
            error_details={'error': str(e)}
        )

        logger.error(f"Error manually posting invoice {invoice_id}: {str(e)}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to post invoice: {str(e)}"
        )


@router.get("/posting-status", response_model=PostingStatusResponse)
async def get_posting_status(
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get current auto-posting status for the user.
    """
    user_uuid = UUID(user_id)
    auto_posting_service = AutoPostingService(db)

    # Get user
    user = db.get(User, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    from datetime import datetime
    current_datetime = datetime.utcnow()
    current_time = current_datetime.time()

    # Determine current status
    if not user.auto_posting_enabled:
        status_str = "disabled"
    elif user.auto_posting_paused_until and user.auto_posting_paused_until > current_datetime:
        status_str = "paused"
    elif not auto_posting_service.is_within_time_window(
        current_time,
        user.auto_posting_start_time,
        user.auto_posting_end_time
    ):
        status_str = "outside_hours"
    else:
        status_str = "active"

    # Calculate next check time (next 5-minute cycle)
    next_check_time = None
    if status_str == "active":
        from datetime import timedelta
        next_check_time = (current_datetime + timedelta(minutes=5)).isoformat()

    return PostingStatusResponse(
        status=status_str,
        auto_posting_enabled=user.auto_posting_enabled,
        current_window_active=auto_posting_service.is_within_time_window(
            current_time,
            user.auto_posting_start_time,
            user.auto_posting_end_time
        ),
        next_check_time=next_check_time,
        today_posted_count=0,
        today_failed_count=0,
        remaining_limit=user.auto_posting_daily_limit,
        daily_limit=user.auto_posting_daily_limit,
        environment=user.auto_posting_environment,
        paused_until=user.auto_posting_paused_until.isoformat() if user.auto_posting_paused_until else None
    )


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
    disposition: str = Query("attachment", description="Content disposition: 'attachment' or 'inline'")
):
    """
    Generate and download PDF for an invoice.

    For POSTED invoices: Includes FBR response number and QR code
    For other statuses: Generates basic invoice PDF without FBR data
    """
    user_uuid = UUID(user_id)

    # Validate disposition
    if disposition not in ["attachment", "inline"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid disposition. Must be 'attachment' or 'inline'"
        )

    # Get invoice
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check ownership
    if invoice.user_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this invoice"
        )

    # Check if deleted
    if invoice.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    try:
        # Generate PDF
        pdf_service = PDFService()
        pdf_bytes = pdf_service.generate_invoice_pdf(invoice)

        # Create filename
        sanitized_number = invoice.external_id.replace('/', '_') if invoice.external_id else str(invoice_id)
        filename = f"invoice_{sanitized_number}.pdf"

        # Return PDF as streaming response
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"'
            }
        )

    except ValueError as e:
        # PDF generation validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError as e:
        # Missing assets (logo, font)
        logger.error(f"PDF generation failed - missing assets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation failed - server configuration error"
        )
    except Exception as e:
        # Unexpected error
        logger.error(f"PDF generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


# ===================================================================
# Bulk Background Operations
# ===================================================================


@router.post("/bulk-validate", response_model=BulkOperationResponse)
def start_bulk_validate(
    request: Request,
    body: BulkValidateRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """
    Start background validation of selected invoices.

    Returns immediately with a task_id. Poll /invoices/bulk-task/{task_id}
    for progress.
    """
    user_uuid = UUID(user_id)
    service = BulkOperationService()

    # Check for existing active operation
    if service.has_active_operation(db, user_uuid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A bulk operation is already in progress. Please wait for it to complete.",
        )

    invoice_ids = body.invoice_ids

    if not invoice_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invoice_ids must not be empty",
        )

    task = BulkOperationTask(
        user_id=user_uuid,
        operation_type=BulkOperationType.BULK_VALIDATE,
        invoice_ids=[str(i) for i in invoice_ids],
        status=BulkOperationStatus.PROCESSING,
        total_count=len(invoice_ids),
        processed_count=0,
        success_count=0,
        failure_count=0,
        errors=[],
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Enqueue background processing
    background_tasks.add_task(
        service.bulk_validate_invoices,
        task_id=task.id,
        invoice_ids=invoice_ids,
        user_id=user_uuid,
    )

    logger.info(
        "Bulk validate started: task=%s, invoices=%d, user=%s",
        task.id, len(invoice_ids), user_id,
    )

    return BulkOperationResponse(
        task_id=task.id,
        message=f"Validation started for {len(invoice_ids)} invoice(s).",
    )


@router.post("/bulk-post", response_model=BulkOperationResponse)
def start_bulk_post(
    request: Request,
    body: BulkPostRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """
    Start background posting of selected validated invoices to FBR.

    Returns immediately with a task_id. Poll /invoices/bulk-task/{task_id}
    for progress.
    """
    user_uuid = UUID(user_id)
    service = BulkOperationService()

    # Check for existing active operation
    if service.has_active_operation(db, user_uuid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A bulk operation is already in progress. Please wait for it to complete.",
        )

    invoice_ids = body.invoice_ids

    if not invoice_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invoice_ids must not be empty",
        )

    task = BulkOperationTask(
        user_id=user_uuid,
        operation_type=BulkOperationType.BULK_POST,
        invoice_ids=[str(i) for i in invoice_ids],
        status=BulkOperationStatus.PROCESSING,
        total_count=len(invoice_ids),
        processed_count=0,
        success_count=0,
        failure_count=0,
        errors=[],
        environment=body.environment,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Enqueue background processing
    background_tasks.add_task(
        service.bulk_post_invoices,
        task_id=task.id,
        invoice_ids=invoice_ids,
        environment=body.environment,
        user_id=user_uuid,
    )

    logger.info(
        "Bulk post started: task=%s, invoices=%d, user=%s, env=%s",
        task.id, len(invoice_ids), user_id, body.environment,
    )

    return BulkOperationResponse(
        task_id=task.id,
        message=f"Posting started for {len(invoice_ids)} invoice(s) to {body.environment}.",
    )


@router.post("/bulk-task/{task_id}/cancel", response_model=BulkOperationResponse)
def cancel_bulk_task(
    request: Request,
    task_id: UUID,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """
    Cancel a running bulk operation.

    Sets the task status to CANCELLED, which the background processing
    loop checks before processing each invoice. Already-processed
    invoices retain their new status. If the task already completed or
    doesn't exist, returns success anyway — the desired state is met.
    """
    user_uuid = UUID(user_id)
    service = BulkOperationService()
    task = service.cancel_task(db, task_id, user_uuid)

    if not task:
        logger.info(
            "Cancel requested for task %s by %s — already completed or not found",
            task_id, user_id,
        )
        return BulkOperationResponse(
            task_id=task_id,
            message="Bulk operation is already stopped.",
        )

    logger.info("Bulk operation %s cancelled by user %s", task_id, user_id)

    return BulkOperationResponse(
        task_id=task.id,
        message="Bulk operation cancelled.",
    )


@router.get("/bulk-task/{task_id}", response_model=BulkOperationStatusResponse)
def get_bulk_task_status(
    request: Request,
    task_id: UUID,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """
    Get the current progress of a bulk operation.

    Returns full status including counters, errors, and progress percentage.
    """
    user_uuid = UUID(user_id)
    service = BulkOperationService()
    task = service.get_task(db, task_id, user_uuid)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk operation task not found.",
        )

    progress_percentage = 0.0
    if task.total_count > 0:
        progress_percentage = round(
            (task.processed_count / task.total_count) * 100, 1
        )

    return BulkOperationStatusResponse(
        task_id=task.id,
        operation_type=task.operation_type.value if hasattr(task.operation_type, 'value') else str(task.operation_type),
        status=task.status.value if hasattr(task.status, 'value') else str(task.status),
        total_count=task.total_count,
        processed_count=task.processed_count,
        success_count=task.success_count,
        failure_count=task.failure_count,
        errors=[
            BulkOperationError(
                invoice_id=e["invoice_id"],
                invoice_number=e.get("invoice_number", ""),
                error=e.get("error", ""),
            )
            for e in (task.errors or [])
        ],
        progress_percentage=progress_percentage,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


@router.get("/bulk-tasks/active", response_model=ActiveBulkTasksResponse)
def get_active_bulk_tasks(
    request: Request,
    db=Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """
    Get all currently processing bulk tasks for the authenticated user.

    Used by the frontend to recover operation state after page navigation
    or browser close/reopen.
    """
    user_uuid = UUID(user_id)
    service = BulkOperationService()
    tasks = service.get_active_tasks(db, user_uuid)

    return ActiveBulkTasksResponse(
        tasks=[
            BulkOperationStatusResponse(
                task_id=t.id,
                operation_type=t.operation_type.value if hasattr(t.operation_type, 'value') else str(t.operation_type),
                status=t.status.value if hasattr(t.status, 'value') else str(t.status),
                total_count=t.total_count,
                processed_count=t.processed_count,
                success_count=t.success_count,
                failure_count=t.failure_count,
                errors=[
                    BulkOperationError(
                        invoice_id=e["invoice_id"],
                        invoice_number=e.get("invoice_number", ""),
                        error=e.get("error", ""),
                    )
                    for e in (t.errors or [])
                ],
                progress_percentage=round(
                    (t.processed_count / t.total_count * 100) if t.total_count > 0 else 0, 1
                ),
                created_at=t.created_at,
                completed_at=t.completed_at,
            )
            for t in tasks
        ],
    )
