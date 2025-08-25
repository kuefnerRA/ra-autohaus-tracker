# tests/test_api_basics.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_bigquery():
    with patch('src.main.bq_client') as mock:
        mock.query.return_value = []
        yield mock

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "RA Autohaus Tracker API"
    assert data["version"] == "1.0.0"

@pytest.mark.unit
def test_flowers_prozess_mapping():
    from src.handlers.flowers_handler import FlowersHandler
    handler = FlowersHandler()
    
    assert handler.normalize_prozess_typ("gwa") == "Aufbereitung"
    assert handler.normalize_prozess_typ("garage") == "Werkstatt"
    assert handler.normalize_prozess_typ("transport") == "Anlieferung"