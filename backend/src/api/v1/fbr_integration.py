from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from uuid import UUID
import asyncio
from pydantic import BaseModel

from src.database.session import get_db
from src.services.invoice_service import InvoiceService
from src.services.validation_service import ValidationService
from src.services.fbr_client import FBRClient
from src.services.fbr_service import fbr_service
from src.services.posting_service import PostingService
from src.schemas.fbr import (
    FBRValidationRequest, FBRValidationResponse,
    FBRPostingRequest, FBRPostingResponse,
    BulkPostingRequest, BulkPostingResponse, BulkPostingResult
)
from src.api.middleware.auth_middleware import require_authentication
from src.api.deps import get_database_session
from src.models.invoice import Invoice, InvoiceStatus
from src.models.fbr_response import FBRResponse
from src.models.user import User
from src.utils.helpers import generate_correlation_id
from src.utils.logging import log_audit_event


router = APIRouter()


class BuyerVerificationRequest(BaseModel):
    ntn_cnic: str
    environment: str = "SANDBOX"


class BuyerVerificationResponse(BaseModel):
    success: bool
    registration_type: str
    is_registered: bool
    business_name: str | None = None
    error: str | None = None


@router.post("/validate/{invoice_id}", response_model=FBRValidationResponse)
async def validate_invoice(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Validate an invoice with the FBR system.
    """
    # Get the invoice
    invoice_service = InvoiceService()
    user_uuid = UUID(user_id)

    invoice = invoice_service.get_invoice_by_id(db, invoice_id, user_uuid)

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if invoice is in draft status (can only validate drafts)
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot validate invoice with status '{invoice.status}'. Only draft invoices can be validated."
        )

    # Perform local validation first
    validation_service = ValidationService()
    is_locally_valid, local_validation_errors = validation_service.validate_invoice_locally(invoice.invoice_data)

    if not is_locally_valid:
        # Update invoice with validation errors
        invoice.status = InvoiceStatus.FAILED
        invoice.validation_errors = local_validation_errors
        invoice.updated_at = invoice.updated_at  # This will trigger updated_at update
        db.add(invoice)
        db.commit()

        return FBRValidationResponse(
            invoice_id=invoice_id,
            status="failed",
            validation_result=local_validation_errors,
            error_details=local_validation_errors
        )

    # Proceed with FBR validation
    fbr_client = FBRClient()

    try:
        is_valid, fbr_response_data, reference_number = await fbr_client.validate_invoice(
            invoice.invoice_data,
            invoice.environment
        )

        # Process the validation result
        processed_invoice = validation_service.process_validation_result(
            invoice, is_valid, fbr_response_data.get("errors") if not is_valid else None
        )

        # Update the invoice in database
        db.add(processed_invoice)
        db.commit()
        db.refresh(processed_invoice)

        # Log the validation attempt
        validation_service.log_validation_attempt(
            user_id, invoice_id, invoice.invoice_data, fbr_response_data
        )

        # Log audit event
        log_audit_event(
            user_id=user_id,
            action="invoice_validation",
            resource_type="invoice",
            resource_id=str(invoice_id),
            previous_state={"status": "draft"},
            new_state={"status": processed_invoice.status.value},
            success=is_valid
        )

        return FBRValidationResponse(
            invoice_id=invoice_id,
            status="validated" if is_valid else "failed",
            validation_result=fbr_response_data,
            fbr_reference_number=reference_number
        )

    except Exception as e:
        # Handle validation error
        invoice.status = InvoiceStatus.FAILED
        invoice.validation_errors = {"error": str(e)}
        invoice.updated_at = invoice.updated_at
        db.add(invoice)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )
    finally:
        await fbr_client.close()


@router.post("/post/{invoice_id}", response_model=FBRPostingResponse)
async def post_invoice(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Post a validated invoice to the FBR system.
    """
    # Get the invoice
    invoice_service = InvoiceService()
    user_uuid = UUID(user_id)

    invoice = invoice_service.get_invoice_by_id(db, invoice_id, user_uuid)

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if invoice is validated (can only post validated invoices)
    if invoice.status != InvoiceStatus.VALIDATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot post invoice with status '{invoice.status}'. Only validated invoices can be posted."
        )

    # Use the posting service
    posting_service = PostingService()

    try:
        is_posted, reference_number, fbr_response_data = await posting_service.post_single_invoice(
            db, invoice, user_id
        )

        # Log audit event
        log_audit_event(
            user_id=user_id,
            action="invoice_posting",
            resource_type="invoice",
            resource_id=str(invoice_id),
            previous_state={"status": "validated"},
            new_state={"status": "posted" if is_posted else "failed", "fbr_reference_number": reference_number},
            success=is_posted
        )

        return FBRPostingResponse(
            invoice_id=invoice_id,
            status="posted" if is_posted else "failed",
            fbr_reference_number=reference_number,
            fbr_response=fbr_response_data if is_posted else None,
            error=None if is_posted else fbr_response_data.get("error", "Posting failed")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Posting failed: {str(e)}"
        )
    finally:
        await posting_service.close()


