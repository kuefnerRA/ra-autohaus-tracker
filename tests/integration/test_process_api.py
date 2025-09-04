# tests/integration/test_process_api.py
"""
Integration Tests für Process API Routes
Reinhardt Automobile GmbH - RA Autohaus Tracker
Tests für die HTTP-Endpunkte der Process API mit echten Service-Integrationen.
"""
import pytest
import re
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime
from src.main import app


class TestProcessAPI:
    """Integration Tests für Process API Endpunkte"""
    
    @pytest.fixture
    def client(self):
        """FastAPI TestClient für HTTP-Tests"""
        return TestClient(app)
    
    # ===============================
    # Zapier Webhook Tests
    # ===============================
    
    def test_zapier_webhook_success(self, client):
        """Test: Erfolgreiche Zapier Webhook-Verarbeitung"""
        payload = {
            "fahrzeug_fin": "WVWZZZ1JZ8W123456",
            "prozess_name": "gwa",
            "neuer_status": "In Bearbeitung",
            "bearbeiter_name": "Thomas K.",
            "prioritaet": "3"
        }
        
        response = client.post("/api/v1/process/zapier/webhook", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Processing-ID hat Format: proc_YYYYMMDD_HHMMSS_zapier
        assert re.match(r"proc_\d{8}_\d{6}_zapier", data["processing_id"])
        assert data["source"] == "zapier"
        assert "erfolgreich" in data["message"].lower()
    
    def test_zapier_webhook_validation_error(self, client):
        """Test: Zapier Webhook mit ungültigen Daten"""
        invalid_payload = {
            "fahrzeug_fin": "INVALID",  # Zu kurz
            "prozess_name": "gwa",
            "neuer_status": "Test"
        }
        
        response = client.post("/api/v1/process/zapier/webhook", json=invalid_payload)
        assert response.status_code == 422  # Validation Error
    
    def test_zapier_webhook_creates_new_vehicle(self, client):
        """Test: Zapier Webhook erstellt neues Fahrzeug wenn nicht vorhanden"""
        payload = {
            "fahrzeug_fin": "TESTFIN1234567890",  # Neue FIN
            "prozess_name": "foto",
            "neuer_status": "Geplant"
        }
        
        response = client.post("/api/v1/process/zapier/webhook", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        # API erstellt erfolgreich neues Fahrzeug
        assert data["success"] is True
        assert data["source"] == "zapier"
    
    def test_zapier_webhook_with_headers(self, client):
        """Test: Zapier Webhook mit Custom Headers"""
        headers = {
            "User-Agent": "Zapier",
            "X-Zapier-Hook": "test123"
        }
        
        payload = {
            "fahrzeug_fin": "TESTFIN1234567890",
            "prozess_name": "werkstatt",
            "neuer_status": "Diagnose"
        }
        
        response = client.post("/api/v1/process/zapier/webhook", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    # ===============================
    # E-Mail Processing Tests
    # ===============================
    
    def test_email_processing_success(self, client):
        """Test: Erfolgreiche E-Mail-Verarbeitung"""
        email_data = {
            "email_content": "Fahrzeug FIN: WVWZZZ1JZ8W123456 Status: Fertig",
            "subject": "Aufbereitung abgeschlossen",
            "sender": "werkstatt@example.com"
        }
        
        response = client.post("/api/v1/process/email/parse", json=email_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["source"] == "email"
        assert re.match(r"proc_\d{8}_\d{6}_email", data["processing_id"])
    
    def test_email_processing_no_fin_found(self, client):
        """Test: E-Mail ohne FIN"""
        email_data = {
            "email_content": "Allgemeine Information ohne Fahrzeugbezug",
            "subject": "Info",
            "sender": "info@example.com"
        }
        
        response = client.post("/api/v1/process/email/parse", json=email_data)
        assert response.status_code == 422  # Unprocessable Entity
        error_data = response.json()
        assert "Keine relevanten Fahrzeugdaten" in error_data["detail"]
    
    def test_email_processing_with_metadata(self, client):
        """Test: E-Mail mit Metadaten"""
        email_data = {
            "email_content": "FIN: TESTFIN1234567890 - Aufbereitung fertig",
            "subject": "Update",
            "sender": "system@flowers.de",
            "received_at": datetime.now().isoformat(),
            "headers": {"X-Priority": "High"}
        }
        
        response = client.post("/api/v1/process/email/parse", json=email_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    # ===============================
    # Unified Processing Tests
    # ===============================
    
    def test_unified_processing_success(self, client):
        """Test: Erfolgreiche Unified-Verarbeitung"""
        unified_data = {
            "fin": "TESTFIN1234567890",
            "prozess_typ": "Aufbereitung",
            "status": "Gestartet",
            "bearbeiter": "Max Mustermann",
            "prioritaet": 5
        }
        
        response = client.post("/api/v1/process/unified", json=unified_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert re.match(r"proc_\d{8}_\d{6}_api", data["processing_id"])
        assert data["source"] == "api"
    
    def test_unified_processing_with_source(self, client):
        """Test: Unified Processing mit Custom Source"""
        unified_data = {
            "fin": "TESTFIN1234567890",
            "prozess_typ": "Verkauf",
            "status": "Angebot erstellt"
        }
        
        response = client.post("/api/v1/process/unified?source=manual", json=unified_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_unified_processing_validation_error(self, client):
        """Test: Unified Processing mit Validierungsfehler"""
        invalid_data = {
            "fin": "SHORT",  # Zu kurz
            "prozess_typ": "Test",
            "status": "Invalid"
        }
        
        response = client.post("/api/v1/process/unified", json=invalid_data)
        assert response.status_code == 422
        error_data = response.json()
        # Prüfe dass Validierungsfehler zurückgegeben wird
        assert "detail" in error_data
        assert isinstance(error_data["detail"], list)
        assert any("fin" in str(err) for err in error_data["detail"])
    
    # ===============================
    # Health & Info Tests
    # ===============================
    
    def test_process_health_check_healthy(self, client):
        """Test: Process Service Health Check"""
        response = client.get("/api/v1/process/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "dependencies" in data
    
    def test_process_info(self, client):
        """Test: Process Service Info"""
        response = client.get("/api/v1/process/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ProcessService"
        assert data["version"] == "2.0.0"
        assert "capabilities" in data
        assert "mappings" in data
        assert "endpoints" in data


class TestProcessAPIIntegrationFlow:
    """Tests für komplette Integration Flows"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_zapier_to_unified_flow(self, client):
        """Test: Kompletter Flow von Zapier zu Unified Processing"""
        # Schritt 1: Zapier Webhook
        zapier_payload = {
            "fahrzeug_fin": "FLOWTEST123456789",
            "prozess_name": "gwa",
            "neuer_status": "Gestartet",
            "bearbeiter_name": "Test User"
        }
        
        zapier_response = client.post("/api/v1/process/zapier/webhook", json=zapier_payload)
        assert zapier_response.status_code == 200
        zapier_data = zapier_response.json()
        assert zapier_data["success"] is True
        
        # Schritt 2: Info abrufen
        info_response = client.get("/api/v1/process/info")
        assert info_response.status_code == 200
        
        # Schritt 3: Health Check
        health_response = client.get("/api/v1/process/health")
        assert health_response.status_code == 200
    
    def test_email_parsing_flow(self, client):
        """Test: E-Mail Parsing mit verschiedenen Formaten"""
        test_emails = [
            {
                "content": "FIN: EMAILTEST12345678 Status: Fertig",  # Genau 17 Zeichen
                "expected": True
            },
            {
                "content": "Fahrzeug EMAILTEST23456789 wurde bearbeitet",  # Genau 17 Zeichen
                "expected": True
            },
            {
                "content": "Keine Fahrzeugdaten hier",
                "expected": False
            }
        ]
        
        for test_case in test_emails:
            email_data = {
                "email_content": test_case["content"],
                "subject": "Test",
                "sender": "test@example.com"
            }
            
            response = client.post("/api/v1/process/email/parse", json=email_data)
            
            if test_case["expected"]:
                assert response.status_code == 200
                assert response.json()["success"] is True
            else:
                assert response.status_code == 422