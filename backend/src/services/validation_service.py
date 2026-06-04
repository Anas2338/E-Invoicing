from typing import Dict, Any, Optional
from datetime import datetime
import logging
from uuid import UUID

from src.models.invoice import Invoice, InvoiceStatus
from src.models.fbr_response import FBRResponse
from src.schemas.fbr import FBRValidationResponse
from src.utils.helpers import calculate_hash, validate_fbr_invoice_structure


logger = logging.getLogger(__name__)


class ValidationService:
    """
    Service class for handling invoice validation business logic.
    """

    def validate_invoice_locally(self, invoice_data: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
        """
        Perform local validation of invoice data before sending to FBR based on FBR technical specification.

        Args:
            invoice_data: Invoice data to validate

        Returns:
            Tuple of (is_valid, validation_errors)
        """
        validation_errors = {}

        # Validate required FBR fields based on technical specification
        required_fields = [
            "invoice_type", "invoice_date", "seller_ntn_cnic", "seller_business_name",
            "seller_province", "seller_address", "buyer_ntn_cnic", "buyer_business_name",
            "buyer_province", "buyer_address", "buyer_registration_type", "items"
        ]

        for field in required_fields:
            if field not in invoice_data:
                validation_errors[field] = f"Missing required field: {field}"

        # Validate invoice type
        if "invoice_type" in invoice_data:
            valid_types = ["Sale Invoice", "Debit Note", "Credit Note"]
            if invoice_data["invoice_type"] not in valid_types:
                validation_errors["invoice_type"] = f"Invalid invoice type. Must be one of: {valid_types}"

        # Validate date format
        if "invoice_date" in invoice_data:
            try:
                # FBR expects date in YYYY-MM-DD format
                datetime.strptime(invoice_data["invoice_date"], "%Y-%m-%d")
            except ValueError:
                validation_errors["invoice_date"] = "Invalid date format, expected YYYY-MM-DD"

        # Validate NTN/CNIC format (7 or 13 chars, buyer may be empty)
        for field in ["seller_ntn_cnic", "buyer_ntn_cnic"]:
            if field in invoice_data:
                ntn_cnic = str(invoice_data[field]).strip()
                if field == "buyer_ntn_cnic" and not ntn_cnic:
                    continue  # Empty buyer NTN/CNIC is allowed
                # Handle float-to-string artifacts (e.g., "1234567.0" → "1234567")
                if ntn_cnic.endswith(".0") and len(ntn_cnic) > 2:
                    ntn_cnic = ntn_cnic[:-2]
                # Accept 7-char NTN, 13-char CNIC, or alphanumeric formats with dashes
                ntn_cnic_clean = ntn_cnic.replace('-', '').replace(' ', '')
                if not (6 <= len(ntn_cnic_clean) <= 15):
                    validation_errors[field] = f"{field} must be 7 or 13 digits"

        # Validate buyer registration type
        if "buyer_registration_type" in invoice_data:
            valid_reg_types = ["Registered", "Unregistered"]
            if invoice_data["buyer_registration_type"] not in valid_reg_types:
                validation_errors["buyer_registration_type"] = f"Invalid registration type. Must be one of: {valid_reg_types}"

        # Validate items
        if "items" in invoice_data:
            items = invoice_data["items"]
            if not isinstance(items, list) or len(items) == 0:
                validation_errors["items"] = "Items must be a non-empty list"
            else:
                for i, item in enumerate(items):
                    if not isinstance(item, dict):
                        validation_errors[f"item_{i}"] = f"Item {i} must be an object"
                        continue

                    # Validate required item fields per FBR spec
                    item_required_fields = ["hs_code", "product_description", "rate", "uom", "quantity", "total_values", "value_sales_excluding_st", "sales_tax_applicable", "fed_payable", "discount"]
                    for field in item_required_fields:
                        if field not in item:
                            validation_errors[f"item_{i}_{field}"] = f"Item {i} missing required field: {field}"

        is_valid = len(validation_errors) == 0
        return is_valid, validation_errors

    def validate_invoice_against_fbr_spec(self, invoice: Invoice) -> tuple[bool, Dict[str, Any]]:
        """
        Validate an invoice against the FBR technical specification.

        Args:
            invoice: Invoice object to validate

        Returns:
            Tuple of (is_valid, validation_errors)
        """
        # This would contain the actual FBR specification validation logic
        # For now, we'll implement a basic validation based on our understanding

        # Perform local validation first
        is_valid, validation_errors = self.validate_invoice_locally(invoice.invoice_data)

        # Additional FBR-specific validations would go here
        # This is where the actual FBR technical specification would be applied

        return is_valid, validation_errors

    def process_validation_result(self, invoice: Invoice, validation_success: bool,
                                validation_errors: Optional[Dict[str, Any]] = None) -> Invoice:
        """
        Process the validation result and update the invoice status accordingly.

        Args:
            invoice: Invoice object being validated
            validation_success: Whether validation passed
            validation_errors: Dictionary of validation errors if any

        Returns:
            Updated invoice object
        """
        if validation_success:
            # Update invoice status to validated
            invoice.status = InvoiceStatus.VALIDATED
            invoice.validated_at = datetime.utcnow()
            invoice.validation_errors = None  # Clear any previous errors
        else:
            # Update invoice status to failed with validation errors
            invoice.status = InvoiceStatus.FAILED
            if validation_errors:
                invoice.validation_errors = validation_errors

        invoice.updated_at = datetime.utcnow()
        return invoice

    def prepare_validation_request(self, invoice: Invoice) -> Dict[str, Any]:
        """
        Prepare the validation request payload for FBR API.

        Args:
            invoice: Invoice object to prepare for validation

        Returns:
            Dictionary containing the validation request payload
        """
        # Construct the validation request based on FBR API requirements
        validation_payload = {
            "invoice_id": str(invoice.id),
            "external_id": invoice.external_id,
            "invoice_data": invoice.invoice_data,
            "invoice_type": invoice.invoice_type.value,
            "environment": invoice.environment.value,
            "timestamp": datetime.utcnow().isoformat()
        }

        return validation_payload

    def create_validation_response(self, invoice_id: UUID, is_valid: bool,
                                 validation_result: Dict[str, Any],
                                 fbr_reference_number: Optional[str] = None) -> FBRValidationResponse:
        """
        Create a validation response object.

        Args:
            invoice_id: ID of the invoice being validated
            is_valid: Whether the validation passed
            validation_result: Detailed validation result
            fbr_reference_number: Reference number from FBR if validation passed

        Returns:
            FBRValidationResponse object
        """
        status = "validated" if is_valid else "failed"

        return FBRValidationResponse(
            invoice_id=invoice_id,
            status=status,
            validation_result=validation_result,
            fbr_reference_number=fbr_reference_number
        )

    def log_validation_attempt(self, user_id: str, invoice_id: UUID,
                             request_payload: Dict[str, Any],
                             response_payload: Dict[str, Any]):
        """
        Log validation attempt for audit purposes.

        Args:
            user_id: ID of the user initiating the validation
            invoice_id: ID of the invoice being validated
            request_payload: Request sent to validation service
            response_payload: Response received from validation service
        """
        logger.info(f"Validation attempt for invoice {invoice_id} by user {user_id}",
                   extra={
                       "user_id": user_id,
                       "invoice_id": str(invoice_id),
                       "action": "invoice_validation_attempt",
                       "request_size": len(str(request_payload)),
                       "response_size": len(str(response_payload))
                   })

    def validate_environment_compatibility(self, invoice: Invoice, target_environment: str) -> bool:
        """
        Validate that the invoice is compatible with the target environment.

        Args:
            invoice: Invoice object to validate
            target_environment: Target environment (SANDBOX/PRODUCTION)

        Returns:
            True if compatible, False otherwise
        """
        # In a real implementation, there might be specific rules about
        # which invoices can be validated in which environments
        # For now, we'll allow all invoices in any environment

        # Check if invoice environment matches target or if it's a valid transition
        if invoice.environment.value == target_environment.upper():
            return True

        # Additional environment-specific validation rules would go here
        return True

    def calculate_validation_score(self, invoice: Invoice) -> float:
        """
        Calculate a validation confidence score for the invoice.

        Args:
            invoice: Invoice object to score

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # This would implement business logic to calculate how confident
        # we are that the invoice will pass FBR validation
        # For now, return a basic score based on completeness

        score = 0.0

        # Check if required fields are present
        required_weight = 0.5
        if "invoice_number" in invoice.invoice_data:
            score += required_weight * 0.25
        if "issue_date" in invoice.invoice_data:
            score += required_weight * 0.25
        if "supplier_info" in invoice.invoice_data:
            score += required_weight * 0.25
        if "customer_info" in invoice.invoice_data:
            score += required_weight * 0.25

        # Check data quality
        quality_weight = 0.3
        if isinstance(invoice.invoice_data.get("items"), list) and len(invoice.invoice_data["items"]) > 0:
            score += quality_weight

        # Check format validity
        format_weight = 0.2
        try:
            datetime.fromisoformat(invoice.invoice_data.get("issue_date", "").replace('Z', '+00:00'))
            score += format_weight
        except (ValueError, TypeError):
            pass  # Date format is invalid, don't add to score

        return min(score, 1.0)  # Cap at 1.0