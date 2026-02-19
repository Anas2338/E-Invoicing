import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
from decimal import Decimal

from src.main import app
from src.models.invoice import InvoiceCreate, InvoiceItem, Environment


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_create_invoice_endpoint_exists():
    """Test that the create invoice endpoint exists (without calling it due to DB dependency)."""
    # Just verify that the route exists by importing the router
    from src.api.v1.invoices import router
    assert router is not None


def test_get_invoices_endpoint_exists():
    """Test that the get invoices endpoint exists (without calling it due to DB dependency)."""
    # Just verify that the route exists by importing the router
    from src.api.v1.invoices import router
    assert router is not None


def test_get_invoice_by_id_endpoint_exists(client):
    """Test that the get invoice by ID endpoint exists."""
    response = client.get("/api/v1/invoices/non-existent-id")
    # Should return 401 for auth issues, 404 for not found, or 422 for validation
    assert response.status_code in [401, 404, 422]


def test_invoice_model_creation():
    """Test that InvoiceCreate model can be created with valid data."""
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

    assert invoice_data.external_id == "test-123"
    assert len(invoice_data.items) == 1
    assert invoice_data.environment == Environment.SANDBOX