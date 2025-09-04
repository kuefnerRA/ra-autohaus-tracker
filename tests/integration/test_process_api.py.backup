# tests/integration/test_process_api.py
"""
Integration Tests für Process API Routes
Reinhardt Automobile GmbH - RA Autohaus Tracker

Tests für die HTTP-Endpunkte der Process API mit echten Service-Integrationen.
"""

import pytest
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
    
    @pytest.fixture
    def mock_process_service(self):
        """Mock ProcessService für isolierte API-Tests"""
        mock_service = Mock()
        mock_service.process_zapier_webhook = AsyncMock()
        mock_service.process_email_data = AsyncMock()
        mock_service.process_unified_data = AsyncMock()
        mock_service.health_check = AsyncMock()
        mock_service.process_mappings = {"gwa": "Aufbereitung"}
        mock_service.bearbeiter_mappings = {"Thomas K.": "Thomas Küfner"}
        mock_service.sla_hours = {"Aufbereitung": 72}
        return mock_service
    
    # ===============================
    # Zapier Webhook Tests
    # ===============================
    
    @patch('src.api.routes.process.get_process_service')
    def test_zapier_webhook_success(self, mock_get_service, client, mock_process_service):
        """Test: Erfolgreiche Zapier Webhook-Verarbeitung"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.process_zapier_webhook.return_value = {
            "success": True,
            "processing_id": "proc_12345_zapier",
            "source": "zapier",
            "result": {"fin": "WVWZZZ1JZ8W123456"},
            "sla_data": {"sla_hours": 72, "is_critical": False},
            "timestamp": datetime.now().isoformat()
        }
        
        payload = {
            "fahrzeug_fin": "WVWZZZ1JZ8W123456",
            "prozess_name": "gwa",
            "neuer_status": "In Bearbeitung",
            "bearbeiter_name": "Thomas K.",
            "prioritaet": "3"
        }
        
        response = client.post("/process/zapier/webhook", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["processing_id"] == "proc_12345_zapier"
        assert data["source"] == "zapier"
        assert "result" in data
        assert "sla_data" in data
    
    @patch('src.api.routes.process.get_process_service')
    def test_zapier_webhook_validation_error(self, mock_get_service, client):
        """Test: Zapier Webhook mit ungültigen Daten"""
        mock_get_service.return_value = Mock()
        
        invalid_payload = {
            "fahrzeug_fin": "SHORT",  # Zu kurze FIN
            "prozess_name": "",  # Leerer Prozess-Name
            "neuer_status": "Test"
        }
        
        response = client.post("/process/zapier/webhook", json=invalid_payload)
        
        assert response.status_code == 422  # Validation Error
        error_data = response.json()
        assert "detail" in error_data
        # Pydantic Validierungsfehler für FIN-Länge
        assert any("min_length" in str(error) or "max_length" in str(error) 
                  for error in error_data["detail"])
    
    @patch('src.api.routes.process.get_process_service')
    def test_zapier_webhook_processing_error(self, mock_get_service, client, mock_process_service):
        """Test: Zapier Webhook mit ProcessService-Fehler"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.process_zapier_webhook.return_value = {
            "success": False,
            "processing_id": "proc_error_zapier",
            "source": "zapier",
            "error": "FIN bereits in Bearbeitung",
            "timestamp": datetime.now().isoformat()
        }
        
        payload = {
            "fahrzeug_fin": "TESTFIN1234567890",
            "prozess_name": "foto",
            "neuer_status": "Geplant"
        }
        
        response = client.post("/process/zapier/webhook", json=payload)
        
        assert response.status_code == 200  # API funktioniert, aber Processing failed
        data = response.json()
        assert data["success"] == False
        assert "error_details" in data
        assert data["message"] == "Verarbeitung fehlgeschlagen"
    
    @patch('src.api.routes.process.get_process_service')
    def test_zapier_webhook_with_headers(self, mock_get_service, client, mock_process_service):
        """Test: Zapier Webhook mit HTTP-Headers"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.process_zapier_webhook.return_value = {
            "success": True,
            "processing_id": "proc_headers_zapier",
            "source": "zapier",
            "timestamp": datetime.now().isoformat()
        }
        
        payload = {
            "fahrzeug_fin": "TESTFIN1234567890",
            "prozess_name": "werkstatt",
            "neuer_status": "Diagnose"
        }
        
        headers = {
            "User-Agent": "Zapier",
            "X-Zapier-Delivery-ID": "test-delivery-123"
        }
        
        response = client.post("/process/zapier/webhook", json=payload, headers=headers)
        
        assert response.status_code == 200
        # Verify headers were passed to service
        mock_process_service.process_zapier_webhook.assert_called_once()
        call_args = mock_process_service.process_zapier_webhook.call_args
        assert "user-agent" in call_args[0][1]  # headers parameter
    
    # ===============================
    # Email Processing Tests
    # ===============================
    
    @patch('src.api.routes.process.get_process_service')
    def test_email_processing_success(self, mock_get_service, client, mock_process_service):
        """Test: Erfolgreiche E-Mail-Verarbeitung"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.process_email_data.return_value = {
            "success": True,
            "processing_id": "proc_email_123",
            "source": "email",
            "result": {"fin": "WVWZZZ1JZ8W123456"},
            "timestamp": datetime.now().isoformat()
        }
        
        email_data = {
            "email_content": """
            Fahrzeug Update:
            FIN: WVWZZZ1JZ8W123456
            Status: Reparatur abgeschlossen
            """,
            "subject": "Fahrzeug-Update",
            "sender": "werkstatt@flowers.de"
        }
        
        response = client.post("/process/email/parse", json=email_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["source"] == "email"
        assert "result" in data
    
    @patch('src.api.routes.process.get_process_service')
    def test_email_processing_no_fin_found(self, mock_get_service, client, mock_process_service):
        """Test: E-Mail ohne FIN wird abgelehnt"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.process_email_data.side_effect = ValueError("Keine FIN gefunden")
        
        email_data = {
            "email_content": "Allgemeine Information ohne Fahrzeugdaten",
            "subject": "Info",
            "sender": "info@example.com"
        }
        
        response = client.post("/process/email/parse", json=email_data)
        
        assert response.status_code == 422  # Unprocessable Entity
        error_data = response.json()
        assert "Keine FIN gefunden" in error_data["detail"]
    
    @patch('src.api.routes.process.get_process_service')
    def test_email_processing_with_metadata(self, mock_get_service, client, mock_process_service):
        """Test: E-Mail-Verarbeitung mit zusätzlichen Metadaten"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.process_email_data.return_value = {
            "success": True,
            "processing_id": "proc_email_meta",
            "source": "email",
            "timestamp": datetime.now().isoformat()
        }
        
        email_data = {
            "email_content": "FIN: TESTFIN1234567890 Status: Bereit",
            "subject": "Update",
            "sender": "system@flowers.de",
            "received_at": "2025-09-03T10:30:00Z",
            "headers": {
                "Message-ID": "test-123",
                "X-Priority": "High"
            }
        }
        
        response = client.post("/process/email/parse", json=email_data)
        
        assert response.status_code == 200
        # Verify metadata was passed to service
        call_args = mock_process_service.process_email_data.call_args
        metadata = call_args.kwargs["metadata"]
        assert "received_at" in metadata
        assert "headers" in metadata
    
    # ===============================
    # Unified Processing Tests
    # ===============================
    
    @patch('src.api.routes.process.get_process_service')
    def test_unified_processing_success(self, mock_get_service, client, mock_process_service):
        """Test: Erfolgreiche einheitliche Datenverarbeitung"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.process_unified_data.return_value = {
            "success": True,
            "processing_id": "proc_unified_123",
            "source": "api",
            "result": {"vehicle_updated": True},
            "sla_data": {"hours_remaining": 48},
            "timestamp": datetime.now().isoformat()
        }
        
        unified_data = {
            "fin": "TESTFIN1234567890",
            "prozess_typ": "Aufbereitung",
            "status": "Gestartet",
            "bearbeiter": "Thomas Küfner",
            "prioritaet": 2,
            "notizen": "API-Test"
        }
        
        response = client.post("/process/unified", json=unified_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["processing_id"] == "proc_unified_123"
        assert "sla_data" in data
    
    @patch('src.api.routes.process.get_process_service')
    def test_unified_processing_with_source(self, mock_get_service, client, mock_process_service):
        """Test: Unified Processing mit spezifischer Quelle"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.process_unified_data.return_value = {
            "success": True,
            "processing_id": "proc_manual_123",
            "source": "manual",
            "timestamp": datetime.now().isoformat()
        }
        
        unified_data = {
            "fin": "TESTFIN1234567890",
            "prozess_typ": "Verkauf",
            "status": "Angebot erstellt"
        }
        
        response = client.post("/process/unified?source=manual", json=unified_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    @patch('src.api.routes.process.get_process_service')
    def test_unified_processing_validation_error(self, mock_get_service, client):
        """Test: Unified Processing mit ungültigen Daten"""
        mock_get_service.return_value = Mock()
        
        invalid_data = {
            "fin": "SHORT",  # Ungültige FIN-Länge
            "prozess_typ": "",  # Leerer Prozesstyp
            "status": ""  # Leerer Status
        }
        
        response = client.post("/process/unified", json=invalid_data)
        
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data
        # Mehrere Validierungsfehler erwartet
        assert len(error_data["detail"]) >= 2
    
    # ===============================
    # System Endpoints Tests
    # ===============================
    
    @patch('src.api.routes.process.get_process_service')
    def test_process_health_check_healthy(self, mock_get_service, client, mock_process_service):
        """Test: Process Service Health Check - gesund"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.health_check.return_value = {
            "status": "healthy",
            "service": "ProcessService",
            "dependencies": {
                "vehicle_service": {"status": "healthy"},
                "bigquery_service": {"status": "healthy"}
            },
            "capabilities": {
                "unified_processing": True,
                "zapier_integration": True
            },
            "timestamp": datetime.now().isoformat()
        }
        
        response = client.get("/process/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ProcessService"
        assert "dependencies" in data
        assert "capabilities" in data
    
    @patch('src.api.routes.process.get_process_service')
    def test_process_health_check_degraded(self, mock_get_service, client, mock_process_service):
        """Test: Process Service Health Check - degradiert"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.health_check.return_value = {
            "status": "degraded",
            "service": "ProcessService",
            "dependencies": {
                "vehicle_service": {"status": "healthy"},
                "bigquery_service": {"status": "unhealthy", "error": "Connection failed"}
            },
            "timestamp": datetime.now().isoformat()
        }
        
        response = client.get("/process/health")
        
        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["bigquery_service"]["status"] == "unhealthy"
    
    @patch('src.api.routes.process.get_process_service')
    def test_process_info(self, mock_get_service, client, mock_process_service):
        """Test: Process Service Informationen"""
        mock_get_service.return_value = mock_process_service
        
        response = client.get("/process/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ProcessService"
        assert data["version"] == "2.0.0"
        assert "capabilities" in data
        assert "mappings" in data
        assert "endpoints" in data
        assert data["capabilities"]["unified_processing"] == True
        assert data["capabilities"]["zapier_integration"] == True
    
    # ===============================
    # Error Handling Tests
    # ===============================
    
    @patch('src.api.routes.process.get_process_service')
    def test_zapier_webhook_service_exception(self, mock_get_service, client, mock_process_service):
        """Test: Service-Exception wird korrekt behandelt"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.process_zapier_webhook.side_effect = Exception("Database connection failed")
        
        payload = {
            "fahrzeug_fin": "TESTFIN1234567890",
            "prozess_name": "gwa",
            "neuer_status": "Test"
        }
        
        response = client.post("/process/zapier/webhook", json=payload)
        
        assert response.status_code == 500
        error_data = response.json()
        assert "Database connection failed" in error_data["detail"]
    
    @patch('src.api.routes.process.get_process_service')
    def test_health_check_exception(self, mock_get_service, client, mock_process_service):
        """Test: Health Check Exception wird behandelt"""
        mock_get_service.return_value = mock_process_service
        mock_process_service.health_check.side_effect = Exception("Service initialization failed")
        
        response = client.get("/process/health")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Service initialization failed" in data["error"]

class TestProcessAPIIntegrationFlow:
    """Integration Tests für komplette Workflow-Szenarien"""
    
    @pytest.fixture
    def client(self):
        """FastAPI TestClient"""
        return TestClient(app)
    
    @patch('src.api.routes.process.get_process_service')
    def test_zapier_to_unified_flow(self, mock_get_service, client):
        """Test: Zapier-Daten → Unified Processing Flow"""
        mock_service = Mock()
        mock_service.process_zapier_webhook = AsyncMock(return_value={
            "success": True,
            "processing_id": "proc_flow_123",
            "source": "zapier",
            "result": {"fin": "TESTFIN1234567890"},
            "timestamp": datetime.now().isoformat()
        })
        mock_get_service.return_value = mock_service
        
        # 1. Zapier Webhook
        zapier_payload = {
            "fahrzeug_fin": "TESTFIN1234567890",
            "prozess_name": "gwa",
            "neuer_status": "Warteschlange"
        }
        
        zapier_response = client.post("/process/zapier/webhook", json=zapier_payload)
        assert zapier_response.status_code == 200
        
        # 2. Verify processing_id in response
        zapier_data = zapier_response.json()
        assert "processing_id" in zapier_data
        assert zapier_data["success"] == True

# Test Utilities für Process API
def create_valid_zapier_payload():
    """Hilfsfunktion: Gültiges Zapier-Payload erstellen"""
    return {
        "fahrzeug_fin": "TESTFIN1234567890",
        "prozess_name": "gwa",
        "neuer_status": "In Bearbeitung",
        "bearbeiter_name": "Thomas K.",
        "prioritaet": "3",
        "notizen": "Test-Verarbeitung"
    }

def create_valid_email_payload():
    """Hilfsfunktion: Gültiges E-Mail-Payload erstellen"""
    return {
        "email_content": "Fahrzeug FIN: TESTFIN1234567890 Status: Fertig",
        "subject": "Fahrzeug-Update",
        "sender": "system@flowers.de",
        "received_at": datetime.now().isoformat()
    }

def create_valid_unified_payload():
    """Hilfsfunktion: Gültiges Unified-Payload erstellen"""
    return {
        "fin": "TESTFIN1234567890",
        "prozess_typ": "Aufbereitung",
        "status": "In Bearbeitung",
        "bearbeiter": "Thomas Küfner",
        "prioritaet": 3,
        "notizen": "Test-Prozess"
    }

# Pytest Marks
pytestmark = [
    pytest.mark.integration,
    pytest.mark.api
]