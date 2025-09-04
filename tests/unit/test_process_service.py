# tests/unit/test_process_service.py
"""
Unit Tests für ProcessService
Reinhardt Automobile GmbH - RA Autohaus Tracker

Tests für die zentrale Business Logic des ProcessService.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from src.services.process_service import ProcessService, ProcessingSource
from src.models.integration import ProzessTyp, Datenquelle

class TestProcessService:
    """Unit Tests für ProcessService Geschäftslogik"""
    
    @pytest.fixture
    def mock_vehicle_service(self):
        """Mock VehicleService für isolierte Tests"""
        mock = Mock()
        mock.get_vehicle_details = AsyncMock()
        mock.health_check = AsyncMock(return_value={'status': 'healthy'})
        return mock
    
    @pytest.fixture
    def mock_bigquery_service(self):
        """Mock BigQueryService für isolierte Tests"""
        mock = Mock()
        mock.health_check = AsyncMock(return_value={'status': 'healthy'})
        return mock
    
    @pytest.fixture
    def process_service(self, mock_vehicle_service, mock_bigquery_service):
        """ProcessService mit Mock-Dependencies"""
        return ProcessService(
            vehicle_service=mock_vehicle_service,
            bigquery_service=mock_bigquery_service
        )
    
    # ===============================
    # Data Normalization Tests
    # ===============================
    
    @pytest.mark.asyncio
    async def test_normalize_zapier_data(self, process_service):
        """Test: Zapier-Daten werden korrekt normalisiert"""
        zapier_input = {
            "fahrzeug_fin": "wvwzzz1jz8w123456",  # Kleinbuchstaben
            "prozess_name": "gwa",               # Wird zu Aufbereitung
            "bearbeiter_name": "Thomas K.",       # Wird zu Thomas Küfner
            "prioritaet": "3"                     # String wird zu Int
        }
        
        normalized = await process_service._normalize_input_data(
            zapier_input, ProcessingSource.ZAPIER
        )
        
        # Assertions
        assert normalized["fin"] == "WVWZZZ1JZ8W123456"  # Großbuchstaben
        assert normalized["prozess_typ"] == ProzessTyp.AUFBEREITUNG
        assert normalized["bearbeiter"] == "Thomas Küfner"
        assert normalized["prioritaet"] == 3
        assert normalized["datenquelle"] == Datenquelle.ZAPIER
    
    @pytest.mark.asyncio
    async def test_normalize_email_data(self, process_service):
        """Test: E-Mail-Daten werden korrekt normalisiert"""
        email_input = {
            "fin": "WBA12345678901234",
            "prozess_typ": "garage",  # Wird zu Werkstatt
            "status": "Reparatur begonnen"
        }
        
        normalized = await process_service._normalize_input_data(
            email_input, ProcessingSource.EMAIL
        )
        
        assert normalized["fin"] == "WBA12345678901234"
        assert normalized["prozess_typ"] == ProzessTyp.WERKSTATT
        assert normalized["datenquelle"] == Datenquelle.EMAIL
    
    @pytest.mark.asyncio
    async def test_normalize_handles_missing_data(self, process_service):
        """Test: Fehlende Daten werden sauber behandelt"""
        minimal_input = {
            "fin": "TEST123456789"
            # Keine anderen Felder
        }
        
        normalized = await process_service._normalize_input_data(
            minimal_input, ProcessingSource.API
        )
        
        assert normalized["fin"] == "TEST123456789"
        assert "start_timestamp" in normalized
        assert normalized["datenquelle"] == Datenquelle.API
        # Optional fields sollten None oder Defaults sein
        assert normalized.get("prioritaet") is None
    
    # ===============================
    # Business Rules Validation Tests
    # ===============================
    
    @pytest.mark.asyncio
    async def test_validate_complete_data(self, process_service):
        """Test: Vollständige Daten bestehen Validierung"""
        complete_data = {
            "fin": "WVWZZZ1JZ8W123456",
            "prozess_typ": ProzessTyp.AUFBEREITUNG,
            "status": "In Bearbeitung",
            "prioritaet": 3
        }
        
        result = await process_service._validate_business_rules(complete_data)
        
        assert result["valid"] == True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_missing_fin(self, process_service):
        """Test: Fehlende FIN führt zu Validierungsfehler"""
        invalid_data = {
            "prozess_typ": ProzessTyp.AUFBEREITUNG,
            "status": "In Bearbeitung"
            # FIN fehlt
        }
        
        result = await process_service._validate_business_rules(invalid_data)
        
        assert result["valid"] == False
        assert any("FIN ist erforderlich" in error for error in result["errors"])
    
    @pytest.mark.asyncio
    async def test_validate_invalid_fin_length(self, process_service):
        """Test: Ungültige FIN-Länge führt zu Fehler"""
        invalid_data = {
            "fin": "SHORT",  # Zu kurz
            "prozess_typ": ProzessTyp.AUFBEREITUNG,
            "status": "In Bearbeitung"
        }
        
        result = await process_service._validate_business_rules(invalid_data)
        
        assert result["valid"] == False
        assert any("FIN muss 17 Zeichen haben" in error for error in result["errors"])
    
    @pytest.mark.asyncio
    async def test_validate_priority_warning(self, process_service):
        """Test: Ungültige Priorität erzeugt Warning"""
        data_with_bad_priority = {
            "fin": "WVWZZZ1JZ8W123456",
            "prozess_typ": ProzessTyp.AUFBEREITUNG,
            "status": "In Bearbeitung",
            "prioritaet": 15  # Außerhalb 1-10 Bereich
        }
        
        result = await process_service._validate_business_rules(data_with_bad_priority)
        
        assert result["valid"] == True  # Nur Warning, kein Error
        assert len(result["warnings"]) > 0
        assert any("Priorität sollte zwischen" in warning for warning in result["warnings"])
    
    # ===============================
    # SLA Calculation Tests
    # ===============================
    
    def test_sla_calculation_aufbereitung(self, process_service):
        """Test: SLA-Berechnung für Aufbereitung (72h)"""
        start_time = datetime.now() - timedelta(hours=24)  # 24h alt
        
        sla_data = process_service._calculate_sla_data(
            ProzessTyp.AUFBEREITUNG, start_time
        )
        
        assert sla_data["sla_hours"] == 72
        assert sla_data["hours_remaining"] == 48.0  # 72 - 24 = 48
        assert sla_data["is_critical"] == False
        assert "sla_deadline" in sla_data
    
    def test_sla_calculation_critical(self, process_service):
        """Test: SLA-Berechnung für kritischen Fall"""
        start_time = datetime.now() - timedelta(hours=80)  # 80h alt
        
        sla_data = process_service._calculate_sla_data(
            ProzessTyp.AUFBEREITUNG, start_time  # 72h SLA
        )
        
        assert sla_data["is_critical"] == True
        assert sla_data["hours_remaining"] < 0
    
    def test_sla_calculation_warning(self, process_service):
        """Test: SLA-Warning bei wenig verbleibender Zeit"""
        # 20% der SLA-Zeit = 14.4h für Aufbereitung (72h)
        start_time = datetime.now() - timedelta(hours=60)  # 12h übrig
        
        sla_data = process_service._calculate_sla_data(
            ProzessTyp.AUFBEREITUNG, start_time
        )
        
        assert sla_data["is_warning"] == True
        assert sla_data["is_critical"] == False
    
    def test_sla_unknown_process_type(self, process_service):
        """Test: Unbekannter Prozesstyp gibt None-Werte zurück"""
        sla_data = process_service._calculate_sla_data(None, datetime.now())
        
        assert sla_data["sla_hours"] is None
        assert sla_data["is_critical"] == False
    
    # ===============================
    # Zapier Integration Tests
    # ===============================
    
    @pytest.mark.asyncio
    async def test_zapier_webhook_processing(self, process_service, mock_vehicle_service):
        """Test: Zapier Webhook wird korrekt verarbeitet"""
        mock_vehicle_service.get_vehicle_details.return_value = None  # Fahrzeug existiert nicht
        
        zapier_payload = {
            "fahrzeug_fin": "WVWZZZ1JZ8W123456",
            "prozess_name": "gwa",
            "neuer_status": "Warteschlange",
            "bearbeiter_name": "Thomas K.",
            "prioritaet": "3"
        }
        
        result = await process_service.process_zapier_webhook(zapier_payload)
        
        assert result["success"] == True
        assert result["source"] == "zapier"
        assert "processing_id" in result
        assert "sla_data" in result
    
    @pytest.mark.asyncio
    async def test_zapier_webhook_with_headers(self, process_service):
        """Test: Zapier Webhook mit HTTP-Headers"""
        headers = {
            "User-Agent": "Zapier",
            "X-Zapier-Delivery-ID": "test-123"
        }
        
        zapier_payload = {
            "fahrzeug_fin": "TESTFIN1234567890",
            "prozess_name": "foto",
            "neuer_status": "Geplant"
        }
        
        result = await process_service.process_zapier_webhook(zapier_payload, headers)
        
        assert result["success"] == True
        # Headers sollten in Metadaten gespeichert werden
        assert result["source"] == "zapier"
    
    # ===============================
    # Email Processing Tests
    # ===============================
    
    @pytest.mark.asyncio
    async def test_email_content_parsing(self, process_service):
        """Test: E-Mail-Inhalt wird korrekt geparst"""
        email_content = """
        Fahrzeug Update:
        
        FIN: WVWZZZ1JZ8W123456
        Status: Reparatur abgeschlossen
        Werkstatt: Garage Nord
        """
        
        parsed_data = await process_service._parse_email_content(
            email_content, 
            "Fahrzeug Update",
            "werkstatt@flowers.de"
        )
        
        assert parsed_data is not None
        assert parsed_data["fin"] == "WVWZZZ1JZ8W123456"
        assert "zusatz_daten" in parsed_data
        assert parsed_data["zusatz_daten"]["email_sender"] == "werkstatt@flowers.de"
    
    @pytest.mark.asyncio
    async def test_email_no_fin_found(self, process_service):
        """Test: E-Mail ohne FIN wird korrekt behandelt"""
        email_without_fin = """
        Allgemeine Information über Werkstatt.
        Keine spezifischen Fahrzeugdaten.
        """
        
        parsed_data = await process_service._parse_email_content(
            email_without_fin,
            "Info",
            "info@flowers.de"
        )
        
        assert parsed_data is None
    
    # ===============================
    # Health Check Tests  
    # ===============================
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, process_service, mock_vehicle_service, mock_bigquery_service):
        """Test: Health Check bei gesunden Services"""
        mock_vehicle_service.health_check.return_value = {'status': 'healthy'}
        mock_bigquery_service.health_check.return_value = {'status': 'healthy'}
        
        health = await process_service.health_check()
        
        assert health['status'] == 'healthy'
        assert health['service'] == 'ProcessService'
        assert 'dependencies' in health
        assert 'capabilities' in health
        assert health['capabilities']['unified_processing'] == True
    
    @pytest.mark.asyncio
    async def test_health_check_degraded_service(self, process_service, mock_vehicle_service, mock_bigquery_service):
        """Test: Health Check bei degradierten Services"""
        mock_vehicle_service.health_check.return_value = {'status': 'healthy'}
        mock_bigquery_service.health_check.return_value = {'status': 'unhealthy'}
        
        health = await process_service.health_check()
        
        assert health['status'] == 'degraded'
        assert health['dependencies']['bigquery_service']['status'] == 'unhealthy'

# Test-Utilities für ProcessService
def create_test_zapier_payload():
    """Hilfsfunktion: Test-Zapier-Payload erstellen"""
    return {
        "fahrzeug_fin": "TESTFIN1234567890",
        "prozess_name": "gwa",
        "neuer_status": "In Bearbeitung",
        "bearbeiter_name": "Thomas K.",
        "prioritaet": "3",
        "notizen": "Test-Payload"
    }

def create_test_email_content():
    """Hilfsfunktion: Test-E-Mail-Inhalt erstellen"""
    return """
    Fahrzeug-Update Notification:
    
    FIN: TESTFIN1234567890
    Prozess: Aufbereitung
    Status: Abgeschlossen
    Bearbeiter: Max Mustermann
    
    Weitere Details siehe System.
    """

# Pytest-Marks
pytestmark = [
    pytest.mark.unit,
    pytest.mark.fast
]