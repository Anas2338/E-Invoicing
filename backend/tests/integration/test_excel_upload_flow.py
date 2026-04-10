"""
Integration tests for Excel upload flow.
"""
import pytest
from io import BytesIO
from datetime import date, time
import pandas as pd
from uuid import uuid4
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool

from src.services.excel_service import ExcelService
from src.services.automation_service import AutomationService
from src.utils.file_storage import FileStorageService
from src.models.user import User
from src.models.excel_upload_session import ExcelUploadProcessingStatus
from src.models.automation_invoice import AutomationInvoiceStatus


@pytest.fixture
def db_session():
    """Create in-memory database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        hashed_password="hashed_password",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def file_storage(tmp_path):
    """Create file storage service with temp directory."""
    return FileStorageService(base_upload_dir=str(tmp_path / "uploads"))


class TestExcelUploadFlow:
    """Integration tests for complete Excel upload flow."""

    def test_complete_upload_flow_success(self, db_session, test_user, file_storage, tmp_path):
        """Test complete successful upload flow from template to storage."""
        excel_service = ExcelService(db_session)
        automation_service = AutomationService(db_session)

        # Step 1: Generate template
        template = excel_service.generate_excel_template()
        assert template is not None

        # Step 2: Create valid Excel file with FBR-compliant columns
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
            "tax_rate": ["18%", "18%"],
            "uom": ["PCE", "PCE"],
            "quantity": [1, 2],
            "unit_price": [10000, 20000],
            "discount": [0, 0],
            "sales_tax_applicable": [1800, 7200],
            "invoice_ref_no": ["", ""],
            "scenario_id": ["SN001", "SN002"],
            "scheduled_date": ["2026-04-10", "2026-04-11"],  # Future dates
            "scheduled_time": ["10:00", "11:00"],
            "environment": ["SANDBOX", "SANDBOX"],
            "status": ["", ""],
            "reason": ["", ""]
        })

        file_path = tmp_path / "test_upload.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        # Step 3: Validate Excel structure
        is_valid, error = excel_service.validate_excel_structure(str(file_path))
        assert is_valid is True

        # Step 4: Check for duplicates
        is_valid, error = excel_service.check_duplicate_invoices(str(file_path))
        assert is_valid is True

        # Step 5: Check concurrent upload
        existing = excel_service.check_concurrent_upload(test_user.id)
        assert existing is None

        # Step 6: Parse Excel file
        invoices = excel_service.parse_excel_file(str(file_path))
        assert len(invoices) == 2

        # Step 7: Create upload session
        session = automation_service.create_upload_session(
            user_id=test_user.id,
            file_path=str(file_path),
            original_filename="test_upload.xlsx",
            total_rows=len(invoices)
        )
        assert session.processing_status == ExcelUploadProcessingStatus.PROCESSING

        # Step 8: Store invoices
        created_invoices = automation_service.store_invoices_from_excel(
            user_id=test_user.id,
            session_id=session.id,
            invoices=invoices
        )
        assert len(created_invoices) == 2

        # Step 9: Mark past invoices as expired
        expired_count = automation_service.mark_past_invoices_as_expired(
            user_id=test_user.id,
            session_id=session.id
        )
        # Future dates should not be expired
        assert expired_count == 0

        # Step 10: Update session status
        session.processing_status = ExcelUploadProcessingStatus.COMPLETED
        session.processed_rows = len(invoices)
        db_session.add(session)
        db_session.commit()

        # Verify final state
        db_session.refresh(session)
        assert session.processing_status == ExcelUploadProcessingStatus.COMPLETED
        assert session.processed_rows == 2

    def test_upload_flow_with_duplicate_invoices(self, db_session, test_user, tmp_path):
        """Test upload flow fails with duplicate invoice numbers."""
        excel_service = ExcelService(db_session)

        # Create Excel with duplicates
        df = pd.DataFrame({
            "invoice_number": ["INV-001", "INV-001"],  # Duplicate
            "customer_name": ["Customer 1", "Customer 2"],
            "items": ["Product A", "Product B"],
            "amount": [10000, 20000],
            "tax": [1800, 3600],
            "scheduled_date": ["2026-04-05", "2026-04-06"],
            "scheduled_time": ["10:00", "11:00"],
            "status": ["", ""],
            "reason": ["", ""]
        })

        file_path = tmp_path / "duplicates.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        # Validation should fail
        is_valid, error = excel_service.check_duplicate_invoices(str(file_path))
        assert is_valid is False
        assert "Duplicate invoice numbers" in error

    def test_upload_flow_with_missing_columns(self, db_session, test_user, tmp_path):
        """Test upload flow fails with missing required columns."""
        excel_service = ExcelService(db_session)

        # Create Excel with missing columns
        df = pd.DataFrame({
            "invoice_number": ["INV-001"],
            "customer_name": ["Customer 1"],
            # Missing other required columns
        })

        file_path = tmp_path / "missing_columns.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        # Validation should fail
        is_valid, error = excel_service.validate_excel_structure(str(file_path))
        assert is_valid is False
        assert "Missing required columns" in error

    def test_upload_flow_concurrent_upload_blocked(self, db_session, test_user):
        """Test concurrent upload is blocked."""
        excel_service = ExcelService(db_session)
        automation_service = AutomationService(db_session)

        # Create first upload session (processing)
        session1 = automation_service.create_upload_session(
            user_id=test_user.id,
            file_path="uploads/first.xlsx",
            original_filename="first.xlsx",
            total_rows=10
        )

        # Check for concurrent upload
        existing = excel_service.check_concurrent_upload(test_user.id)
        assert existing is not None
        assert existing.id == session1.id

    def test_upload_flow_past_invoices_marked_expired(self, db_session, test_user, tmp_path):
        """Test invoices with past scheduled times are marked as expired."""
        excel_service = ExcelService(db_session)
        automation_service = AutomationService(db_session)

        # Create Excel with past dates with FBR-compliant columns
        df = pd.DataFrame({
            "invoice_number": ["INV-200", "INV-201"],
            "invoice_type": ["Sale Invoice", "Sale Invoice"],
            "invoice_date": ["2020-01-01", "2026-12-31"],
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
            "tax_rate": ["18%", "18%"],
            "uom": ["PCE", "PCE"],
            "quantity": [1, 2],
            "unit_price": [10000, 20000],
            "discount": [0, 0],
            "sales_tax_applicable": [1800, 7200],
            "invoice_ref_no": ["", ""],
            "scenario_id": ["SN001", "SN002"],
            "scheduled_date": ["2020-01-01", "2026-12-31"],  # One past, one future
            "scheduled_time": ["10:00", "11:00"],
            "environment": ["SANDBOX", "SANDBOX"],
            "status": ["", ""],
            "reason": ["", ""]
        })

        file_path = tmp_path / "past_dates.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        # Parse and store
        invoices = excel_service.parse_excel_file(str(file_path))
        assert len(invoices) == 2  # Verify both invoices parsed

        session = automation_service.create_upload_session(
            user_id=test_user.id,
            file_path=str(file_path),
            original_filename="past_dates.xlsx",
            total_rows=len(invoices)
        )

        created_invoices = automation_service.store_invoices_from_excel(
            user_id=test_user.id,
            session_id=session.id,
            invoices=invoices
        )
        assert len(created_invoices) == 2

        # Mark past invoices as expired
        expired_count = automation_service.mark_past_invoices_as_expired(
            user_id=test_user.id,
            session_id=session.id
        )

        # Should mark the 2020 invoice as expired
        assert expired_count == 1

        # Verify statuses
        db_session.refresh(created_invoices[0])
        db_session.refresh(created_invoices[1])

        assert created_invoices[0].status == AutomationInvoiceStatus.EXPIRED
        assert created_invoices[1].status == AutomationInvoiceStatus.PENDING

    def test_upload_flow_empty_file(self, db_session, test_user, tmp_path):
        """Test upload flow fails with empty Excel file."""
        excel_service = ExcelService(db_session)

        # Create empty Excel
        df = pd.DataFrame()
        file_path = tmp_path / "empty.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        # Validation should fail
        is_valid, error = excel_service.validate_excel_structure(str(file_path))
        assert is_valid is False
        assert "empty" in error.lower()
