import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_read_root(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "FBR Invoice Integration Portal Backend API"}


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "fbr-invoice-portal-backend"


def test_docs_endpoint(client):
    """Test the docs endpoint loads."""
    response = client.get("/api/v1/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text


def test_redoc_endpoint(client):
    """Test the redoc endpoint loads."""
    response = client.get("/api/v1/redoc")
    assert response.status_code == 200
    assert "ReDoc" in response.text  # Check for ReDoc in the title/content


def test_openapi_endpoint(client):
    """Test the OpenAPI schema endpoint."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "FBR Invoice Integration Portal API"