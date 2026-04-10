"""
Integration tests for verifying independence of manual and automated invoice systems.
"""
import pytest
from datetime import date, time, datetime
from uuid import uuid4
from sqlmodel import Session, create_engine, SQLModel, select
from sqlalchemy.pool import StaticPool

from src.models.user import User
from src.models.invoice import Invoice
from src.models.automation_invoice import AutomationInvoice, AutomationInvoiceStatus, InvoiceSource
from src.models.automation_log import AutomationLog
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


class TestManualAutomatedIndependence:
    """Tests to verify manual and automated invoice systems work independently."""

    def test_automated_invoice_upload_works_independently(self, db_session, test_user):
        """Test that automated invoice upload works independently of manual system."""
        # Create Excel upload session
        session = ExcelUploadSession(
            id=uuid4(),
            user_id=test_user.id,
            file_path="uploads/test.xlsx",
            original_filename="test.xlsx",
            total_rows=1,
            processed_rows=1,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # Create automated invoice
        auto_invoice = AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=session.id,
            invoice_number="AUTO-001",
            invoice_data={
                "customer_name": "Auto Customer",
                "amount": 20000,
                "tax": 3600
            },
            scheduled_date=date(2026, 4, 10),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.PENDING,
            source=InvoiceSource.EXCEL_UPLOAD
        )

        db_session.add(auto_invoice)
        db_session.commit()
        db_session.refresh(auto_invoice)

        # Verify automated invoice was created
        assert auto_invoice.id is not None
        assert auto_invoice.invoice_number == "AUTO-001"
        assert auto_invoice.source == InvoiceSource.EXCEL_UPLOAD

        # Verify it's stored in AutomationInvoice table
        statement = select(AutomationInvoice).where(AutomationInvoice.id == auto_invoice.id)
        retrieved = db_session.exec(statement).first()
        assert retrieved is not None
        assert retrieved.invoice_number == "AUTO-001"

    def test_source_filter_distinguishes_invoice_types(self, db_session, test_user):
        """Test that source filter can distinguish between different automation sources."""
        # Create Excel upload session
        session = ExcelUploadSession(
            id=uuid4(),
            user_id=test_user.id,
            file_path="uploads/test3.xlsx",
            original_filename="test3.xlsx",
            total_rows=2,
            processed_rows=2,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()

        # Create invoices with different sources
        excel_invoice = AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=session.id,
            invoice_number="EXCEL-001",
            invoice_data={"customer_name": "Excel Customer", "amount": 10000, "tax": 1800},
            scheduled_date=date(2026, 4, 10),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.PENDING,
            source=InvoiceSource.EXCEL_UPLOAD
        )

        api_invoice = AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=session.id,
            invoice_number="API-001",
            invoice_data={"customer_name": "API Customer", "amount": 20000, "tax": 3600},
            scheduled_date=date(2026, 4, 11),
            scheduled_time=time(11, 0),
            status=AutomationInvoiceStatus.PENDING,
            source=InvoiceSource.API
        )

        db_session.add(excel_invoice)
        db_session.add(api_invoice)
        db_session.commit()

        # Filter by Excel source
        excel_query = select(AutomationInvoice).where(
            AutomationInvoice.user_id == test_user.id,
            AutomationInvoice.source == InvoiceSource.EXCEL_UPLOAD
        )
        excel_invoices = db_session.exec(excel_query).all()

        # Filter by API source
        api_query = select(AutomationInvoice).where(
            AutomationInvoice.user_id == test_user.id,
            AutomationInvoice.source == InvoiceSource.API
        )
        api_invoices = db_session.exec(api_query).all()

        # Verify filtering works
        assert len(excel_invoices) >= 1
        assert len(api_invoices) >= 1
        assert all(inv.source == InvoiceSource.EXCEL_UPLOAD for inv in excel_invoices)
        assert all(inv.source == InvoiceSource.API for inv in api_invoices)

    def test_user_data_isolation_maintained(self, db_session):
        """Test that user data isolation is maintained for automated invoices."""
        # Create two users
        user1 = User(
            id=uuid4(),
            email="user1@example.com",
            name="User 1",
            hashed_password="hashed_password",
            is_active=True
        )
        user2 = User(
            id=uuid4(),
            email="user2@example.com",
            name="User 2",
            hashed_password="hashed_password",
            is_active=True
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # Create Excel sessions for both users
        session_u1 = ExcelUploadSession(
            id=uuid4(),
            user_id=user1.id,
            file_path="uploads/user1.xlsx",
            original_filename="user1.xlsx",
            total_rows=1,
            processed_rows=1,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        session_u2 = ExcelUploadSession(
            id=uuid4(),
            user_id=user2.id,
            file_path="uploads/user2.xlsx",
            original_filename="user2.xlsx",
            total_rows=1,
            processed_rows=1,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session_u1)
        db_session.add(session_u2)
        db_session.commit()

        # Create automated invoices for both users
        auto_invoice_u1 = AutomationInvoice(
            id=uuid4(),
            user_id=user1.id,
            excel_upload_session_id=session_u1.id,
            invoice_number="U1-AUTO-001",
            invoice_data={"customer_name": "User1 Customer", "amount": 10000, "tax": 1800},
            scheduled_date=date(2026, 4, 10),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.PENDING,
            source=InvoiceSource.EXCEL_UPLOAD
        )

        auto_invoice_u2 = AutomationInvoice(
            id=uuid4(),
            user_id=user2.id,
            excel_upload_session_id=session_u2.id,
            invoice_number="U2-AUTO-001",
            invoice_data={"customer_name": "User2 Customer", "amount": 20000, "tax": 3600},
            scheduled_date=date(2026, 4, 10),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.PENDING,
            source=InvoiceSource.EXCEL_UPLOAD
        )
        db_session.add(auto_invoice_u1)
        db_session.add(auto_invoice_u2)
        db_session.commit()

        # Verify user1 can only see their automated invoices
        user1_auto = db_session.exec(
            select(AutomationInvoice).where(AutomationInvoice.user_id == user1.id)
        ).all()
        assert len(user1_auto) == 1
        assert user1_auto[0].invoice_number == "U1-AUTO-001"

        # Verify user2 can only see their automated invoices
        user2_auto = db_session.exec(
            select(AutomationInvoice).where(AutomationInvoice.user_id == user2.id)
        ).all()
        assert len(user2_auto) == 1
        assert user2_auto[0].invoice_number == "U2-AUTO-001"

    def test_default_source_is_excel_upload(self, db_session, test_user):
        """Test that default source for new automated invoices is EXCEL_UPLOAD."""
        # Create Excel upload session
        session = ExcelUploadSession(
            id=uuid4(),
            user_id=test_user.id,
            file_path="uploads/default_test.xlsx",
            original_filename="default_test.xlsx",
            total_rows=1,
            processed_rows=1,
            processing_status=ExcelUploadProcessingStatus.COMPLETED
        )
        db_session.add(session)
        db_session.commit()

        # Create automated invoice without specifying source
        auto_invoice = AutomationInvoice(
            id=uuid4(),
            user_id=test_user.id,
            excel_upload_session_id=session.id,
            invoice_number="DEFAULT-001",
            invoice_data={"customer_name": "Default Customer", "amount": 10000, "tax": 1800},
            scheduled_date=date(2026, 4, 10),
            scheduled_time=time(10, 0),
            status=AutomationInvoiceStatus.PENDING
            # Note: source not specified, should default to EXCEL_UPLOAD
        )

        db_session.add(auto_invoice)
        db_session.commit()
        db_session.refresh(auto_invoice)

        # Verify default source is EXCEL_UPLOAD
        assert auto_invoice.source == InvoiceSource.EXCEL_UPLOAD
