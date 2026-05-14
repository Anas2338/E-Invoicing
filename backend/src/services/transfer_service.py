"""
TransferService: Transfers validated automation invoices to the main database.

Handles data transformation from AutomationInvoice (JSON-based) to the
structured Invoice model, duplicate detection, and error classification.

All automation traces are hidden — transferred invoices appear identical
to manually created invoices (source="manual", normal status flow).
"""
import logging
from typing import Any
from datetime import datetime
from uuid import UUID

from sqlmodel import select

from src.models.invoice import Invoice, InvoiceStatus, Environment
from src.models.automation_invoice import AutomationInvoice

logger = logging.getLogger(__name__)


class TransferService:
    """Transforms and transfers automation invoices into the main invoice table."""

    def transform_invoice_data(self, automation_invoice: AutomationInvoice) -> Invoice:
        """
        Transform an AutomationInvoice into a main Invoice model.

        Automation traces are hidden:
        - source set to "manual" (indistinguishable from manual invoices)
        - status set to VALIDATED (already validated before transfer)
        - automation_invoice_id stored for duplicate detection but hidden from API
        - transferred_at left as None
        """
        data: dict[str, Any] = automation_invoice.invoice_data or {}

        invoice = Invoice(
            external_id=automation_invoice.invoice_number,
            user_id=automation_invoice.user_id,
            invoice_type=data.get("invoice_type", "Sale Invoice"),
            invoice_date=data.get("invoice_date", ""),
            transaction_type_id=data.get("transaction_type_id"),
            seller_ntn_cnic=data.get("seller_ntn_cnic", ""),
            seller_business_name=data.get("seller_business_name", ""),
            seller_province=data.get("seller_province", ""),
            seller_address=data.get("seller_address", ""),
            buyer_ntn_cnic=data.get("buyer_ntn_cnic", ""),
            buyer_business_name=data.get("buyer_business_name", ""),
            buyer_province=data.get("buyer_province", ""),
            buyer_address=data.get("buyer_address", ""),
            buyer_registration_type=data.get("buyer_registration_type", "Registered"),
            invoice_ref_no=data.get("invoice_ref_no"),
            scenario_id=data.get("scenario_id"),
            income_tax=data.get("income_tax", "236G"),
            items=data.get("items", []),
            environment=Environment(data.get("environment", "SANDBOX")),
            status=InvoiceStatus.VALIDATED,
            validated_at=datetime.utcnow(),
            source="manual",
            automation_invoice_id=automation_invoice.id,  # Stored for duplicate detection, hidden from API
            transferred_at=None,
        )
        return invoice

    def check_duplicate(self, main_db, user_id: UUID, automation_invoice_id: UUID) -> bool:
        """
        Check if an automation invoice has already been transferred.

        Returns True if a matching invoice exists in the main database.
        """
        existing = main_db.exec(
            select(Invoice).where(
                Invoice.user_id == user_id,
                Invoice.automation_invoice_id == automation_invoice_id,
                Invoice.is_deleted == False,
            )
        ).first()
        return existing is not None

    def classify_error(self, error: Exception) -> str:
        """
        Classify an exception into a human-readable error category.

        Used for structured error tracking on AutomationInvoice.transfer_error.
        """
        name = type(error).__name__

        if name in ("IntegrityError", "UniqueViolation"):
            return "duplicate"
        if name in ("DBAPIError", "OperationalError", "DatabaseError"):
            return "database"
        if name in ("TimeoutError", "ConnectTimeout", "ConnectionError"):
            return "timeout"
        if name in ("ValidationError", "ValueError", "TypeError", "KeyError"):
            return "validation"
        return "unknown"
