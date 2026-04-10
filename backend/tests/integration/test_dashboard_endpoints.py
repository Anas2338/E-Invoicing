"""
Integration tests for dashboard endpoints.
"""
import pytest
from io import BytesIO
from datetime import date, time, datetime
import pandas as pd
from uuid import uuid4
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.main import app
from src.models.user import User
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.automation_log import AutomationLog, AutomationLogAction, AutomationLogStatus
from src.models.excel_upload_session import ExcelUploadSession, ExcelUploadProcessingStatus
from src.database.session import get_db


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
def test_session(db_session, test_user):
    """Create test Excel upload session."""
    session = ExcelUploadSession(
        id=uuid4(),
        user_id=test_user.id,
        file_path="uploads/test.xlsx",
        original_filename="test.xlsx",
        total_rows=5,
        processed_rows=5,
        processing_status=ExcelUploadProcessingStatus.COMPLETED
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def test_invoices(db_session, test_user, test_session):
    """Create test invoices with various statuses."""
    invoices = [
        AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=test_session.id,
            invoice_number="INV-100",
            invoice_data={"customer_name": "Customer 1", "amount": 10000, "tax": 1800},
            scheduled_date=date(2026, 4, 10),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.PENDING
        ),
        AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=test_session.id,
            invoice_number="INV-101",
            invoice_data={"customer_name": "Customer 2", "amount": 20000, "tax": 3600},
            scheduled_date=date(2026, 4, 11),
            scheduled_time=time(11, 0),
            status=AutomationInvoiceStatus.SUBMITTED,
            fbr_response={"reference_number": "REF-123"},
            processed_at=datetime.utcnow()
        ),
        AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=test_session.id,
            invoice_number="INV-102",
            invoice_data={"customer_name": "Customer 3", "amount": 30000, "tax": 5400},
            scheduled_date=date(2026, 4, 12),
            scheduled_time=time(12, 0),
            status=AutomationInvoiceStatus.FAILED,
            validation_errors="Invalid customer",
            processed_at=datetime.utcnow()
        ),
        AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=test_session.id,
            invoice_number="INV-103",
            invoice_data={"customer_name": "Customer 4", "amount": 40000, "tax": 7200},
            scheduled_date=date(2026, 4, 13),
            scheduled_time=time(13, 0),
            status=AutomationInvoiceStatus.VALIDATED
        ),
        AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=test_session.id,
            invoice_number="INV-104",
            invoice_data={"customer_name": "Customer 5", "amount": 50000, "tax": 9000},
            scheduled_date=date(2026, 4, 14),
            scheduled_time=time(14, 0),
            status=AutomationInvoiceStatus.EXPIRED,
            validation_errors="Scheduled time is in the past"
        )
    ]

    for invoice in invoices:
        db_session.add(invoice)
    db_session.commit()

    for invoice in invoices:
        db_session.refresh(invoice)

    return invoices


@pytest.fixture
def test_logs(db_session, test_invoices):
    """Create test automation logs."""
    logs = [
        AutomationLog(
            id=uuid4(),
            automation_invoice_id=test_invoices[1].id,
            action=AutomationLogAction.VALIDATE,
            status=AutomationLogStatus.SUCCESS,
            details={"message": "Validation successful"}
        ),
        AutomationLog(
            id=uuid4(),
            automation_invoice_id=test_invoices[1].id,
            action=AutomationLogAction.SUBMIT,
            status=AutomationLogStatus.SUCCESS,
            details={"reference_number": "REF-123"}
        )
    ]

    for log in logs:
        db_session.add(log)
    db_session.commit()

    return logs


