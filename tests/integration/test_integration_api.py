"""Integration Tests für Zapier und Flowers Endpoints"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_zapier_webhook_success():
    """Test erfolgreiche Zapier-Webhook-Verarbeitung"""
    payload = {
        "fin": "WAUZZZGE1NB999999",
        "prozess_typ": "Aufbereitung",
        "status": "gestartet",
        "bearbeiter": "Thomas K."
    }
    
    response = client.post("/api/v1/integration/zapier/webhook", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["fin"] == "WAUZZZGE1NB999999"
    assert data["source"] == "zapier"

def test_zapier_webhook_missing_fin():
    """Test Zapier-Webhook ohne FIN"""
    payload = {"prozess_typ": "Aufbereitung"}
    
    response = client.post("/api/v1/integration/zapier/webhook", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    # Sollte trotzdem verarbeiten, aber ohne FIN

def test_flowers_email_success():
    """Test erfolgreiche Flowers-Email-Verarbeitung"""
    email_data = {
        "subject": "Aufbereitung abgeschlossen",
        "body": "Fahrzeug WAUZZZGE1NB999999 wurde fertig aufbereitet"
    }
    
    response = client.post("/api/v1/integration/flowers/email", json=email_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["fin"] == "WAUZZZGE1NB999999"
    assert data["source"] == "flowers_email"

def test_flowers_email_no_fin():
    """Test Flowers-Email ohne erkennbare FIN"""
    email_data = {
        "subject": "Status Update",
        "body": "Prozess wurde abgeschlossen"
    }
    
    response = client.post("/api/v1/integration/flowers/email", json=email_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == False
    assert "Keine FIN gefunden" in data["error"]