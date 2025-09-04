"""Unit Tests für Info Routes"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
from src.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_get_prozesse_endpoint():
    """Test /api/v1/info/prozesse Endpoint"""
    response = client.get("/api/v1/info/prozesse")
    
    assert response.status_code == 200
    data = response.json()
    assert "prozesse" in data
    assert "gesamt" in data

def test_get_prozess_details_endpoint():
    """Test /api/v1/info/prozesse/{prozess_typ} Endpoint"""
    response = client.get("/api/v1/info/prozesse/Aufbereitung")
    
    assert response.status_code == 200
    data = response.json()
    assert data["prozess_typ"] == "Aufbereitung"

def test_get_system_endpoint():
    """Test /api/v1/info/system Endpoint"""
    response = client.get("/api/v1/info/system")
    
    assert response.status_code == 200
    data = response.json()
    assert data["system"]["name"] == "RA Autohaus Tracker"

def test_get_mappings_endpoint():
    """Test /api/v1/info/mappings Endpoint"""
    response = client.get("/api/v1/info/mappings")
    
    assert response.status_code == 200
    data = response.json()
    assert "prozess_mapping" in data

def test_prozess_not_found():
    """Test 404 für nicht existierenden Prozess"""
    response = client.get("/api/v1/info/prozesse/NichtExistent")
    
    assert response.status_code == 404   

def test_get_bearbeiter_not_found():
    """Test 404 für nicht existierenden Bearbeiter"""
    response = client.get("/api/v1/info/bearbeiter/UnbekannterMitarbeiter")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_get_health_endpoint():
    """Test /api/v1/info/health Endpoint"""
    response = client.get("/api/v1/info/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"