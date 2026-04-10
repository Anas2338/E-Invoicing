"""
Unit tests for ExcelService.
"""
import pytest
from io import BytesIO
from datetime import datetime, date, time
from pathlib import Path
import pandas as pd
from uuid import uuid4

from src.services.excel_service import ExcelService
from src.models.excel_upload_session import ExcelUploadSession, ExcelUploadProcessingStatus
from src.utils.excel_validator import ExcelValidator


class TestExcelService:
    """Test suite for ExcelService."""

    def test_generate_excel_template(self, db_session):
        """Test template generation returns valid Excel file."""
        service = ExcelService(db_session)
        template = service.generate_excel_template()

        assert isinstance(template, BytesIO)
        assert template.tell() == 0  # File pointer at start

        # Read template and verify structure
        df = pd.read_excel(template, engine='openpyxl')
        expected_columns = [
            # Invoice identification
            "invoice_number", "invoice_type", "invoice_date",
            # Seller information
            "seller_ntn_cnic", "seller_business_name", "seller_province", "seller_address",
            # Buyer information
            "buyer_ntn_cnic", "buyer_business_name", "buyer_province", "buyer_address", "buyer_registration_type",
            # Item details - FBR-compliant
            "hs_code", "product_description", "tax_rate", "uom", "quantity",
            "total_values", "value_sales_excluding_st", "fixed_notified_value_or_retail_price",
            "sales_tax_applicable", "sales_tax_withheld_at_source", "extra_tax", "further_tax",
            "sro_schedule_no", "fed_payable", "discount", "sale_type", "sro_item_serial_no",
            # Optional fields
            "invoice_ref_no", "scenario_id",
            # Scheduling
            "scheduled_date", "scheduled_time",
            # Environment
            "environment",
            # Status fields
            "status", "reason"
        ]
        assert list(df.columns) == expected_columns

        # Verify sample row exists
        assert len(df) == 1
        assert df.iloc[0]['invoice_number'] == 'INV-001'

    def test_validate_excel_structure_valid(self, db_session, tmp_path):
        """Test validation passes for valid Excel structure."""
        service = ExcelService(db_session)

        # Create valid Excel file with FBR-compliant columns
        df = pd.DataFrame({
            "invoice_number": ["INV-001"],
            "invoice_type": ["Sale Invoice"],
            "invoice_date": ["2026-04-10"],
            "seller_ntn_cnic": ["1234567"],
            "seller_business_name": ["ABC Company"],
            "seller_province": ["Punjab"],
            "seller_address": ["123 Main Street"],
            "buyer_ntn_cnic": ["7654321"],
            "buyer_business_name": ["XYZ Corp"],
            "buyer_province": ["Sindh"],
            "buyer_address": ["456 Business Ave"],
            "buyer_registration_type": ["Registered"],
            "hs_code": ["8471.30.00"],
            "product_description": ["Laptop"],
            "tax_rate": ["18"],
            "uom": ["NOS"],
            "quantity": [1],
            "total_values": [118000],
            "value_sales_excluding_st": [100000],
            "fixed_notified_value_or_retail_price": [0],
            "sales_tax_applicable": [18000],
            "sales_tax_withheld_at_source": [0],
            "extra_tax": [0],
            "further_tax": [0],
            "sro_schedule_no": [""],
            "fed_payable": [0],
            "discount": [0],
            "sale_type": ["01"],
            "sro_item_serial_no": [""],
            "invoice_ref_no": [""],
            "scenario_id": ["SN001"],
            "scheduled_date": ["2026-04-10"],
            "scheduled_time": ["10:00"],
            "environment": ["SANDBOX"],
            "status": [""],
            "reason": [""]
        })

        file_path = tmp_path / "valid.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        is_valid, error = service.validate_excel_structure(str(file_path))
        assert is_valid is True
        assert error is None

    def test_validate_excel_structure_missing_columns(self, db_session, tmp_path):
        """Test validation fails for missing required columns."""
        service = ExcelService(db_session)

        # Create Excel with missing columns
        df = pd.DataFrame({
            "invoice_number": ["INV-001"],
            "customer_name": ["Test Customer"],
            # Missing other required columns
        })

        file_path = tmp_path / "invalid.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        is_valid, error = service.validate_excel_structure(str(file_path))
        assert is_valid is False
        assert "Missing required columns" in error

    def test_validate_excel_structure_empty_file(self, db_session, tmp_path):
        """Test validation fails for empty Excel file."""
        service = ExcelService(db_session)

        # Create empty Excel file
        df = pd.DataFrame()
        file_path = tmp_path / "empty.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        is_valid, error = service.validate_excel_structure(str(file_path))
        assert is_valid is False
        assert "empty" in error.lower()

    def test_check_duplicate_invoices_no_duplicates(self, db_session, tmp_path):
        """Test duplicate check passes when no duplicates exist."""
        service = ExcelService(db_session)

        df = pd.DataFrame({
            "invoice_number": ["INV-001", "INV-002", "INV-003"],
            "customer_name": ["Customer 1", "Customer 2", "Customer 3"],
            "items": ["Product A", "Product B", "Product C"],
            "amount": [10000, 20000, 30000],
            "tax": [1800, 3600, 5400],
            "scheduled_date": ["2026-04-05", "2026-04-05", "2026-04-05"],
            "scheduled_time": ["10:00", "11:00", "12:00"],
            "status": ["", "", ""],
            "reason": ["", "", ""]
        })

        file_path = tmp_path / "no_duplicates.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        is_valid, error = service.check_duplicate_invoices(str(file_path))
        assert is_valid is True
        assert error is None

    def test_check_duplicate_invoices_with_duplicates(self, db_session, tmp_path):
        """Test duplicate check fails when duplicates exist."""
        service = ExcelService(db_session)

        df = pd.DataFrame({
            "invoice_number": ["INV-001", "INV-002", "INV-001"],  # Duplicate INV-001
            "customer_name": ["Customer 1", "Customer 2", "Customer 3"],
            "items": ["Product A", "Product B", "Product C"],
            "amount": [10000, 20000, 30000],
            "tax": [1800, 3600, 5400],
            "scheduled_date": ["2026-04-05", "2026-04-05", "2026-04-05"],
            "scheduled_time": ["10:00", "11:00", "12:00"],
            "status": ["", "", ""],
            "reason": ["", "", ""]
        })

        file_path = tmp_path / "with_duplicates.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        is_valid, error = service.check_duplicate_invoices(str(file_path))
        assert is_valid is False
        assert "Duplicate invoice numbers" in error
        assert "INV-001" in error

    def test_parse_excel_file_valid(self, db_session, tmp_path):
        """Test parsing valid Excel file returns invoice data."""
        service = ExcelService(db_session)

        df = pd.DataFrame({
            "invoice_number": ["INV-100", "INV-101"],
            "invoice_type": ["Sale Invoice", "Sale Invoice"],
            "invoice_date": ["2026-04-10", "2026-04-11"],
            "seller_ntn_cnic": ["1234567", "1234567"],
            "seller_business_name": ["ABC Company", "ABC Company"],
            "seller_province": ["Punjab", "Punjab"],
            "seller_address": ["123 Main Street", "123 Main Street"],
            "buyer_ntn_cnic": ["7654321", "9876543"],
            "buyer_business_name": ["Customer 1", "Customer 2"],
            "buyer_province": ["Sindh", "KPK"],
            "buyer_address": ["456 Business Ave", "789 Trade St"],
            "buyer_registration_type": ["Registered", "Registered"],
            "hs_code": ["8471.30.00", "8471.30.00"],
            "product_description": ["Product A", "Product B"],
            "tax_rate": ["18", "18"],
            "uom": ["NOS", "NOS"],
            "quantity": [1, 2],
            "total_values": [118000, 236000],
            "value_sales_excluding_st": [100000, 200000],
            "fixed_notified_value_or_retail_price": [0, 0],
            "sales_tax_applicable": [18000, 36000],
            "sales_tax_withheld_at_source": [0, 0],
            "extra_tax": [0, 0],
            "further_tax": [0, 0],
            "sro_schedule_no": ["", ""],
            "fed_payable": [0, 0],
            "discount": [0, 0],
            "sale_type": ["01", "01"],
            "sro_item_serial_no": ["", ""],
            "invoice_ref_no": ["", ""],
            "scenario_id": ["SN001", "SN002"],
            "scheduled_date": ["2026-04-05", "2026-04-06"],
            "scheduled_time": ["10:00", "11:00"],
            "environment": ["SANDBOX", "SANDBOX"],
            "status": ["", ""],
            "reason": ["", ""]
        })

        file_path = tmp_path / "valid.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        invoices = service.parse_excel_file(str(file_path))

        assert len(invoices) == 2
        assert invoices[0]['invoice_data']['invoice_number'] == 'INV-100'
        assert invoices[0]['invoice_data']['buyer_business_name'] == 'Customer 1'
        assert invoices[0]['invoice_data']['items'][0]['total_values'] == 118000.0
        assert invoices[0]['invoice_data']['items'][0]['sales_tax_applicable'] == 18000.0
        assert isinstance(invoices[0]['scheduled_date'], date)
        assert isinstance(invoices[0]['scheduled_time'], time)

    def test_parse_excel_file_removes_sample_row(self, db_session, tmp_path):
        """Test parsing removes sample row from template."""
        service = ExcelService(db_session)

        df = pd.DataFrame({
            "invoice_number": ["INV-001", "INV-002"],
            "invoice_type": ["Sale Invoice", "Sale Invoice"],
            "invoice_date": ["2026-04-10", "2026-04-11"],
            "seller_ntn_cnic": ["1234567", "1234567"],
            "seller_business_name": ["ABC Company", "ABC Company"],
            "seller_province": ["Punjab", "Punjab"],
            "seller_address": ["123 Main Street", "123 Main Street"],
            "buyer_ntn_cnic": ["7654321", "9876543"],
            "buyer_business_name": ["Example Customer", "Real Customer"],
            "buyer_province": ["Sindh", "KPK"],
            "buyer_address": ["456 Business Ave", "789 Trade St"],
            "buyer_registration_type": ["Registered", "Registered"],
            "hs_code": ["8471.30.00", "8471.30.00"],
            "product_description": ["Product A", "Product C"],
            "tax_rate": ["18", "18"],
            "uom": ["NOS", "NOS"],
            "quantity": [1, 2],
            "total_values": [118000, 236000],
            "value_sales_excluding_st": [100000, 200000],
            "fixed_notified_value_or_retail_price": [0, 0],
            "sales_tax_applicable": [18000, 36000],
            "sales_tax_withheld_at_source": [0, 0],
            "extra_tax": [0, 0],
            "further_tax": [0, 0],
            "sro_schedule_no": ["", ""],
            "fed_payable": [0, 0],
            "discount": [0, 0],
            "sale_type": ["01", "01"],
            "sro_item_serial_no": ["", ""],
            "invoice_ref_no": ["", ""],
            "scenario_id": ["SN001", "SN002"],
            "scheduled_date": ["2026-04-04", "2026-04-05"],
            "scheduled_time": ["10:00", "11:00"],
            "environment": ["SANDBOX", "SANDBOX"],
            "status": ["", ""],
            "reason": ["", ""]
        })

        file_path = tmp_path / "with_sample.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        invoices = service.parse_excel_file(str(file_path))

        # Should skip first row (INV-001 sample) and only return INV-002
        assert len(invoices) == 1
        assert invoices[0]['invoice_data']['invoice_number'] == 'INV-002'

    def test_check_concurrent_upload_no_existing(self, db_session):
        """Test concurrent check returns None when no upload in progress."""
        service = ExcelService(db_session)
        user_id = uuid4()

        result = service.check_concurrent_upload(user_id)
        assert result is None

    def test_check_concurrent_upload_existing_processing(self, db_session):
        """Test concurrent check returns session when upload in progress."""
        service = ExcelService(db_session)
        user_id = uuid4()

        # Create processing session
        session = ExcelUploadSession(
            user_id=user_id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=10,
            processing_status=ExcelUploadProcessingStatus.PROCESSING
        )
        db_session.add(session)
        db_session.commit()

        result = service.check_concurrent_upload(user_id)
        assert result is not None
        assert result.id == session.id
        assert result.processing_status == ExcelUploadProcessingStatus.PROCESSING

    def test_check_concurrent_upload_completed_session(self, db_session):
        """Test concurrent check returns None for completed sessions."""
        service = ExcelService(db_session)
        user_id = uuid4()

        # Create completed session
        session = ExcelUploadSession(
            user_id=user_id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=10,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()

        result = service.check_concurrent_upload(user_id)
        assert result is None


@pytest.fixture
def db_session():
    """Mock database session for testing."""
    from sqlmodel import Session, create_engine, SQLModel
    from sqlalchemy.pool import StaticPool

    # Import all models to register them with SQLModel
    from src.models.user import User
    from src.models.automation_invoice import AutomationInvoice
    from src.models.automation_log import AutomationLog
    from src.models.excel_upload_session import ExcelUploadSession

    # Create in-memory SQLite database for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session
