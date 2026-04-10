"""
Unit tests for AutomationService.
"""
import pytest
from datetime import datetime, date, time, timedelta
from uuid import uuid4
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool

from src.services.automation_service import AutomationService
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.automation_log import AutomationLog, AutomationLogAction, AutomationLogStatus
from src.models.excel_upload_session import ExcelUploadSession, ExcelUploadProcessingStatus
from src.models.user import User


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


class TestAutomationService:
    """Test suite for AutomationService."""

    def test_create_upload_session(self, db_session, test_user):
        """Test creating Excel upload session."""
        service = AutomationService(db_session)

        session = service.create_upload_session(
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=10
        )

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.file_path == "uploads/test.xlsx"
        assert session.original_filename == "test.xlsx"
        assert session.total_rows == 10
        assert session.processing_status == ExcelUploadProcessingStatus.PROCESSING

    def test_store_invoices_from_excel(self, db_session, test_user):
        """Test storing invoices from Excel data."""
        service = AutomationService(db_session)

        # Create upload session
        session = ExcelUploadSession(
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=2,
            processing_status=ExcelUploadProcessingStatus.PROCESSING
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # Invoice data
        invoices = [
            {
                "invoice_data": {
                    "invoice_number": "INV-001",
                    "customer_name": "Customer 1",
                    "items": "Product A",
                    "amount": 10000.0,
                    "tax": 1800.0,
                },
                "scheduled_date": date(2026, 4, 5),
                "scheduled_time": time(10, 0)
            },
            {
                "invoice_data": {
                    "invoice_number": "INV-002",
                    "customer_name": "Customer 2",
                    "items": "Product B",
                    "amount": 20000.0,
                    "tax": 3600.0,
                },
                "scheduled_date": date(2026, 4, 6),
                "scheduled_time": time(11, 0)
            }
        ]

        created_invoices = service.store_invoices_from_excel(
            user_id=test_user.id,
            session_id=session.id,
            invoices=invoices
        )

        assert len(created_invoices) == 2
        assert created_invoices[0].invoice_number == "INV-001"
        assert created_invoices[0].status == AutomationInvoiceStatus.PENDING
        assert created_invoices[1].invoice_number == "INV-002"

    def test_mark_past_invoices_as_expired(self, db_session, test_user):
        """Test marking invoices with past scheduled times as expired."""
        service = AutomationService(db_session)

        # Create upload session
        session = ExcelUploadSession(
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=3,
            processing_status=ExcelUploadProcessingStatus.PROCESSING
        )
        db_session.add(session)
        db_session.commit()

        # Create invoices with different scheduled times
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        tomorrow = date.today() + timedelta(days=1)

        invoices = [
            AutomationInvoice(
                user_id=test_user.id,
                excel_upload_session_id=session.id,
                invoice_number="INV-PAST-1",
                invoice_data={},
                scheduled_date=yesterday,
                scheduled_time=time(10, 0),
                status=AutomationInvoiceStatus.PENDING
            ),
            AutomationInvoice(
                user_id=test_user.id,
                excel_upload_session_id=session.id,
                invoice_number="INV-FUTURE",
                invoice_data={},
                scheduled_date=tomorrow,
                scheduled_time=time(10, 0),
                status=AutomationInvoiceStatus.PENDING
            ),
            AutomationInvoice(
                user_id=test_user.id,
                excel_upload_session_id=session.id,
                invoice_number="INV-PAST-2",
                invoice_data={},
                scheduled_date=today,
                scheduled_time=time(0, 0),  # Past time today
                status=AutomationInvoiceStatus.PENDING
            )
        ]

        for invoice in invoices:
            db_session.add(invoice)
        db_session.commit()

        # Mark past invoices as expired
        expired_count = service.mark_past_invoices_as_expired(
            user_id=test_user.id,
            session_id=session.id
        )

        # Should mark at least the invoice from yesterday as expired
        assert expired_count >= 1

        # Verify statuses
        db_session.refresh(invoices[0])
        db_session.refresh(invoices[1])

        assert invoices[0].status == AutomationInvoiceStatus.EXPIRED
        assert invoices[1].status == AutomationInvoiceStatus.PENDING

    def test_get_pending_invoices_for_hour(self, db_session, test_user):
        """Test getting pending invoices for current hour."""
        service = AutomationService(db_session)

        # Create upload session
        session = ExcelUploadSession(
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=3,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()

        today = date.today()

        # Create invoices for different hours
        invoices = [
            AutomationInvoice(
                user_id=test_user.id,
                excel_upload_session_id=session.id,
                invoice_number="INV-10AM",
                invoice_data={},
                scheduled_date=today,
                scheduled_time=time(10, 0),
                status=AutomationInvoiceStatus.PENDING
            ),
            AutomationInvoice(
                user_id=test_user.id,
                excel_upload_session_id=session.id,
                invoice_number="INV-10AM-2",
                invoice_data={},
                scheduled_date=today,
                scheduled_time=time(10, 30),  # Same hour
                status=AutomationInvoiceStatus.PENDING
            ),
            AutomationInvoice(
                user_id=test_user.id,
                excel_upload_session_id=session.id,
                invoice_number="INV-11AM",
                invoice_data={},
                scheduled_date=today,
                scheduled_time=time(11, 0),
                status=AutomationInvoiceStatus.PENDING
            )
        ]

        for invoice in invoices:
            db_session.add(invoice)
        db_session.commit()

        # Get invoices for hour 10
        pending = service.get_pending_invoices_for_hour(
            current_hour=10,
            current_date=today
        )

        assert len(pending) == 2
        assert all(inv.invoice_number.startswith("INV-10AM") for inv in pending)

    def test_update_invoice_status(self, db_session, test_user):
        """Test updating invoice status."""
        service = AutomationService(db_session)

        # Create invoice
        session = ExcelUploadSession(
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=1,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()

        invoice = AutomationInvoice(
            user_id=test_user.id,
            excel_upload_session_id=session.id,
            invoice_number="INV-001",
            invoice_data={},
            scheduled_date=date.today(),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.PENDING
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)

        # Update to submitted
        updated = service.update_invoice_status(
            invoice_id=invoice.id,
            status=AutomationInvoiceStatus.SUBMITTED,
            fbr_response={"success": True}
        )

        assert updated.status == AutomationInvoiceStatus.SUBMITTED
        assert updated.fbr_response == {"success": True}
        assert updated.processed_at is not None

    def test_log_automation_activity(self, db_session, test_user):
        """Test logging automation activity."""
        service = AutomationService(db_session)

        # Create invoice
        session = ExcelUploadSession(
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=1,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()

        invoice = AutomationInvoice(
            user_id=test_user.id,
            excel_upload_session_id=session.id,
            invoice_number="INV-001",
            invoice_data={},
            scheduled_date=date.today(),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.PENDING
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)

        # Log activity
        log = service.log_automation_activity(
            invoice_id=invoice.id,
            action=AutomationLogAction.VALIDATE,
            status=AutomationLogStatus.SUCCESS,
            details={"message": "Validation successful"}
        )

        assert log.automation_invoice_id == invoice.id
        assert log.action == AutomationLogAction.VALIDATE
        assert log.status == AutomationLogStatus.SUCCESS
        assert log.details == {"message": "Validation successful"}

    def test_get_dashboard_stats(self, db_session, test_user):
        """Test getting dashboard statistics."""
        service = AutomationService(db_session)

        # Create upload session
        session = ExcelUploadSession(
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=5,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()

        # Create invoices with different statuses
        statuses = [
            AutomationInvoiceStatus.PENDING,
            AutomationInvoiceStatus.PENDING,
            AutomationInvoiceStatus.SUBMITTED,
            AutomationInvoiceStatus.FAILED,
            AutomationInvoiceStatus.EXPIRED
        ]

        for i, status in enumerate(statuses):
            invoice = AutomationInvoice(
                user_id=test_user.id,
                excel_upload_session_id=session.id,
                invoice_number=f"INV-{i+1:03d}",
                invoice_data={},
                scheduled_date=date.today(),
                scheduled_time=time(10, 0),
                status=status
            )
            db_session.add(invoice)
        db_session.commit()

        # Get stats
        stats = service.get_dashboard_stats(test_user.id)

        assert stats['total_invoices'] == 5
        assert stats['pending_count'] == 2
        assert stats['submitted_count'] == 1
        assert stats['failed_count'] == 1
        assert stats['expired_count'] == 1

    def test_retry_failed_invoice(self, db_session, test_user):
        """Test retrying failed invoice."""
        service = AutomationService(db_session)

        # Create failed invoice
        session = ExcelUploadSession(
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=1,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()

        invoice = AutomationInvoice(
            user_id=test_user.id,
            excel_upload_session_id=session.id,
            invoice_number="INV-001",
            invoice_data={},
            scheduled_date=date.today(),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.FAILED,
            validation_errors="Test error",
            processed_at=datetime.utcnow()
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)

        # Retry invoice
        retried = service.retry_failed_invoice(invoice.id, test_user.id)

        assert retried.status == AutomationInvoiceStatus.PENDING
        assert retried.validation_errors is None
        assert retried.processed_at is None

    def test_retry_non_failed_invoice_raises_error(self, db_session, test_user):
        """Test retrying non-failed invoice raises error."""
        service = AutomationService(db_session)

        # Create pending invoice
        session = ExcelUploadSession(
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=1,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()

        invoice = AutomationInvoice(
            user_id=test_user.id,
            excel_upload_session_id=session.id,
            invoice_number="INV-001",
            invoice_data={},
            scheduled_date=date.today(),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.PENDING
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)

        # Attempt retry should raise error
        with pytest.raises(ValueError, match="must be in 'failed' status"):
            service.retry_failed_invoice(invoice.id, test_user.id)