@router.post("/bulk-post", response_model=BulkPostingResponse)
async def bulk_post_invoices(
    bulk_request: BulkPostingRequest,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Post multiple validated invoices to the FBR system in bulk.
    """
    # Use the posting service
    posting_service = PostingService()

    try:
        # Validate eligibility before processing
        valid_invoices, validation_errors = await posting_service.validate_bulk_posting_eligibility(
            db, bulk_request.invoice_ids, user_id
        )

        if validation_errors:
            # If there are validation errors, create results for them
            results = []
            for error in validation_errors:
                results.append(BulkPostingResult(
                    invoice_id=UUID(error["invoice_id"]),
                    status="failed",
                    error=error["error"]
                ))

            # Add any valid invoices that can still be processed
            valid_results = await posting_service.post_multiple_invoices(
                db, [inv.id for inv in valid_invoices], bulk_request.environment.value, user_id
            )

            all_results = results + valid_results

        else:
            # All invoices are valid, proceed with bulk posting
            all_results = await posting_service.post_multiple_invoices(
                db, bulk_request.invoice_ids, bulk_request.environment.value, user_id
            )

        # Calculate counts
        successful_count = sum(1 for r in all_results if r.status == "posted")
        failed_count = len(all_results) - successful_count

        # Create and return bulk response
        return BulkPostingResponse(
            request_id=UUID(int=hash(generate_correlation_id())) if generate_correlation_id() else UUID(int=0),
            total_count=len(bulk_request.invoice_ids),
            successful_count=successful_count,
            failed_count=failed_count,
            results=all_results
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk posting failed: {str(e)}"
        )
    finally:
        await posting_service.close()


@router.get("/invoice/{invoice_id}/status")
async def get_invoice_status(
    invoice_id: UUID,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Get the status of an invoice from the FBR system.
    """
    # Get the invoice
    invoice_service = InvoiceService()
    user_uuid = UUID(user_id)

    invoice = invoice_service.get_invoice_by_id(db, invoice_id, user_uuid)

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Check if invoice has been posted (need reference number to check status)
    if not invoice.fbr_reference_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot check status for invoice that hasn't been posted to FBR"
        )

    # Get status from FBR
    fbr_client = FBRClient()

    try:
        success, status_data = await fbr_client.get_invoice_status(
            invoice.fbr_reference_number,
            invoice.environment
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve invoice status from FBR"
            )

        return {
            "invoice_id": invoice_id,
            "fbr_reference_number": invoice.fbr_reference_number,
            "status_data": status_data,
            "environment": invoice.environment
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving invoice status: {str(e)}"
        )
    finally:
        await fbr_client.close()


@router.post("/verify-buyer", response_model=BuyerVerificationResponse)
async def verify_buyer_registration(
    request: BuyerVerificationRequest,
    db = Depends(get_database_session),
    user_id: str = Depends(require_authentication)
):
    """
    Verify buyer registration status with FBR.
    Checks if the buyer's NTN/CNIC is registered and returns the registration type.
    """
    # Get user's FBR access token based on environment
    user = db.query(User).filter(User.id == UUID(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get the appropriate token based on environment
    access_token = None
    if request.environment == "SANDBOX":
        access_token = user.fbr_sandbox_token
    else:
        access_token = user.fbr_production_token

    # Fallback to deprecated fbr_access_token if new tokens not set
    if not access_token:
        access_token = user.fbr_access_token

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FBR access token not configured. Please set up your FBR credentials first."
        )

    try:
        # Call FBR service to verify buyer
        result = await fbr_service.verify_buyer_registration(
            ntn_cnic=request.ntn_cnic,
            access_token=access_token,
            environment=request.environment
        )

        # Log audit event
        log_audit_event(
            user_id=user_id,
            action="buyer_verification",
            resource_type="buyer",
            resource_id=request.ntn_cnic,
            previous_state={},
            new_state={"registration_type": result.get("registrationType")},
            success=result.get("success", False)
        )

        return BuyerVerificationResponse(
            success=result.get("success", False),
            registration_type=result.get("registrationType", "Unregistered"),
            is_registered=result.get("isRegistered", False),
            business_name=result.get("businessName"),
            error=result.get("error")
        )

    except Exception as e:
        return BuyerVerificationResponse(
            success=False,
            registration_type="Unregistered",
            is_registered=False,
            error=f"Verification failed: {str(e)}"
        )