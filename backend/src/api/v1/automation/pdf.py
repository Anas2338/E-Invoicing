"""
PDF generation API endpoints for FBR-compliant invoice printing.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from uuid import UUID
from typing import Annotated, Union
from io import BytesIO
import logging
import asyncio

from src.database.session import get_automation_db
from src.services.pdf_service import PDFService
from src.services.automation_service import AutomationService
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.invoice import Invoice, InvoiceStatus
from src.api.middleware.auth_middleware import require_authentication
from src.middleware.rbac import require_automation_access
from src.schemas.automation import BatchPdfRequest

router = APIRouter()
logger = logging.getLogger(__name__)

# Timeout for batch PDF generation (180 seconds)
BATCH_PDF_TIMEOUT = 180


@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_automation_db)],
    user_id: str = Depends(require_automation_access),
    disposition: str = "attachment"
):
    """
    Generate and download PDF for a single transferred invoice.

    This endpoint generates an FBR-compliant PDF document for a transferred invoice,
    including the FBR Digital Invoicing System logo and a QR code containing the
    FBR-issued USIN (Unique Sales Invoice Number) for verification.

    **Authentication**: Requires valid JWT token in Authorization header

    **Authorization**: User must own the invoice (invoice.user_id == user_id)

    **PDF Contents**:
    - Invoice header (invoice number, date, seller/buyer details)
    - Line items table (HS code, product description, quantity, rates, taxes, totals)
    - Invoice totals (subtotal, taxes, grand total)
    - FBR logo (top right)
    - QR code with USIN (bottom right, Version 2.0, 25x25 modules, 1.0x1.0 inch)

    **File Format**: PDF (A4 size, 210mm x 297mm)

    **Unicode Support**: Supports Urdu/Arabic characters via Noto Sans Arabic font

    Args:
        invoice_id: UUID of the invoice to print
        disposition: Content-Disposition type - "attachment" (download) or "inline" (open in browser)
        db: Database session (injected)
        user_id: Authenticated user ID from JWT token (injected)

    Returns:
        StreamingResponse: PDF file with appropriate Content-Disposition header
        - Content-Type: application/pdf
        - Filename: invoice_<invoice_number>.pdf

    Raises:
        HTTPException 400 (Bad Request):
            - Invalid disposition type (must be 'attachment' or 'inline')
            - Invoice is not in 'transferred' status
            - Invoice is missing FBR response data
            - Invoice is missing USIN in FBR response
            - Invoice data structure is invalid
        HTTPException 403 (Forbidden):
            - User does not own this invoice
        HTTPException 404 (Not Found):
            - Invoice with given ID does not exist
        HTTPException 500 (Internal Server Error):
            - PDF generation failed due to missing assets (logo, font)
            - Unexpected error during PDF generation

    Example:
        ```bash
        # Download PDF
        curl -H "Authorization: Bearer <token>" \\
             http://localhost:8001/api/v1/automation/invoices/{invoice_id}/pdf \\
             --output invoice.pdf

        # Open in browser
        curl -H "Authorization: Bearer <token>" \\
             "http://localhost:8001/api/v1/automation/invoices/{invoice_id}/pdf?disposition=inline" \\
             --output invoice.pdf
        ```
    """
    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    # Validate disposition parameter
    if disposition not in ["attachment", "inline"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid disposition type '{disposition}'. Must be 'attachment' or 'inline'."
        )

    logger.info(
        f"PDF generation requested for invoice {invoice_id} by user {user_id} "
        f"(disposition: {disposition})"
    )

    # Initialize services
    automation_service = AutomationService(db)
    pdf_service = PDFService()

    # Try to fetch from automation invoices first
    invoice: Union[AutomationInvoice, Invoice, None] = automation_service.get_invoice_by_id(invoice_id)
    is_automation = True

    # If not found in automation, try manual invoices
    if not invoice:
        invoice = db.get(Invoice, invoice_id)
        is_automation = False

    if not invoice:
        logger.warning(f"Invoice {invoice_id} not found in either automation or manual invoices")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found"
        )

    # Authorization check: verify user owns this invoice
    if invoice.user_id != user_uuid:
        logger.warning(
            f"User {user_id} attempted to access invoice {invoice_id} "
            f"owned by user {invoice.user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this invoice"
        )

    # Validate invoice status (transferred for automation, POSTED for manual)
    if is_automation:
        if invoice.status != AutomationInvoiceStatus.TRANSFERRED:
            logger.warning(
                f"Cannot generate PDF for automation invoice {invoice_id} with status {invoice.status}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot generate PDF for invoice with status '{invoice.status}'. "
                       "Only transferred invoices can be printed."
            )
    else:
        if invoice.status != InvoiceStatus.POSTED:
            logger.warning(
                f"Cannot generate PDF for manual invoice {invoice_id} with status {invoice.status}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot generate PDF for invoice with status '{invoice.status}'. "
                       "Only posted invoices can be printed."
            )

    # Validate USIN exists (different fields for automation vs manual)
    usin = None
    if is_automation:
        if not invoice.fbr_response:
            logger.error(f"Automation invoice {invoice_id} missing FBR response")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice is missing FBR response data"
            )
        usin = invoice.fbr_response.get('USIN') or invoice.fbr_response.get('usin')
        if not usin:
            logger.error(f"Automation invoice {invoice_id} missing USIN in FBR response")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice is missing USIN (FBR reference number)"
            )
    else:
        # Manual invoice uses fbr_reference_number field
        usin = invoice.fbr_reference_number
        if not usin:
            logger.error(f"Manual invoice {invoice_id} missing FBR reference number")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice is missing FBR reference number"
            )

    # Generate PDF
    try:
        pdf_bytes = pdf_service.generate_invoice_pdf(invoice)

        # Create filename: invoice_<invoice_number>.pdf
        if is_automation:
            invoice_number = invoice.invoice_number.replace('/', '_')
        else:
            invoice_number = invoice.external_id.replace('/', '_')
        filename = f"invoice_{invoice_number}.pdf"

        logger.info(
            f"Successfully generated PDF for {'automation' if is_automation else 'manual'} "
            f"invoice {invoice_id} ({len(pdf_bytes)} bytes)"
        )

        # Return PDF as streaming response with specified disposition
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"{disposition}; filename={filename}"
            }
        )

    except FileNotFoundError as e:
        logger.error(f"PDF generation failed - missing asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"PDF generation failed - invalid data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"PDF generation failed with unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation failed due to an internal error"
        )


@router.post("/invoices/batch-pdf")
async def get_batch_invoice_pdf(
    request: BatchPdfRequest,
    db: Annotated[Session, Depends(get_automation_db)],
    user_id: str = Depends(require_automation_access)
):
    """
    Generate and download PDF for multiple transferred invoices in a single document.

    This endpoint generates a single FBR-compliant PDF document containing multiple
    invoices with page breaks between them. Each invoice includes the FBR logo and
    QR code. Invoices are rendered in the order provided in the request.

    **Authentication**: Requires valid JWT token in Authorization header

    **Authorization**: User must own all invoices in the batch

    **Batch Limits**:
    - Minimum: 1 invoice
    - Maximum: 50 invoices
    - Timeout: 180 seconds

    **PDF Contents** (per invoice):
    - Invoice header (invoice number, date, seller/buyer details)
    - Line items table (HS code, product description, quantity, rates, taxes, totals)
    - Invoice totals (subtotal, taxes, grand total)
    - FBR logo (top right)
    - QR code with USIN (bottom right)
    - Page break (except after last invoice)

    **File Format**: PDF (A4 size, 210mm x 297mm)

    **Performance**:
    - ~3 seconds per invoice
    - 50-invoice batch: ~150 seconds (within 180s timeout)

    **Memory Optimization**: Efficient memory usage for large batches

    Args:
        request: BatchPdfRequest with list of invoice IDs (1-50)
        db: Database session (injected)
        user_id: Authenticated user ID from JWT token (injected)

    Request Body:
        ```json
        {
            "invoice_ids": [
                "uuid-1",
                "uuid-2",
                "uuid-3"
            ]
        }
        ```

    Returns:
        StreamingResponse: PDF file containing all invoices
        - Content-Type: application/pdf
        - Filename: batch_invoices_<count>_<timestamp>.pdf

    Raises:
        HTTPException 400 (Bad Request):
            - Empty invoice list
            - Batch size exceeds 50 invoices
            - One or more invoices not in 'transferred' status
            - One or more invoices missing FBR response/USIN
            - Invalid invoice data structure
        HTTPException 403 (Forbidden):
            - User does not own one or more invoices in the batch
        HTTPException 404 (Not Found):
            - One or more invoices not found
        HTTPException 500 (Internal Server Error):
            - PDF generation failed due to missing assets
            - Failed to retrieve all requested invoices
        HTTPException 504 (Gateway Timeout):
            - Batch PDF generation exceeded 180 second timeout
            - Recommendation: Reduce batch size or contact support

    Example:
        ```bash
        # Generate batch PDF for 3 invoices
        curl -X POST \\
             -H "Authorization: Bearer <token>" \\
             -H "Content-Type: application/json" \\
             -d '{"invoice_ids": ["uuid-1", "uuid-2", "uuid-3"]}' \\
             http://localhost:8001/api/v1/automation/invoices/batch-pdf \\
             --output batch_invoices.pdf
        ```

    Notes:
        - Invoices are rendered in the order provided in invoice_ids array
        - Selection order is preserved from frontend
        - Progress indicator shown in UI for batches with 20+ invoices
        - All invoices must be in 'transferred' status
        - All invoices must belong to the authenticated user
    """
    # Convert user_id string to UUID
    user_uuid = UUID(user_id)

    invoice_ids = request.invoice_ids
    logger.info(
        f"Batch PDF generation requested for {len(invoice_ids)} invoices "
        f"by user {user_id}"
    )

    # Validate batch size (Pydantic already validates 1-50, but double-check)
    if len(invoice_ids) > 50:
        logger.warning(f"Batch size {len(invoice_ids)} exceeds maximum of 50")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum limit of 50 invoices (got {len(invoice_ids)})"
        )

    if len(invoice_ids) == 0:
        logger.warning("Empty invoice list provided for batch PDF")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No invoices provided for batch PDF generation"
        )

    # Initialize services
    automation_service = AutomationService(db)
    pdf_service = PDFService()

    # Fetch all invoices in the order provided (preserve selection order)
    invoices = []
    for invoice_id in invoice_ids:
        invoice = automation_service.get_invoice_by_id(invoice_id)

        if not invoice:
            logger.warning(f"Invoice {invoice_id} not found in batch request")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with ID {invoice_id} not found"
            )

        # Authorization check: verify user owns this invoice
        if invoice.user_id != user_uuid:
            logger.warning(
                f"User {user_id} attempted to access invoice {invoice_id} "
                f"owned by user {invoice.user_id} in batch request"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to access invoice {invoice_id}"
            )

        # Validate invoice status
        if invoice.status != AutomationInvoiceStatus.TRANSFERRED:
            logger.warning(
                f"Cannot include invoice {invoice_id} with status {invoice.status} in batch PDF"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot generate PDF for invoice {invoice.invoice_number} "
                       f"with status '{invoice.status}'. Only transferred invoices can be printed."
            )

        invoices.append(invoice)

    # Verify we have all invoices
    if len(invoices) != len(invoice_ids):
        logger.error(
            f"Mismatch in invoice count: requested {len(invoice_ids)}, "
            f"found {len(invoices)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve all requested invoices"
        )

    # Generate batch PDF
    try:
        # Wrap PDF generation in asyncio timeout to prevent long-running operations
        try:
            # Run PDF generation with timeout
            pdf_bytes = await asyncio.wait_for(
                asyncio.to_thread(pdf_service.generate_batch_pdf, invoices),
                timeout=BATCH_PDF_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Batch PDF generation timed out after {BATCH_PDF_TIMEOUT} seconds "
                f"for {len(invoices)} invoices"
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Batch PDF generation timed out after {BATCH_PDF_TIMEOUT} seconds. "
                       f"Please try with fewer invoices or contact support."
            )

        # Create filename: batch_invoices_<count>_<timestamp>.pdf
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_invoices_{len(invoices)}_{timestamp}.pdf"

        logger.info(
            f"Successfully generated batch PDF for {len(invoices)} invoices "
            f"({len(pdf_bytes)} bytes)"
        )

        # Return PDF as streaming response
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except FileNotFoundError as e:
        logger.error(f"Batch PDF generation failed - missing asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Batch PDF generation failed - invalid data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Batch PDF generation failed with unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch PDF generation failed due to an internal error"
        )