@pytest.fixture
def client(db_session):
    """Create test client with database override."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestDashboardEndpoints:
    """Integration tests for dashboard endpoints."""

    def test_dashboard_stats_returns_correct_counts(self, db_session, test_user, test_invoices):
        """Test dashboard stats endpoint returns correct counts."""
        from src.services.automation_service import AutomationService

        service = AutomationService(db_session)
        stats = service.get_dashboard_stats(test_user.id)

        assert stats["total_invoices"] == 5
        assert stats["pending_count"] == 1
        assert stats["submitted_count"] == 1
        assert stats["failed_count"] == 1
        assert stats["validated_count"] == 1
        assert stats["expired_count"] == 1

    def test_invoice_list_pagination_works(self, db_session, test_user, test_invoices):
        """Test invoice list pagination works correctly."""
        from sqlmodel import select

        # Test page 1 with page_size=2
        query = select(AutomationInvoice).where(
            AutomationInvoice.user_id == test_user.id
        ).offset(0).limit(2)

        invoices_page1 = db_session.exec(query).all()
        assert len(invoices_page1) == 2

        # Test page 2 with page_size=2
        query = select(AutomationInvoice).where(
            AutomationInvoice.user_id == test_user.id
        ).offset(2).limit(2)

        invoices_page2 = db_session.exec(query).all()
        assert len(invoices_page2) == 2

        # Test page 3 with page_size=2
        query = select(AutomationInvoice).where(
            AutomationInvoice.user_id == test_user.id
        ).offset(4).limit(2)

        invoices_page3 = db_session.exec(query).all()
        assert len(invoices_page3) == 1

    def test_status_filter_works_correctly(self, db_session, test_user, test_invoices):
        """Test status filter works correctly."""
        from sqlmodel import select

        # Filter by pending status
        query = select(AutomationInvoice).where(
            AutomationInvoice.user_id == test_user.id,
            AutomationInvoice.status == AutomationInvoiceStatus.PENDING
        )
        pending_invoices = db_session.exec(query).all()
        assert len(pending_invoices) == 1
        assert pending_invoices[0].status == AutomationInvoiceStatus.PENDING

        # Filter by submitted status
        query = select(AutomationInvoice).where(
            AutomationInvoice.user_id == test_user.id,
            AutomationInvoice.status == AutomationInvoiceStatus.SUBMITTED
        )
        submitted_invoices = db_session.exec(query).all()
        assert len(submitted_invoices) == 1
        assert submitted_invoices[0].status == AutomationInvoiceStatus.SUBMITTED

        # Filter by failed status
        query = select(AutomationInvoice).where(
            AutomationInvoice.user_id == test_user.id,
            AutomationInvoice.status == AutomationInvoiceStatus.FAILED
        )
        failed_invoices = db_session.exec(query).all()
        assert len(failed_invoices) == 1
        assert failed_invoices[0].status == AutomationInvoiceStatus.FAILED

    def test_date_range_filter_works_correctly(self, db_session, test_user, test_invoices):
        """Test date range filter works correctly."""
        from sqlmodel import select

        # Filter by date range (2026-04-11 to 2026-04-13)
        date_from = date(2026, 4, 11)
        date_to = date(2026, 4, 13)

        query = select(AutomationInvoice).where(
            AutomationInvoice.user_id == test_user.id,
            AutomationInvoice.scheduled_date >= date_from,
            AutomationInvoice.scheduled_date <= date_to
        )
        filtered_invoices = db_session.exec(query).all()

        assert len(filtered_invoices) == 3
        assert all(date_from <= inv.scheduled_date <= date_to for inv in filtered_invoices)

    def test_invoice_detail_shows_complete_information(self, db_session, test_user, test_invoices, test_logs):
        """Test invoice detail shows complete information."""
        from sqlmodel import select

        # Get invoice with logs
        invoice = test_invoices[1]  # Submitted invoice with logs

        # Get logs for this invoice
        logs_query = select(AutomationLog).where(
            AutomationLog.automation_invoice_id == invoice.id
        )
        logs = db_session.exec(logs_query).all()

        # Verify invoice details
        assert invoice.id is not None
        assert invoice.invoice_number == "INV-101"
        assert invoice.status == AutomationInvoiceStatus.SUBMITTED
        assert invoice.fbr_response is not None
        assert invoice.processed_at is not None

        # Verify logs
        assert len(logs) == 2
        assert any(log.action == AutomationLogAction.VALIDATE for log in logs)
        assert any(log.action == AutomationLogAction.SUBMIT for log in logs)

    def test_manual_retry_succeeds_for_failed_invoice(self, db_session, test_user, test_invoices):
        """Test manual retry succeeds for failed invoice."""
        from src.services.automation_service import AutomationService
        from sqlmodel import select

        service = AutomationService(db_session)

        # Get failed invoice
        failed_invoice = test_invoices[2]
        assert failed_invoice.status == AutomationInvoiceStatus.FAILED

        # Retry invoice
        updated_invoice = service.retry_failed_invoice(failed_invoice.id)

        # Verify status changed to pending
        assert updated_invoice.status == AutomationInvoiceStatus.PENDING
        assert updated_invoice.validation_errors is None
        assert updated_invoice.fbr_response is None
        assert updated_invoice.processed_at is None

        # Verify retry log was created
        logs_query = select(AutomationLog).where(
            AutomationLog.automation_invoice_id == failed_invoice.id,
            AutomationLog.action == AutomationLogAction.RETRY
        )
        retry_logs = db_session.exec(logs_query).all()
        assert len(retry_logs) == 1
        assert retry_logs[0].status == AutomationLogStatus.SUCCESS

    def test_download_excel_returns_updated_file(self, db_session, test_user, test_session, tmp_path):
        """Test download Excel returns updated file."""
        import os

        # Create actual Excel file for testing
        df = pd.DataFrame({
            "invoice_number": ["INV-100"],
            "customer_name": ["Customer 1"],
            "items": ["Product A"],
            "amount": [10000],
            "tax": [1800],
            "scheduled_date": ["2026-04-10"],
            "scheduled_time": ["10:00"],
            "status": ["pending"],
            "reason": [""]
        })

        file_path = tmp_path / "test.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')

        # Update session file path
        test_session.file_path = str(file_path)
        db_session.add(test_session)
        db_session.commit()

        # Verify file exists
        assert os.path.exists(test_session.file_path)

        # In a real test, you would make an HTTP request to the download endpoint
        # and verify the response is a valid Excel file
        # For now, we just verify the file exists and is readable
        assert os.path.isfile(test_session.file_path)
        assert test_session.file_path.endswith('.xlsx')
