"""Unit Tests für Dashboard Routes"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_get_kpis_endpoint():
    """Test /api/v1/dashboard/kpis Endpoint"""
    response = client.get("/api/v1/dashboard/kpis")
    
    assert response.status_code == 200
    data = response.json()
    assert "fahrzeuge" in data
    assert "prozesse" in data
    assert "sla" in data

def test_get_warteschlangen_endpoint():
    """Test /api/v1/dashboard/warteschlangen Endpoint"""
    response = client.get("/api/v1/dashboard/warteschlangen")
    
    assert response.status_code == 200
    data = response.json()
    assert "Aufbereitung" in data
    assert isinstance(data["Aufbereitung"], list)

def test_get_sla_endpoint():
    """Test /api/v1/dashboard/sla Endpoint"""
    response = client.get("/api/v1/dashboard/sla")
    
    assert response.status_code == 200
    data = response.json()
    assert "überfällig" in data
    assert "statistik" in data

def test_get_bearbeiter_workload_endpoint():
    """Test /api/v1/dashboard/bearbeiter Endpoint"""
    response = client.get("/api/v1/dashboard/bearbeiter")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_trends_endpoint():
    """Test /api/v1/dashboard/trends Endpoint"""
    response = client.get("/api/v1/dashboard/trends?tage=7")
    
    assert response.status_code == 200
    data = response.json()
    assert "zeitraum_tage" in data
    assert data["zeitraum_tage"] == 7