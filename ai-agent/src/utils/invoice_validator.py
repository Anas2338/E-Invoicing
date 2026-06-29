"""
Input validation utilities for invoice data.

Validates:
- NTN/CNIC format and checksums
- Numeric ranges and constraints
- Date validity
- Business logic rules
"""

import re
from datetime import date, datetime
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class InvoiceValidator:
    """Comprehensive invoice data validation."""

    # NTN format: Flexible pattern to accept various formats
    # - 7 digits (e.g., "1234567")
    # - Letter + 6-7 digits (e.g., "A123456", "A1234567")
    # - With optional dashes (e.g., "1234567-8")
    NTN_PATTERN = re.compile(r'^[A-Z]?\d{6,7}(-\d)?$')

    # CNIC format: 13 digits with optional dashes (XXXXX-XXXXXXX-X)
    CNIC_PATTERN = re.compile(r'^\d{5}-?\d{7}-?\d{1}$')

    # Relaxed NTN/CNIC pattern: Accept alphanumeric strings of reasonable length
    # Let FBR API be the final validator
    RELAXED_NTN_CNIC_PATTERN = re.compile(r'^[A-Z0-9][A-Z0-9\-]{5,14}$', re.IGNORECASE)

    # Valid invoice types (case-insensitive)
    VALID_INVOICE_TYPES = {
        'sale invoice', 'purchase invoice', 'credit note', 'debit note'
    }

    @staticmethod
    def validate_ntn(ntn: str) -> Tuple[bool, Optional[str]]:
        """
        Validate NTN (National Tax Number) format.
        Uses relaxed validation - FBR API is the final validator.

        Args:
            ntn: NTN to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not ntn:
            return False, "NTN is required"

        # Remove spaces and convert to string
        ntn = str(ntn).strip().replace(' ', '')

        # Use relaxed pattern to accept various formats
        if not InvoiceValidator.RELAXED_NTN_CNIC_PATTERN.match(ntn):
            return False, "Invalid NTN format. Expected: 7 digits (e.g., 1234567) or letter + digits (e.g., A123456)"

        return True, None

    @staticmethod
    def validate_cnic(cnic: str) -> Tuple[bool, Optional[str]]:
        """
        Validate CNIC (Computerized National Identity Card) format.
        Uses relaxed validation - FBR API is the final validator.

        Args:
            cnic: CNIC to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not cnic:
            return False, "CNIC is required"

        # Remove spaces and convert to string
        cnic = str(cnic).strip().replace(' ', '')

        # Use relaxed pattern to accept various formats
        if not InvoiceValidator.RELAXED_NTN_CNIC_PATTERN.match(cnic):
            return False, "Invalid CNIC format. Expected: 13 digits (e.g., 12345-1234567-1 or 1234512345671)"

        return True, None

    @staticmethod
    def validate_ntn_or_cnic(value: str, allow_empty: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate NTN or CNIC (accepts either format).
        Uses relaxed validation - FBR API is the final validator.

        Args:
            value: NTN or CNIC to validate
            allow_empty: If True, empty values are considered valid

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            if allow_empty:
                return True, None
            return False, "NTN/CNIC is required"

        # Remove spaces and convert to string
        value = str(value).strip().replace(' ', '')

        # Handle float-to-string artifacts (e.g., "1234567.0" → "1234567")
        if value.endswith(".0") and len(value) > 2:
            value = value[:-2]

        # Use relaxed pattern - accept alphanumeric strings of reasonable length
        if not InvoiceValidator.RELAXED_NTN_CNIC_PATTERN.match(value):
            return False, "Invalid NTN/CNIC format. Expected: 7-digit NTN (e.g., 1234567, A123456) or 13-digit CNIC (e.g., 1234512345671)"

        return True, None

    @staticmethod
    def validate_province(province: str) -> Tuple[bool, Optional[str]]:
        """
        Validate province name (non-empty check only).

        Note: Province names come from FBR API and may vary in format.
        The FBR API is the source of truth for valid provinces.

        Args:
            province: Province name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not province:
            return False, "Province is required"

        province = province.strip()

        if not province:
            return False, "Province cannot be empty"

        return True, None

    @staticmethod
    def validate_invoice_date(invoice_date: date) -> Tuple[bool, Optional[str]]:
        """
        Validate invoice date.

        Args:
            invoice_date: Invoice date to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not invoice_date:
            return False, "Invoice date is required"

        today = date.today()

        # Allow future dates for scheduled invoices (automation system)
        # Add reasonable upper limit: not more than 1 year in the future
        one_year_future = date(today.year + 1, today.month, today.day)
        if invoice_date > one_year_future:
            return False, f"Invoice date cannot be more than 1 year in the future. Maximum date: {one_year_future}"

        # Invoice date cannot be more than 1 year old (business rule)
        one_year_ago = date(today.year - 1, today.month, today.day)
        if invoice_date < one_year_ago:
            return False, f"Invoice date cannot be more than 1 year old. Minimum date: {one_year_ago}"

        return True, None

    @staticmethod
    def validate_amount(amount: float, field_name: str, min_value: float = 0, max_value: float = 999999999) -> Tuple[bool, Optional[str]]:
        """
        Validate numeric amount.

        Args:
            amount: Amount to validate
            field_name: Name of the field (for error messages)
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Tuple of (is_valid, error_message)
        """
        if amount is None:
            return False, f"{field_name} is required"

        # Check if negative
        if amount < min_value:
            return False, f"{field_name} cannot be less than {min_value}"

        # Check if exceeds maximum
        if amount > max_value:
            return False, f"{field_name} cannot exceed {max_value}"

        # Check for reasonable precision (max 2 decimal places for currency)
        if round(amount, 2) != amount:
            return False, f"{field_name} must have at most 2 decimal places"

        return True, None

    @staticmethod
    def validate_quantity(quantity: float) -> Tuple[bool, Optional[str]]:
        """
        Validate item quantity.

        Args:
            quantity: Quantity to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if quantity is None:
            return False, "Quantity is required"

        if quantity <= 0:
            return False, "Quantity must be greater than 0"

        if quantity > 1000000:
            return False, "Quantity cannot exceed 1,000,000"

        return True, None

    @staticmethod
    def validate_invoice_data(invoice_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive validation of invoice data.

        Args:
            invoice_data: Invoice data dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate seller NTN/CNIC
        seller_ntn = invoice_data.get('seller_ntn_cnic', '')
        is_valid, error = InvoiceValidator.validate_ntn_or_cnic(seller_ntn)
        if not is_valid:
            return False, f"Seller {error}"

        # Validate buyer NTN/CNIC (required for registered buyers, optional for unregistered)
        buyer_ntn = invoice_data.get('buyer_ntn_cnic', '')
        buyer_reg_type = invoice_data.get('buyer_registration_type', '').strip()
        allow_empty_buyer_ntn = buyer_reg_type != "Registered"
        is_valid, error = InvoiceValidator.validate_ntn_or_cnic(buyer_ntn, allow_empty=allow_empty_buyer_ntn)
        if not is_valid:
            error_msg = error
            if buyer_reg_type == "Registered" and not buyer_ntn:
                error_msg = "Buyer NTN/CNIC is required for registered buyers"
            return False, error_msg

        # Validate seller province
        seller_province = invoice_data.get('seller_province', '')
        is_valid, error = InvoiceValidator.validate_province(seller_province)
        if not is_valid:
            return False, f"Seller {error}"

        # Validate buyer province
        buyer_province = invoice_data.get('buyer_province', '')
        is_valid, error = InvoiceValidator.validate_province(buyer_province)
        if not is_valid:
            return False, f"Buyer {error}"

        # Validate invoice date
        invoice_date_str = invoice_data.get('invoice_date', '')
        try:
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
            is_valid, error = InvoiceValidator.validate_invoice_date(invoice_date)
            if not is_valid:
                return False, error
        except ValueError:
            return False, "Invalid invoice date format. Expected: YYYY-MM-DD"

        # Validate invoice type (case-insensitive)
        invoice_type = invoice_data.get('invoice_type', '').strip()
        if not invoice_type:
            return False, "Invoice type is required"

        invoice_type_lower = invoice_type.lower()
        if invoice_type_lower not in InvoiceValidator.VALID_INVOICE_TYPES:
            return False, f"Invalid invoice type '{invoice_type}'. Must be one of: Sale Invoice, Purchase Invoice, Credit Note, Debit Note"

        # Validate items
        items = invoice_data.get('items', [])
        if not items:
            return False, "Invoice must have at least one item"

        for idx, item in enumerate(items, 1):
            # Validate quantity
            quantity = item.get('quantity', 0)
            is_valid, error = InvoiceValidator.validate_quantity(quantity)
            if not is_valid:
                return False, f"Item {idx}: {error}"

            # Validate amounts
            amount_fields = [
                ('total_values', 'Total value'),
                ('value_sales_excluding_st', 'Value excluding sales tax'),
                ('sales_tax_applicable', 'Sales tax'),
            ]

            for field, label in amount_fields:
                amount = item.get(field, 0)
                is_valid, error = InvoiceValidator.validate_amount(amount, label)
                if not is_valid:
                    return False, f"Item {idx}: {error}"

            # Business logic: total_values = max(value_excl, fixed_price) + sales_tax + further_tax - discount
            total = item.get('total_values', 0)
            value_excl_tax = item.get('value_sales_excluding_st', 0)
            fixed_price = item.get('fixed_notified_value_or_retail_price', 0)
            tax = item.get('sales_tax_applicable', 0)
            further_tax = item.get('further_tax', 0)
            discount = item.get('discount', 0)

            base_value = max(value_excl_tax, fixed_price)
            expected_total = round(base_value + tax + further_tax - discount, 2)
            if abs(total - expected_total) > 0.01:  # Allow 1 cent rounding difference
                return False, f"Item {idx}: Total value ({total}) must equal base value ({base_value}) + sales tax ({tax}) + further tax ({further_tax}) - discount ({discount})"

        logger.info("Invoice data validation passed")
        return True, None
