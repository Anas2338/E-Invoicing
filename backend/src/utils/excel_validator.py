"""
Excel file validation utilities.
"""
from typing import Optional, Union
from io import BytesIO
import pandas as pd
from pathlib import Path


class ExcelValidationError(Exception):
    """Custom exception for Excel validation errors."""
    pass


class ExcelValidator:
    """Validator for Excel file structure and content."""

    # Required columns for invoice automation Excel template (simplified with saved_item_code)
    REQUIRED_COLUMNS = [
        # Invoice identification
        "invoice_number",
        "invoice_type",
        "invoice_date",

        # Buyer information
        "buyer_ntn_cnic",
        "buyer_business_name",
        "buyer_province",
        "buyer_address",
        "buyer_registration_type",

        # Item details - simplified with saved_item_code
        "saved_item_code",
        "quantity",
        "value_sales_excluding_st",
        "fixed_notified_value_or_retail_price",
        "further_tax",
        "discount",
        "income_tax",

        # Scheduling
        "scheduled_date",
        "scheduled_time",

        # Status fields
        "status",
        "reason"
    ]

    # Required columns for manual invoice Excel template
    # Same as automation but without scheduled_date/scheduled_time, with income_tax added
    MANUAL_REQUIRED_COLUMNS = [
        # Invoice identification
        "invoice_number",
        "invoice_type",
        "invoice_date",

        # Buyer information
        "buyer_ntn_cnic",
        "buyer_business_name",
        "buyer_province",
        "buyer_address",
        "buyer_registration_type",

        # Item details - simplified with saved_item_code
        "saved_item_code",
        "quantity",
        "value_sales_excluding_st",
        "fixed_notified_value_or_retail_price",
        "further_tax",
        "discount",

        # Income tax
        "income_tax",
    ]

    # Maximum file size in bytes (10 MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Maximum number of rows
    MAX_ROWS = 20000

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """
        Validate file has .xlsx extension.

        Args:
            filename: Filename to validate

        Returns:
            True if valid, False otherwise
        """
        return filename.lower().endswith('.xlsx')

    @staticmethod
    def validate_file_size(file_source: Union[str, BytesIO]) -> bool:
        """
        Validate file size is within limits.

        Args:
            file_source: Path to file or BytesIO object

        Returns:
            True if valid, False otherwise

        Raises:
            ExcelValidationError: If file size exceeds limit
        """
        if isinstance(file_source, BytesIO):
            file_size = file_source.getbuffer().nbytes
        else:
            file_size = Path(file_source).stat().st_size

        if file_size > ExcelValidator.MAX_FILE_SIZE:
            raise ExcelValidationError(
                f"File size ({file_size} bytes) exceeds maximum allowed size "
                f"({ExcelValidator.MAX_FILE_SIZE} bytes)"
            )
        return True

    @staticmethod
    def validate_excel_structure(file_source: Union[str, BytesIO]) -> tuple[bool, Optional[str]]:
        """
        Validate Excel file has required columns.

        Args:
            file_source: Path to Excel file or BytesIO object

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Read Excel file (pandas handles both str and BytesIO)
            df = pd.read_excel(file_source, engine='openpyxl')

            # Check if file is empty
            if df.empty:
                return False, "Excel file is empty"

            # Check row count
            if len(df) > ExcelValidator.MAX_ROWS:
                return False, f"Excel file has {len(df)} rows, maximum allowed is {ExcelValidator.MAX_ROWS}"

            # Get actual columns (strip whitespace)
            actual_columns = [col.strip() for col in df.columns]

            # Check for required columns
            missing_columns = []
            for required_col in ExcelValidator.REQUIRED_COLUMNS:
                if required_col not in actual_columns:
                    missing_columns.append(required_col)

            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}"

            return True, None

        except Exception as e:
            return False, f"Error reading Excel file: {str(e)}"

    @staticmethod
    def validate_no_duplicate_invoices(file_source: Union[str, BytesIO]) -> tuple[bool, Optional[str]]:
        """
        Validate Excel file has no duplicate invoice numbers.

        Args:
            file_source: Path to Excel file or BytesIO object

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            df = pd.read_excel(file_source, engine='openpyxl')

            # Check for duplicate invoice numbers
            invoice_numbers = df['invoice_number'].dropna()
            duplicates = invoice_numbers[invoice_numbers.duplicated()].unique()

            if len(duplicates) > 0:
                duplicate_list = ', '.join(str(inv) for inv in duplicates[:5])
                if len(duplicates) > 5:
                    duplicate_list += f" (and {len(duplicates) - 5} more)"
                return False, f"Duplicate invoice numbers found: {duplicate_list}"

            return True, None

        except Exception as e:
            return False, f"Error checking for duplicates: {str(e)}"

    @staticmethod
    def validate_excel_file(file_source: Union[str, BytesIO]) -> tuple[bool, list[str]]:
        """
        Run all validations on Excel file.

        Args:
            file_source: Path to Excel file or BytesIO object

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate file size
        try:
            ExcelValidator.validate_file_size(file_source)
        except ExcelValidationError as e:
            errors.append(str(e))
            return False, errors

        # Validate structure
        is_valid, error_msg = ExcelValidator.validate_excel_structure(file_source)
        if not is_valid:
            errors.append(error_msg)

        # Validate no duplicates
        is_valid, error_msg = ExcelValidator.validate_no_duplicate_invoices(file_source)
        if not is_valid:
            errors.append(error_msg)

        return len(errors) == 0, errors

    @staticmethod
    def validate_manual_excel_structure(file_source: Union[str, BytesIO]) -> tuple[bool, Optional[str]]:
        """
        Validate manual Excel file has the required columns for manual invoice upload.

        Args:
            file_source: Path to Excel file or BytesIO object

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            df = pd.read_excel(file_source, engine='openpyxl')

            if df.empty:
                return False, "Excel file is empty"

            if len(df) > ExcelValidator.MAX_ROWS:
                return False, f"Excel file has {len(df)} rows, maximum allowed is {ExcelValidator.MAX_ROWS}"

            actual_columns = [col.strip() for col in df.columns]

            missing_columns = []
            for required_col in ExcelValidator.MANUAL_REQUIRED_COLUMNS:
                if required_col not in actual_columns:
                    missing_columns.append(required_col)

            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}"

            return True, None

        except Exception as e:
            return False, f"Error reading Excel file: {str(e)}"

    @staticmethod
    def validate_manual_excel_file(file_source: Union[str, BytesIO]) -> tuple[bool, list[str]]:
        """
        Run all validations on manual Excel file.
        Note: Duplicate invoice numbers are allowed — they represent multi-item invoices.

        Args:
            file_source: Path to Excel file or BytesIO object

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        try:
            ExcelValidator.validate_file_size(file_source)
        except ExcelValidationError as e:
            errors.append(str(e))
            return False, errors

        is_valid, error_msg = ExcelValidator.validate_manual_excel_structure(file_source)
        if not is_valid:
            errors.append(error_msg)

        return len(errors) == 0, errors
