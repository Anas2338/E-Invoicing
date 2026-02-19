import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.services.invoice_service import InvoiceService
from src.models.invoice import Invoice, InvoiceCreate, InvoiceItem, Environment, InvoiceStatus
from src.models.user import User
from src.schemas.invoice import InvoiceFilter


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    return session


@pytest.fixture
def mock_user():
    """Mock user object."""
    user = User(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        email="test@example.com",
        name="Test User",
        is_active=True
    )
    return user


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing."""
    item = InvoiceItem(
        hs_code="12345",
        product_description="Test Product",
        rate="18%",
        uom="Piece",
        quantity=10,
        total_values=1000.0,
        value_sales_excluding_st=847.46,
        fixed_notified_value_or_retail_price=1000.0,
        sales_tax_applicable=152.54,
        sales_tax_withheld_at_source=0.0,
        extra_tax=0.0,
        further_tax=0.0,
        fed_payable=0.0,
        discount=0.0
    )

    invoice_data = InvoiceCreate(
        external_id="test-123",
        invoice_type="Sale Invoice",
        invoice_date="2023-12-01",
        seller_ntn_cnic="1234567890123",
        seller_business_name="Test Seller",
        seller_province="Punjab",
        seller_address="Test Address",
        buyer_ntn_cnic="9876543210987",
        buyer_business_name="Test Buyer",
        buyer_province="Punjab",
        buyer_address="Test Address",
        buyer_registration_type="Registered",
        items=[item],
        environment=Environment.SANDBOX
    )

    return invoice_data


def test_invoice_service_create_invoice(mock_db_session, mock_user, sample_invoice_data):
    """Test creating an invoice using the service."""
    service = InvoiceService()

    # Mock the database save operation
    invoice_data_dict = sample_invoice_data.model_dump()
    saved_invoice = Invoice(
        id=UUID("87654321-4321-8765-4321-876543218765"),
        external_id=sample_invoice_data.external_id,
        user_id=mock_user.id,
        invoice_type=invoice_data_dict['invoice_type'],
        invoice_date=invoice_data_dict['invoice_date'],
        seller_ntn_cnic=invoice_data_dict['seller_ntn_cnic'],
        seller_business_name=invoice_data_dict['seller_business_name'],
        seller_province=invoice_data_dict['seller_province'],
        seller_address=invoice_data_dict['seller_address'],
        buyer_ntn_cnic=invoice_data_dict['buyer_ntn_cnic'],
        buyer_business_name=invoice_data_dict['buyer_business_name'],
        buyer_province=invoice_data_dict['buyer_province'],
        buyer_address=invoice_data_dict['buyer_address'],
        buyer_registration_type=invoice_data_dict['buyer_registration_type'],
        invoice_ref_no=invoice_data_dict.get('invoice_ref_no'),
        scenario_id=invoice_data_dict.get('scenario_id'),
        items=[item.model_dump() for item in sample_invoice_data.items],
        environment=invoice_data_dict['environment'],
        status=InvoiceStatus.DRAFT
    )

    mock_db_session.add = MagicMock()
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock(return_value=saved_invoice)

    # Call the service method
    result = service.create_invoice(mock_db_session, sample_invoice_data, mock_user.id)

    # Assertions
    assert result is not None
    assert result.external_id == sample_invoice_data.external_id
    assert result.user_id == mock_user.id
    assert result.status == InvoiceStatus.DRAFT

    # Verify that database methods were called
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


def test_invoice_service_get_invoice(mock_db_session):
    """Test getting an invoice by ID using the service."""
    service = InvoiceService()

    # Mock invoice
    mock_invoice = Invoice(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        external_id="test-123",
        user_id=UUID("12345678-1234-5678-1234-567812345678"),
        invoice_type="Sale Invoice",
        invoice_date="2023-12-01",
        seller_ntn_cnic="1234567890123",
        seller_business_name="Test Seller",
        seller_province="Punjab",
        seller_address="Test Address",
        buyer_ntn_cnic="9876543210987",
        buyer_business_name="Test Buyer",
        buyer_province="Punjab",
        buyer_address="Test Address",
        buyer_registration_type="Registered",
        items=[],
        environment=Environment.SANDBOX,
        status=InvoiceStatus.VALIDATED
    )

    # Mock the query execution
    mock_exec_result = MagicMock()
    mock_exec_result.first.return_value = mock_invoice
    mock_db_session.exec.return_value = mock_exec_result

    # Call the service method
    user_id = UUID("12345678-1234-5678-1234-567812345678")
    result = service.get_invoice_by_id(mock_db_session, UUID("11111111-1111-1111-1111-111111111111"), user_id)

    # Assertions
    assert result is not None
    assert result.id == UUID("11111111-1111-1111-1111-111111111111")
    assert result.external_id == "test-123"

    # Verify the query was called
    mock_db_session.exec.assert_called_once()


def test_invoice_service_get_user_invoices(mock_db_session, mock_user):
    """Test getting all invoices for a user."""
    service = InvoiceService()

    # Mock invoices
    mock_invoices = [
        Invoice(
            id=UUID(f"11111111-1111-1111-1111-{str(i).zfill(12)}"),
            external_id=f"test-{i}",
            user_id=mock_user.id,
            invoice_type="Sale Invoice",
            invoice_date="2023-12-01",
            seller_ntn_cnic="1234567890123",
            seller_business_name="Test Seller",
            seller_province="Punjab",
            seller_address="Test Address",
            buyer_ntn_cnic="9876543210987",
            buyer_business_name="Test Buyer",
            buyer_province="Punjab",
            buyer_address="Test Address",
            buyer_registration_type="Registered",
            items=[],
            environment=Environment.SANDBOX,
            status=InvoiceStatus.VALIDATED
        ) for i in range(3)
    ]

    # Mock the query execution
    mock_exec_result = MagicMock()
    mock_exec_result.all.return_value = mock_invoices
    mock_db_session.exec.return_value = mock_exec_result

    # Create filters
    filters = InvoiceFilter(page=1, size=10)

    # Call the service method
    result = service.get_invoices_by_user(mock_db_session, mock_user.id, filters)

    # Assertions
    assert result is not None
    assert len(result) == 3
    for invoice in result:
        assert invoice.user_id == mock_user.id

    # Verify the query was called
    mock_db_session.exec.assert_called_once()


def test_invoice_service_validate_invoice_structure():
    """Test the invoice service initialization."""
    service = InvoiceService()

    # This test verifies that the service class can be instantiated
    assert service is not None
    assert hasattr(service, 'create_invoice')
    assert hasattr(service, 'get_invoice_by_id')
    assert hasattr(service, 'get_invoices_by_user')
    assert hasattr(service, 'update_invoice')
    assert hasattr(service, 'delete_invoice')
    assert hasattr(service, 'validate_invoice_transition')


def test_invoice_service_status_transition_validation():
    """Test the invoice status transition validation."""
    service = InvoiceService()

    # Test valid transitions
    assert service.validate_invoice_transition(InvoiceStatus.DRAFT, InvoiceStatus.VALIDATED) == True
    assert service.validate_invoice_transition(InvoiceStatus.DRAFT, InvoiceStatus.FAILED) == True
    assert service.validate_invoice_transition(InvoiceStatus.VALIDATED, InvoiceStatus.POSTED) == True

    # Test invalid transitions
    assert service.validate_invoice_transition(InvoiceStatus.POSTED, InvoiceStatus.DRAFT) == False
    assert service.validate_invoice_transition(InvoiceStatus.FAILED, InvoiceStatus.DRAFT) == False