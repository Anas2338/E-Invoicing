"""
TransferService: Transfers validated automation invoices to the main database.

Handles data transformation from AutomationInvoice (JSON-based) to the
structured Invoice model, duplicate detection, and error classification.

All automation traces are hidden — transferred invoices appear identical
to manually created invoices (source="manual", normal status flow).

Invoice numbering: numbers are NOT assigned at upload time anymore. Each
invoice receives its next number here, at transfer time, via
InvoiceNumberAssigner (seeded from the user's numbering settings and the
external_ids already present in the main DB).
"""
import logging
from typing import Any, Optional
from datetime import datetime
from uuid import UUID

from sqlmodel import select

from src.models.invoice import Invoice, InvoiceStatus, Environment
from src.models.automation_invoice import AutomationInvoice
from src.services.excel_service import _AutoInvoiceNumberGenerator

logger = logging.getLogger(__name__)


class InvoiceNumberAssigner:
    """Assigns the next invoice number per user at transfer time.

    One generator per user, seeded from the user's numbering settings
    (prefix/start number/padding/include_year) and the external_ids already
    in the main DB. The main-DB snapshot is taken on the first invoice of a
    user within a transfer cycle and then advanced by the generator, so all
    of that user's invoices in the cycle get distinct sequential numbers.
    """

    def __init__(self, main_db):
        self.main_db = main_db
        self._generators: dict[UUID, _AutoInvoiceNumberGenerator] = {}

    def next_for(self, user_id: UUID) -> str:
        """Return the next invoice number for a user, assigning in schedule order."""
        generator = self._generators.get(user_id)
        if generator is None:
            generator = self._build_generator(user_id)
            self._generators[user_id] = generator
        return generator.next()

    def _build_generator(self, user_id: UUID) -> _AutoInvoiceNumberGenerator:
        from src.models.user import User

        user = self.main_db.get(User, user_id)
        taken = set(
            self.main_db.exec(
                select(Invoice.external_id).where(
                    Invoice.user_id == user_id,
                    Invoice.is_deleted == False,
                )
            ).all()
        )
        return _AutoInvoiceNumberGenerator(
            prefix=(user.invoice_prefix if user else None) or "INV-",
            start_number=(user.invoice_start_number if user else None) or 1,
            padding=(user.invoice_padding if user else None) or 4,
            include_year=bool(user.invoice_include_year) if user else False,
            taken=taken,
        )


class TransferService:
    """Transforms and transfers automation invoices into the main invoice table."""

    def transform_invoice_data(
        self,
        automation_invoice: AutomationInvoice,
        external_id: Optional[str] = None,
    ) -> Invoice:
        """
        Transform an AutomationInvoice into a main Invoice model.

        The invoice number is supplied by the caller — it is assigned at
        transfer time (see InvoiceNumberAssigner). When omitted, it falls
        back to the automation row's stored number for backward compatibility.

        Automation traces are hidden:
        - source set to "manual" (indistinguishable from manual invoices)
        - status set to VALIDATED (already validated before transfer)
        - automation_invoice_id stored for duplicate detection but hidden from API
        """
        data: dict[str, Any] = automation_invoice.invoice_data or {}

        invoice = Invoice(
            external_id=external_id or automation_invoice.invoice_number,
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
            items=self._normalize_items_income_tax(data.get("items", []), data.get("income_tax", "236G")),
            environment=Environment(data.get("environment", "SANDBOX")),
            status=InvoiceStatus.VALIDATED,
            validated_at=datetime.utcnow(),
            source="manual",
            automation_invoice_id=automation_invoice.id,
            transferred_at=None,
        )
        return invoice

    @staticmethod
    def _normalize_items_income_tax(items: list, fallback_income_tax: str = "236G") -> list:
        """
        Ensure every item has income_tax_type and withholding_tax_amount.
        Auto-defaults to fallback_income_tax and calculates WHT if missing.
        """
        WHT_RATES = {"236G": 0.001, "236H": 0.005, "None": 0}
        for item in items:
            if not item.get("income_tax_type"):
                item["income_tax_type"] = fallback_income_tax
            # If income tax type is None, set WHT to 0 and skip auto-calc
            if item["income_tax_type"] == "None":
                item["withholding_tax_amount"] = 0
                continue
            if not item.get("withholding_tax_amount") and item.get("value_sales_excluding_st"):
                rate = WHT_RATES.get(item["income_tax_type"], 0.001)
                item["withholding_tax_amount"] = round(float(item["value_sales_excluding_st"]) * rate, 2)
        return items

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
