"""
Unit tests for FTE Worker Service.
"""
import pytest
from datetime import datetime, date, time
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool

from src.services.fte_worker_service import FTEWorkerService
from src.models.user import User
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus
from src.models.automation_log import AutomationLog, AutomationLogAction, AutomationLogStatus
from src.models.excel_upload_session import ExcelUploadSession, ExcelUploadProcessingStatus


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
        total_rows=2,
        processed_rows=2,
        processing_status=ExcelUploadProcessingStatus.COMPLETED
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def pending_invoices(db_session, test_user, test_session):
    """Create pending invoices for testing."""
    now = datetime.utcnow()
    current_hour = now.hour
    current_date = now.date()

    invoices = [
        AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=test_session.id,
            invoice_number="INV-100",
            invoice_data={
                "invoice_number": "INV-100",
                "customer_name": "Customer 1",
                "items": "Product A",
                "amount": 10000,
                "tax": 1800
            },
            scheduled_date=current_date,
            scheduled_time=time(hour=current_hour, minute=0),
            status=AutomationInvoiceStatus.PENDING
        ),
        AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=test_session.id,
            invoice_number="INV-101",
            invoice_data={
                "invoice_number": "INV-101",
                "customer_name": "Customer 2",
                "items": "Product B",
                "amount": 20000,
                "tax": 3600
            },
            scheduled_date=current_date,
            scheduled_time=time(hour=current_hour, minute=30),
            status=AutomationInvoiceStatus.PENDING
        )
    ]

    for invoice in invoices:
        db_session.add(invoice)
    db_session.commit()

    for invoice in invoices:
        db_session.refresh(invoice)

    return invoices


