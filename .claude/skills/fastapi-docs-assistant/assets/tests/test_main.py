from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI example API"}

def test_create_item():
    item_data = {
        "name": "Test Item",
        "description": "This is a test item",
        "price": 10.50
    }
    response = client.post("/items/", json=item_data)
    assert response.status_code == 201
    assert response.json()["name"] == item_data["name"]
    assert response.json()["price"] == item_data["price"]

def test_read_item():
    # First create an item
    item_data = {
        "name": "Test Item",
        "description": "This is a test item",
        "price": 10.50
    }
    create_response = client.post("/items/", json=item_data)
    item_id = create_response.json()["id"]

    # Then read it back
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["id"] == item_id
    assert response.json()["name"] == item_data["name"]