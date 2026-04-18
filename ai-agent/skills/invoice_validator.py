"""
Invoice Validator Skill - Validates invoices using existing ValidationService.

Wraps the backend ValidationService to provide validation within the
AI Agent context.
"""
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Add project root and backend to path (works on both Windows and Docker)
# Backend must be in path for its relative imports (from src.*)
project_root = Path(__file__).parent.parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from skills import BaseSkill, SkillResult, SkillStatus


class InvoiceValidatorSkill(BaseSkill):
    """
    Skill for validating invoices before FBR submission.

    Wraps the existing ValidationService from the backend.
    """

    def __init__(self):
        """Initialize invoice validator skill."""
        super().__init__("invoice_validator")

    def validate_input(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input data.

        Args:
            data: Must contain 'invoice_data' key with invoice details

        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'invoice_data' not in data:
            return False, "Missing required field: invoice_data"

        if not isinstance(data['invoice_data'], dict):
            return False, "invoice_data must be a dictionary"

        return True, None

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Validate invoice data.

        Args:
            context: Must contain 'invoice_data' with invoice details

        Returns:
            SkillResult with validation outcome
        """
        try:
            from backend.src.services.validation_service import ValidationService
            from config import config
            import random

            invoice_data = context['invoice_data']

            # DRY RUN MODE - Simulate validation without actual checks
            if config.DRY_RUN:
                self.logger.info(f"[DRY RUN] Simulating validation for invoice {invoice_data.get('invoice_number', 'unknown')}")

                # Simulate 98% validation success rate (2% random failures for testing)
                is_valid = random.random() < 0.98

                if is_valid:
                    validation_errors = None
                    self.logger.info(f"[DRY RUN] Simulated validation SUCCESS for invoice {invoice_data.get('invoice_number')}")
                else:
                    validation_errors = "Simulated validation error: Missing required field for testing"
                    self.logger.warning(f"[DRY RUN] Simulated validation FAILURE for invoice {invoice_data.get('invoice_number')}")
            else:
                # REAL MODE - Actual validation
                validation_service = ValidationService()
                is_valid, validation_errors = validation_service.validate_invoice_locally(invoice_data)

            if is_valid:
                self.logger.info(f"Invoice {invoice_data.get('invoice_number', 'unknown')} validated successfully")
                return SkillResult(
                    status=SkillStatus.SUCCESS,
                    data={
                        "is_valid": True,
                        "invoice_number": invoice_data.get('invoice_number')
                    }
                )
            else:
                self.logger.warning(f"Invoice {invoice_data.get('invoice_number', 'unknown')} validation failed")
                return SkillResult(
                    status=SkillStatus.FAILURE,
                    data={
                        "is_valid": False,
                        "invoice_number": invoice_data.get('invoice_number'),
                        "validation_errors": validation_errors
                    },
                    error=f"Validation failed: {validation_errors}"
                )

        except Exception as e:
            return self.handle_error(e, context)