class TestFTEWorkerService:
    """Unit tests for FTEWorkerService."""

    @pytest.mark.asyncio
    async def test_identifies_pending_invoices_for_current_hour(
        self, db_session, pending_invoices
    ):
        """Test FTE worker identifies pending invoices for current hour."""
        worker_service = FTEWorkerService(db_session)

        # Mock validation and submission to focus on invoice identification
        with patch.object(
            worker_service.automation_service,
            'validate_invoice',
            new_callable=AsyncMock,
            return_value=(True, {})
        ), patch.object(
            worker_service.automation_service,
            'submit_invoice_to_fbr',
            new_callable=AsyncMock,
            return_value=(True, {"status": "success"}, "REF-123")
        ), patch.object(
            worker_service.excel_service,
            'update_excel_with_status',
            return_value=None
        ):
            stats = await worker_service.process_pending_invoices()

            # Should process both invoices scheduled for current hour
            assert stats["total_processed"] == 2
            assert stats["submitted"] == 2
            assert stats["failed"] == 0

    @pytest.mark.asyncio
    async def test_validates_invoices_correctly(self, db_session, pending_invoices):
        """Test worker validates invoices correctly."""
        worker_service = FTEWorkerService(db_session)

        # Mock validation to return success
        with patch.object(
            worker_service.automation_service,
            'validate_invoice',
            new_callable=AsyncMock,
            return_value=(True, {})
        ) as mock_validate, patch.object(
            worker_service.automation_service,
            'submit_invoice_to_fbr',
            new_callable=AsyncMock,
            return_value=(True, {"status": "success"}, "REF-123")
        ), patch.object(
            worker_service.excel_service,
            'update_excel_with_status',
            return_value=None
        ):
            stats = await worker_service.process_pending_invoices()

            # Validate should be called for each invoice
            assert mock_validate.call_count == 2
            assert stats["validated"] == 2

    @pytest.mark.asyncio
    async def test_submits_valid_invoices_to_fbr(self, db_session, pending_invoices):
        """Test worker submits valid invoices to FBR."""
        worker_service = FTEWorkerService(db_session)

        # Mock successful validation and submission
        with patch.object(
            worker_service.automation_service,
            'validate_invoice',
            new_callable=AsyncMock,
            return_value=(True, {})
        ), patch.object(
            worker_service.automation_service,
            'submit_invoice_to_fbr',
            new_callable=AsyncMock,
            return_value=(True, {"status": "success"}, "REF-123")
        ) as mock_submit, patch.object(
            worker_service.excel_service,
            'update_excel_with_status',
            return_value=None
        ):
            stats = await worker_service.process_pending_invoices()

            # Submit should be called for each validated invoice
            assert mock_submit.call_count == 2
            assert stats["submitted"] == 2

            # Check invoices are marked as submitted
            for invoice in pending_invoices:
                db_session.refresh(invoice)
                assert invoice.status == AutomationInvoiceStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_marks_failed_invoices_with_error_details(
        self, db_session, pending_invoices
    ):
        """Test worker marks failed invoices with error details."""
        worker_service = FTEWorkerService(db_session)

        # Mock validation failure for first invoice
        async def mock_validate(invoice):
            if invoice.invoice_number == "INV-100":
                return False, {"customer_name": "Invalid customer"}
            return True, {}

        with patch.object(
            worker_service.automation_service,
            'validate_invoice',
            side_effect=mock_validate
        ), patch.object(
            worker_service.automation_service,
            'submit_invoice_to_fbr',
            new_callable=AsyncMock,
            return_value=(True, {"status": "success"}, "REF-123")
        ), patch.object(
            worker_service.excel_service,
            'update_excel_with_status',
            return_value=None
        ):
            stats = await worker_service.process_pending_invoices()

            # One should fail validation, one should succeed
            assert stats["failed"] == 1
            assert stats["submitted"] == 1

            # Check failed invoice has error details
            db_session.refresh(pending_invoices[0])
            assert pending_invoices[0].status == AutomationInvoiceStatus.FAILED
            assert "customer_name" in pending_invoices[0].validation_errors

    @pytest.mark.asyncio
    async def test_logs_all_activities(self, db_session, test_session, pending_invoices):
        """Test worker logs validation and submission activities."""
        worker_service = FTEWorkerService(db_session)

        # Ensure session is accessible in the database
        db_session.refresh(test_session)

        # Mock successful processing
        with patch.object(
            worker_service.automation_service,
            'validate_invoice',
            new_callable=AsyncMock,
            return_value=(True, {})
        ), patch.object(
            worker_service.automation_service,
            'submit_invoice_to_fbr',
            new_callable=AsyncMock,
            return_value=(True, {"status": "success"}, "REF-123")
        ):
            stats = await worker_service.process_pending_invoices()

            # Check logs were created
            # For each invoice: validate (success) + submit (success)
            # Total: 2 invoices * 2 logs = 4 logs
            from sqlmodel import select
            logs = db_session.exec(select(AutomationLog)).all()
            assert len(logs) == 4

            # Check log types
            validate_logs = [log for log in logs if log.action == AutomationLogAction.VALIDATE]
            submit_logs = [log for log in logs if log.action == AutomationLogAction.SUBMIT]

            assert len(validate_logs) == 2
            assert len(submit_logs) == 2

            # All should be successful
            assert all(log.status == AutomationLogStatus.SUCCESS for log in logs)

    @pytest.mark.asyncio
    async def test_handles_fbr_downtime_gracefully(self, db_session, pending_invoices):
        """Test worker handles FBR downtime gracefully."""
        worker_service = FTEWorkerService(db_session)

        # Mock FBR submission failure
        with patch.object(
            worker_service.automation_service,
            'validate_invoice',
            new_callable=AsyncMock,
            return_value=(True, {})
        ), patch.object(
            worker_service.automation_service,
            'submit_invoice_to_fbr',
            new_callable=AsyncMock,
            return_value=(False, {"error": "FBR service unavailable"}, None)
        ), patch.object(
            worker_service.excel_service,
            'update_excel_with_status',
            return_value=None
        ):
            stats = await worker_service.process_pending_invoices()

            # Both invoices should fail submission
            assert stats["validated"] == 2
            assert stats["submitted"] == 0
            assert stats["failed"] == 2

            # Check invoices are marked as failed with FBR error
            for invoice in pending_invoices:
                db_session.refresh(invoice)
                assert invoice.status == AutomationInvoiceStatus.FAILED
                assert "FBR service unavailable" in invoice.validation_errors

            # Check failure logs exist
            from sqlmodel import select
            statement = select(AutomationLog).where(
                AutomationLog.action == AutomationLogAction.SUBMIT,
                AutomationLog.status == AutomationLogStatus.FAILURE
            )
            logs = db_session.exec(statement).all()
            assert len(logs) == 2

    @pytest.mark.asyncio
    async def test_no_pending_invoices(self, db_session):
        """Test worker handles case with no pending invoices."""
        worker_service = FTEWorkerService(db_session)

        stats = await worker_service.process_pending_invoices()

        assert stats["total_processed"] == 0
        assert stats["validated"] == 0
        assert stats["submitted"] == 0
        assert stats["failed"] == 0
        assert len(stats["errors"]) == 0

    @pytest.mark.asyncio
    async def test_handles_processing_exception(self, db_session, pending_invoices):
        """Test worker handles unexpected exceptions during processing."""
        worker_service = FTEWorkerService(db_session)

        # Mock validation to raise exception
        with patch.object(
            worker_service.automation_service,
            'validate_invoice',
            new_callable=AsyncMock,
            side_effect=Exception("Unexpected error")
        ), patch.object(
            worker_service.excel_service,
            'update_excel_with_status',
            return_value=None
        ):
            stats = await worker_service.process_pending_invoices()

            # Both invoices should fail
            assert stats["total_processed"] == 2
            assert stats["failed"] == 2
            assert len(stats["errors"]) == 2

            # Check error details
            assert all("Unexpected error" in error["error"] for error in stats["errors"])

            # Check invoices are marked as failed
            for invoice in pending_invoices:
                db_session.refresh(invoice)
                assert invoice.status == AutomationInvoiceStatus.FAILED
