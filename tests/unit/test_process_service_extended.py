# tests/unit/test_process_service_extended.py
"""
Erweiterte Unit Tests für ProcessService
Reinhardt Automobile GmbH - RA Autohaus Tracker

Tests basierend auf dem tatsächlichen process_service.py Code
Ziel: Coverage von 29% auf 70%+ erhöhen
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from typing import Dict, Any, Optional

from src.services.process_service import ProcessService, ProcessingSource
from src.models.integration import (
    FahrzeugStammCreate,
    FahrzeugProzessCreate,
    FahrzeugMitProzess,
    ProzessTyp,
    Datenquelle
)


class TestProcessServiceExtended:
    """Erweiterte Tests für ProcessService - ungetestete Methoden"""
    
    @pytest.fixture
    def mock_vehicle_service(self):
        """Mock VehicleService"""
        mock = Mock()
        mock.get_vehicle_details = AsyncMock()
        mock.get_vehicles = AsyncMock()
        mock.create_complete_vehicle = AsyncMock()
        mock.update_vehicle_status = AsyncMock()
        mock.get_vehicle_kpis = AsyncMock()
        mock.health_check = AsyncMock(return_value={"status": "healthy"})
        return mock
    
    @pytest.fixture
    def mock_bigquery_service(self):
        """Mock BigQueryService"""
        mock = Mock()
        mock.create_fahrzeug_stamm = AsyncMock()
        mock.create_fahrzeug_prozess = AsyncMock()
        mock.get_fahrzeug_by_fin = AsyncMock()
        mock.get_fahrzeuge_mit_prozessen = AsyncMock()
        mock.health_check = AsyncMock(return_value={"status": "healthy"})
        return mock
    
    @pytest.fixture
    def process_service(self, mock_vehicle_service, mock_bigquery_service):
        """ProcessService mit Mocks"""
        return ProcessService(
            vehicle_service=mock_vehicle_service,
            bigquery_service=mock_bigquery_service
        )
    
    # ===============================
    # Tests für process_unified_data
    # ===============================
    
    @pytest.mark.asyncio
    async def test_process_unified_data_success(self, process_service, mock_vehicle_service):
        """Test: Unified Data Processing - Erfolg"""
        test_data = {
            "fin": "WBA12345678901234",
            "prozess_typ": "aufbereitung",
            "status": "In Bearbeitung",
            "bearbeiter": "Thomas K.",
            "prioritaet": "3",
            "notizen": "Test Notiz"
        }
        
        mock_vehicle_service.get_vehicle_details.return_value = FahrzeugMitProzess(
            fin="WBA12345678901234",
            marke="BMW",
            modell="3er"
        )
        
        result = await process_service.process_unified_data(
            data=test_data,
            source=ProcessingSource.API
        )
        
        assert result["success"] is True
        assert result["source"] == "api"
        assert "processing_id" in result
        assert "timestamp" in result
        assert "result" in result
    
    @pytest.mark.asyncio
    async def test_process_unified_data_validation_failure(self, process_service):
        """Test: Unified Data Processing - Validierungsfehler"""
        test_data = {
            # FIN fehlt - sollte Validierungsfehler auslösen
            "prozess_typ": "aufbereitung",
            "status": "In Bearbeitung"
        }
        
        result = await process_service.process_unified_data(
            data=test_data,
            source=ProcessingSource.API
        )
        
        assert result["success"] is False
        assert "FIN ist erforderlich" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_unified_data_with_metadata(self, process_service, mock_vehicle_service):
        """Test: Unified Data Processing mit Metadaten"""
        test_data = {
            "fin": "WBA12345678901234",
            "prozess_typ": "werkstatt",
            "status": "Wartend"
        }
        
        metadata = {
            "headers": {"X-Source": "Test"},
            "timestamp": datetime.now().isoformat()
        }
        
        mock_vehicle_service.get_vehicle_details.return_value = None
        
        result = await process_service.process_unified_data(
            data=test_data,
            source=ProcessingSource.ZAPIER,
            metadata=metadata
        )
        
        assert result["source"] == "zapier"
        assert result["success"] is True
    
    # ===============================
    # Tests für process_zapier_webhook
    # ===============================
    
    @pytest.mark.asyncio
    async def test_process_zapier_webhook_success(self, process_service, mock_vehicle_service):
        """Test: Zapier Webhook Verarbeitung"""
        webhook_data = {
            "fahrzeug_fin": "WVWZZZ1JZ8W123456",
            "prozess_name": "gwa",  # sollte zu AUFBEREITUNG werden
            "neuer_status": "In Bearbeitung",
            "bearbeiter_name": "Thomas K.",  # sollte zu "Thomas Küfner" werden
            "prioritaet": "3",
            "notizen": "Von Zapier",
            "timestamp": datetime.now().isoformat()
        }
        
        mock_vehicle_service.get_vehicle_details.return_value = FahrzeugMitProzess(
            fin="WVWZZZ1JZ8W123456",
            marke="VW",
            modell="Golf"
        )
        
        result = await process_service.process_zapier_webhook(webhook_data)
        
        assert result["success"] is True
        assert result["source"] == "zapier"
    
    @pytest.mark.asyncio
    async def test_process_zapier_webhook_with_headers(self, process_service, mock_vehicle_service):
        """Test: Zapier Webhook mit Headers"""
        webhook_data = {
            "fahrzeug_fin": "WDD12345678901234",
            "prozess_name": "werkstatt",
            "neuer_status": "Abgeschlossen",
            "bearbeiter_name": "Max R."
        }
        
        headers = {
            "X-Zapier-Hook": "12345",
            "Content-Type": "application/json"
        }
        
        mock_vehicle_service.get_vehicle_details.return_value = None
        
        result = await process_service.process_zapier_webhook(
            webhook_data=webhook_data,
            headers=headers
        )
        
        assert result["success"] is True
    
    # ===============================
    # Tests für process_email_data
    # ===============================
    
    @pytest.mark.asyncio
    async def test_process_email_data_with_fin(self, process_service, mock_vehicle_service):
        """Test: E-Mail Processing mit FIN"""
        email_content = "Bitte Fahrzeug WBA12345678901234 aufbereiten."
        subject = "Aufbereitung BMW"
        sender = "werkstatt@example.com"
        
        mock_vehicle_service.get_vehicle_details.return_value = FahrzeugMitProzess(
            fin="WBA12345678901234",
            marke="BMW"
        )
        
        result = await process_service.process_email_data(
            email_content=email_content,
            subject=subject,
            sender=sender
        )
        
        assert result["success"] is True
        assert result["source"] == "email"
    
    @pytest.mark.asyncio
    async def test_process_email_data_no_fin(self, process_service):
        """Test: E-Mail Processing ohne FIN"""
        email_content = "Bitte Fahrzeug aufbereiten."
        subject = "Aufbereitung"
        sender = "werkstatt@example.com"
        
        with pytest.raises(ValueError, match="Keine relevanten Fahrzeugdaten"):
            await process_service.process_email_data(
                email_content=email_content,
                subject=subject,
                sender=sender
            )
    
    @pytest.mark.asyncio
    async def test_process_email_data_with_metadata(self, process_service, mock_vehicle_service):
        """Test: E-Mail Processing mit Metadaten"""
        email_content = "FIN: WBA12345678901234 - Werkstatt fertig"
        subject = "Werkstatt abgeschlossen"
        sender = "service@autohaus.de"
        metadata = {"received_at": datetime.now().isoformat()}
        
        mock_vehicle_service.get_vehicle_details.return_value = None
        
        result = await process_service.process_email_data(
            email_content=email_content,
            subject=subject,
            sender=sender,
            metadata=metadata
        )
        
        assert result["success"] is True
    
    # ===============================
    # Tests für _normalize_input_data
    # ===============================
    
    @pytest.mark.asyncio
    async def test_normalize_input_data_complete(self, process_service):
        """Test: Vollständige Daten-Normalisierung"""
        raw_data = {
            "fahrzeug_fin": "wba12345678901234",  # Kleingeschrieben
            "prozess_name": "gwa",  # Zapier-Kürzel
            "bearbeiter_name": "Thomas K.",  # Kurzname
            "neuer_status": "In Bearbeitung",
            "prioritaet": "5",
            "notizen": "Test"
        }
        
        normalized = await process_service._normalize_input_data(
            raw_data,
            ProcessingSource.ZAPIER
        )
        
        assert normalized["fin"] == "WBA12345678901234"  # Großgeschrieben
        assert normalized["prozess_typ"] == ProzessTyp.AUFBEREITUNG  # Gemappt von "gwa"
        assert normalized["bearbeiter"] == "Thomas Küfner"  # Vollständiger Name
        assert normalized["status"] == "In Bearbeitung"
        assert normalized["prioritaet"] == 5  # Als Integer
        assert normalized["datenquelle"] == Datenquelle.ZAPIER
    
    @pytest.mark.asyncio
    async def test_normalize_input_data_minimal(self, process_service):
        """Test: Minimale Daten-Normalisierung"""
        raw_data = {
            "fin": "WBA12345678901234"
        }
        
        normalized = await process_service._normalize_input_data(
            raw_data,
            ProcessingSource.API
        )
        
        assert normalized["fin"] == "WBA12345678901234"
        assert normalized["datenquelle"] == Datenquelle.API
        assert "start_timestamp" in normalized
    
    # ===============================
    # Tests für _validate_business_rules
    # ===============================
    
    @pytest.mark.asyncio
    async def test_validate_business_rules_valid(self, process_service):
        """Test: Gültige Geschäftsregeln"""
        data = {
            "fin": "WBA12345678901234",
            "prozess_typ": ProzessTyp.AUFBEREITUNG,
            "status": "In Bearbeitung",
            "prioritaet": 5
        }
        
        result = await process_service._validate_business_rules(data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_business_rules_missing_fin(self, process_service):
        """Test: Fehlende FIN"""
        data = {
            "prozess_typ": ProzessTyp.AUFBEREITUNG,
            "status": "In Bearbeitung"
        }
        
        result = await process_service._validate_business_rules(data)
        
        assert result["valid"] is False
        assert "FIN ist erforderlich" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_business_rules_invalid_fin_length(self, process_service):
        """Test: Ungültige FIN-Länge"""
        data = {
            "fin": "WBA123",  # Zu kurz
            "prozess_typ": ProzessTyp.AUFBEREITUNG,
            "status": "In Bearbeitung"
        }
        
        result = await process_service._validate_business_rules(data)
        
        assert result["valid"] is False
        assert "FIN muss 17 Zeichen haben" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_business_rules_priority_warning(self, process_service):
        """Test: Priorität außerhalb des Bereichs"""
        data = {
            "fin": "WBA12345678901234",
            "prozess_typ": ProzessTyp.AUFBEREITUNG,
            "status": "In Bearbeitung",
            "prioritaet": 15  # Zu hoch
        }
        
        result = await process_service._validate_business_rules(data)
        
        assert result["valid"] is True  # Nur Warning, kein Error
        assert "Priorität sollte zwischen 1 und 10 liegen" in result["warnings"]
    
    # ===============================
    # Tests für _calculate_sla_data
    # ===============================
    
    def test_calculate_sla_data_aufbereitung(self, process_service):
        """Test: SLA-Berechnung für Aufbereitung"""
        start_time = datetime.now()
        
        sla_data = process_service._calculate_sla_data(
            ProzessTyp.AUFBEREITUNG,
            start_time
        )
        
        assert sla_data["sla_hours"] == 72
        assert sla_data["hours_remaining"] > 70
        assert sla_data["is_critical"] is False
        assert sla_data["is_warning"] is False
    
    def test_calculate_sla_data_critical(self, process_service):
        """Test: SLA-Berechnung - Kritisch"""
        start_time = datetime.now() - timedelta(hours=73)  # Überfällig
        
        sla_data = process_service._calculate_sla_data(
            ProzessTyp.AUFBEREITUNG,
            start_time
        )
        
        assert sla_data["sla_hours"] == 72
        assert sla_data["hours_remaining"] < 0
        assert sla_data["is_critical"] is True
    
    def test_calculate_sla_data_warning(self, process_service):
        """Test: SLA-Berechnung - Warnung"""
        start_time = datetime.now() - timedelta(hours=65)  # Weniger als 20% übrig
        
        sla_data = process_service._calculate_sla_data(
            ProzessTyp.AUFBEREITUNG,
            start_time
        )
        
        assert sla_data["sla_hours"] == 72
        assert 0 < sla_data["hours_remaining"] < 15
        assert sla_data["is_critical"] is False
        assert sla_data["is_warning"] is True
    
    def test_calculate_sla_data_invalid_type(self, process_service):
        """Test: SLA-Berechnung mit ungültigem Typ"""
        sla_data = process_service._calculate_sla_data(
            None,
            datetime.now()
        )
        
        assert sla_data["sla_hours"] is None
        assert sla_data["sla_deadline"] is None
        assert sla_data["is_critical"] is False
    
    # ===============================
    # Tests für _parse_email_content
    # ===============================
    
    @pytest.mark.asyncio
    async def test_parse_email_content_with_fin(self, process_service):
        """Test: E-Mail-Parsing mit FIN"""
        content = "Das Fahrzeug WBA12345678901234 ist fertig."
        subject = "Aufbereitung abgeschlossen"
        sender = "werkstatt@example.com"
        
        result = await process_service._parse_email_content(
            content, subject, sender
        )
        
        assert result is not None
        assert result["fin"] == "WBA12345678901234"
        assert result["prozess_typ"] == "aufbereitung"
        assert result["status"] == "E-Mail empfangen"
        assert sender in result["zusatz_daten"]["email_sender"]
    
    @pytest.mark.asyncio
    async def test_parse_email_content_no_fin(self, process_service):
        """Test: E-Mail-Parsing ohne FIN"""
        content = "Das Fahrzeug ist fertig."
        subject = "Aufbereitung"
        sender = "werkstatt@example.com"
        
        result = await process_service._parse_email_content(
            content, subject, sender
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_parse_email_content_multiple_fins(self, process_service):
        """Test: E-Mail-Parsing mit mehreren FINs"""
        content = "Fahrzeuge WBA12345678901234 und WDD98765432109876 sind fertig."
        subject = "Mehrere Fahrzeuge"
        sender = "werkstatt@example.com"
        
        result = await process_service._parse_email_content(
            content, subject, sender
        )
        
        assert result is not None
        assert result["fin"] == "WBA12345678901234"  # Erste FIN wird genommen
    
    # ===============================
    # Tests für health_check
    # ===============================
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, process_service, mock_vehicle_service, mock_bigquery_service):
        """Test: Health Check - Alles gesund"""
        mock_vehicle_service.health_check.return_value = {"status": "healthy"}
        mock_bigquery_service.health_check.return_value = {"status": "healthy"}
        
        result = await process_service.health_check()
        
        assert result["status"] == "healthy"
        assert result["service"] == "ProcessService"
        assert result["dependencies"]["vehicle_service"]["status"] == "healthy"
        assert result["dependencies"]["bigquery_service"]["status"] == "healthy"
        assert result["capabilities"]["unified_processing"] is True
        assert result["capabilities"]["zapier_integration"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, process_service, mock_vehicle_service, mock_bigquery_service):
        """Test: Health Check - Degradiert"""
        mock_vehicle_service.health_check.return_value = {"status": "healthy"}
        mock_bigquery_service.health_check.return_value = {"status": "unhealthy"}
        
        result = await process_service.health_check()
        
        assert result["status"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_health_check_error(self, process_service, mock_vehicle_service):
        """Test: Health Check - Fehler"""
        mock_vehicle_service.health_check.side_effect = Exception("Service down")
        
        result = await process_service.health_check()
        
        assert result["status"] == "unhealthy"
        assert "Service down" in result["error"]
    
    # ===============================
    # Integration Tests
    # ===============================
    
    @pytest.mark.asyncio
    async def test_complete_workflow_zapier_to_process(self, process_service, mock_vehicle_service):
        """Test: Kompletter Workflow von Zapier bis Prozess"""
        # Zapier Webhook kommt rein
        webhook_data = {
            "fahrzeug_fin": "WBA12345678901234",
            "prozess_name": "gwa",
            "neuer_status": "Wartend",
            "bearbeiter_name": "Thomas K.",
            "prioritaet": "2"
        }
        
        mock_vehicle_service.get_vehicle_details.return_value = FahrzeugMitProzess(
            fin="WBA12345678901234",
            marke="BMW",
            modell="3er",
            prozess_typ="Aufbereitung"
        )
        
        # Webhook verarbeiten
        result = await process_service.process_zapier_webhook(webhook_data)
        
        assert result["success"] is True
        assert result["source"] == "zapier"
        
        # SLA-Daten sollten berechnet worden sein
        assert "sla_data" in result
        if result["result"].get("prozess_typ"):
            assert result["sla_data"]["sla_hours"] > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_in_processing(self, process_service, mock_vehicle_service):
        """Test: Fehlerbehandlung im Processing"""
        mock_vehicle_service.get_vehicle_details.side_effect = Exception("Database error")
        
        test_data = {
            "fin": "WBA12345678901234",
            "prozess_typ": "aufbereitung",
            "status": "Test"
        }
        
        result = await process_service.process_unified_data(
            data=test_data,
            source=ProcessingSource.API
        )
        
        assert result["success"] is False
        assert "Database error" in result["error"]
    
    # ===============================
    # Edge Cases und Spezialfälle
    # ===============================
    
    @pytest.mark.asyncio
    async def test_process_with_special_characters_in_fin(self, process_service):
        """Test: FIN mit Sonderzeichen"""
        data = {
            "fin": "WBA-12345-678901234",  # Mit Bindestrichen
            "prozess_typ": "werkstatt",
            "status": "Test"
        }
        
        normalized = await process_service._normalize_input_data(
            data,
            ProcessingSource.API
        )
        
        assert normalized["fin"] == "WBA12345678901234"  # Ohne Bindestriche
    
    @pytest.mark.asyncio
    async def test_unknown_process_type_mapping(self, process_service):
        """Test: Unbekannter Prozesstyp"""
        data = {
            "fin": "WBA12345678901234",
            "prozess_typ": "unbekannt",
            "status": "Test"
        }
        
        normalized = await process_service._normalize_input_data(
            data,
            ProcessingSource.API
        )
        
        assert normalized["prozess_typ"] == "unbekannt"  # Bleibt unverändert
    
    @pytest.mark.asyncio
    async def test_unknown_bearbeiter_mapping(self, process_service):
        """Test: Unbekannter Bearbeiter"""
        data = {
            "fin": "WBA12345678901234",
            "bearbeiter": "Neuer Mitarbeiter",
            "status": "Test"
        }
        
        normalized = await process_service._normalize_input_data(
            data,
            ProcessingSource.API
        )
        
        assert normalized["bearbeiter"] == "Neuer Mitarbeiter"  # Bleibt unverändert