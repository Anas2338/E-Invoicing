from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlmodel import Session
from uuid import UUID
import logging

from src.models.invoice import Invoice, InvoiceStatus
from src.models.fbr_response import FBRResponse
from src.schemas.fbr import BulkPostingResult, FBREnvironment
from src.services.fbr_client import FBRClient
from src.utils.helpers import generate_correlation_id


logger = logging.getLogger(__name__)


class PostingService:
    """
    Service class for handling invoice posting business logic.
    """

    def __init__(self):
        self.fbr_client = FBRClient()

    async def post_single_invoice(self, db: Session, invoice: Invoice,
                                user_id: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Post a single validated invoice to FBR.

        Args:
            db: Database session
            invoice: Invoice object to post
            user_id: ID of the user initiating the posting

        Returns:
            Tuple of (success, reference_number, response_data)
        """
        # Verify invoice is in validated state
        if invoice.status != InvoiceStatus.VALIDATED:
            raise ValueError(f"Invoice must be validated before posting. Current status: {invoice.status}")

        # Get user's FBR token
        from src.models.user import User
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            raise ValueError("User not found")

        # Get the appropriate encrypted token based on environment
        encrypted_token = None
        if invoice.environment == "SANDBOX":
            encrypted_token = user.fbr_sandbox_token
        else:
            encrypted_token = user.fbr_production_token

        if not encrypted_token:
            encrypted_token = user.fbr_access_token

        if not encrypted_token:
            raise ValueError("FBR access token not configured")

        try:
            # Post to FBR using user credentials
            is_posted, response_data, reference_number = await self.fbr_client.post_invoice_with_user_credentials(
                invoice.invoice_data,
                invoice.environment,
                encrypted_token
            )

            if is_posted:
                # Update invoice status to posted
                invoice.status = InvoiceStatus.POSTED
                invoice.fbr_reference_number = reference_number
                invoice.posted_at = datetime.utcnow()
                invoice.updated_at = datetime.utcnow()

                # Update the invoice in database
                db.add(invoice)
                db.commit()
                db.refresh(invoice)

                logger.info(f"Invoice {invoice.id} posted successfully with reference {reference_number}")
            else:
                # Update invoice status to failed
                invoice.status = InvoiceStatus.FAILED
                if "errors" in response_data:
                    invoice.validation_errors = response_data["errors"]
                invoice.updated_at = datetime.utcnow()

                # Update the invoice in database
                db.add(invoice)
                db.commit()

                logger.warning(f"Invoice {invoice.id} posting failed: {response_data.get('error')}")

            return is_posted, reference_number, response_data

        except Exception as e:
            # Handle posting error
            invoice.status = InvoiceStatus.FAILED
            invoice.validation_errors = {"error": str(e)}
            invoice.updated_at = datetime.utcnow()

            # Update the invoice in database
            db.add(invoice)
            db.commit()

            logger.error(f"Error posting invoice {invoice.id}: {str(e)}")

            raise

    async def post_multiple_invoices(self, db: Session, invoice_ids: List[UUID],
                                   environment: str, user_id: str) -> List[BulkPostingResult]:
        """
        Post multiple validated invoices to FBR in bulk.

        Args:
            db: Database session
            invoice_ids: List of invoice IDs to post
            environment: Target environment (SANDBOX or PRODUCTION)
            user_id: ID of the user initiating the posting

        Returns:
            List of BulkPostingResult objects
        """
        results = []
        successful_count = 0
        failed_count = 0

        # Process each invoice
        for invoice_id in invoice_ids:
            try:
                # Get the invoice
                invoice = db.get(Invoice, invoice_id)

                if not invoice:
                    results.append(BulkPostingResult(
                        invoice_id=invoice_id,
                        status="failed",
                        error="Invoice not found"
                    ))
                    failed_count += 1
                    continue

                # Check if user owns this invoice
                if str(invoice.user_id) != user_id:
                    results.append(BulkPostingResult(
                        invoice_id=invoice_id,
                        status="failed",
                        error="Access denied: user does not own invoice"
                    ))
                    failed_count += 1
                    continue

                # Check if invoice is validated
                if invoice.status != InvoiceStatus.VALIDATED:
                    results.append(BulkPostingResult(
                        invoice_id=invoice_id,
                        status="failed",
                        error=f"Invoice not validated (status: {invoice.status})"
                    ))
                    failed_count += 1
                    continue

                # Temporarily update environment if needed
                original_environment = invoice.environment
                if environment.upper() != original_environment.value:
                    # In a real system, you might want to validate this change
                    # For now, we'll allow it
                    pass

                # Post the invoice
                is_posted, reference_number, response_data = await self.post_single_invoice(
                    db, invoice, user_id
                )

                if is_posted:
                    results.append(BulkPostingResult(
                        invoice_id=invoice_id,
                        status="posted",
                        fbr_reference_number=reference_number
                    ))
                    successful_count += 1
                else:
                    results.append(BulkPostingResult(
                        invoice_id=invoice_id,
                        status="failed",
                        error=response_data.get("error", "Posting failed")
                    ))
                    failed_count += 1

            except Exception as e:
                results.append(BulkPostingResult(
                    invoice_id=invoice_id,
                    status="failed",
                    error=f"Processing error: {str(e)}"
                ))
                failed_count += 1

        logger.info(f"Bulk posting completed: {successful_count} successful, {failed_count} failed")

        return results

    async def validate_bulk_posting_eligibility(self, db: Session, invoice_ids: List[UUID],
                                             user_id: str) -> Tuple[List[Invoice], List[Dict[str, Any]]]:
        """
        Validate that all invoices are eligible for bulk posting.

        Args:
            db: Database session
            invoice_ids: List of invoice IDs to validate
            user_id: ID of the user initiating the posting

        Returns:
            Tuple of (valid_invoices, validation_errors)
        """
        valid_invoices = []
        validation_errors = []

        for i, invoice_id in enumerate(invoice_ids):
            try:
                # Get the invoice
                invoice = db.get(Invoice, invoice_id)

                if not invoice:
                    validation_errors.append({
                        "index": i,
                        "invoice_id": str(invoice_id),
                        "error": "Invoice not found"
                    })
                    continue

                # Check if user owns this invoice
                if str(invoice.user_id) != user_id:
                    validation_errors.append({
                        "index": i,
                        "invoice_id": str(invoice_id),
                        "error": "Access denied: user does not own invoice"
                    })
                    continue

                # Check if invoice is validated
                if invoice.status != InvoiceStatus.VALIDATED:
                    validation_errors.append({
                        "index": i,
                        "invoice_id": str(invoice_id),
                        "error": f"Invoice not validated (status: {invoice.status})"
                    })
                    continue

                # All checks passed
                valid_invoices.append(invoice)

            except Exception as e:
                validation_errors.append({
                    "index": i,
                    "invoice_id": str(invoice_id),
                    "error": f"Validation error: {str(e)}"
                })

        return valid_invoices, validation_errors

    def prepare_posting_request(self, invoice: Invoice, environment: str = None) -> Dict[str, Any]:
        """
        Prepare the posting request payload for FBR API based on technical specification.

        Args:
            invoice: Invoice object to prepare for posting
            environment: Optional environment override

        Returns:
            Dictionary containing the posting request payload
        """
        target_environment = environment or invoice.environment.value

        # Prepare payload according to FBR technical specification
        payload = {
            "invoiceType": invoice.invoice_type,
            "invoiceDate": invoice.invoice_date,
            "sellerNTNCNIC": invoice.seller_ntn_cnic,
            "sellerBusinessName": invoice.seller_business_name,
            "sellerProvince": invoice.seller_province,
            "sellerAddress": invoice.seller_address,
            "buyerNTNCNIC": invoice.buyer_ntn_cnic,
            "buyerBusinessName": invoice.buyer_business_name,
            "buyerProvince": invoice.buyer_province,
            "buyerAddress": invoice.buyer_address,
            "buyerRegistrationType": invoice.buyer_registration_type,
            "invoiceRefNo": invoice.invoice_ref_no or "",
            "items": [item.dict() for item in invoice.items],
            "environment": target_environment,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add scenario ID for sandbox environment
        if target_environment.upper() == "SANDBOX" and invoice.scenario_id:
            payload["scenarioId"] = invoice.scenario_id

        return payload

    async def get_posting_status(self, db: Session, reference_number: str,
                               environment: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get the status of a posted invoice from FBR.

        Args:
            db: Database session
            reference_number: FBR reference number of the posted invoice
            environment: Environment where the invoice was posted

        Returns:
            Tuple of (success, status_data)
        """
        try:
            success, status_data = await self.fbr_client.get_invoice_status(
                reference_number,
                FBREnvironment(environment.upper())
            )

            return success, status_data

        except Exception as e:
            logger.error(f"Error getting posting status for reference {reference_number}: {str(e)}")
            return False, {"error": f"Failed to get status: {str(e)}"}

    async def ensure_transactional_integrity(self, db: Session, operations: List[callable]) -> bool:
        """
        Ensure transactional integrity for bulk operations.

        Args:
            db: Database session
            operations: List of operations to perform atomically

        Returns:
            True if all operations succeeded, False otherwise
        """
        try:
            # Start a transaction
            for operation in operations:
                await operation()

            # Commit the transaction
            db.commit()
            return True
        except Exception as e:
            # Rollback on error
            db.rollback()
            logger.error(f"Transaction failed: {str(e)}")
            return False

    async def close(self):
        """
        Close the FBR client connection.
        """
        await self.fbr_client.close()