"""Unit Tests für DashboardService"""
import pytest
from unittest.mock import Mock, AsyncMock
from src.services.dashboard_service import DashboardService

@pytest.fixture
def mock_bigquery_service():
    """Mock BigQueryService für Tests"""
    mock = Mock()
    mock.execute_query = AsyncMock(return_value=[])
    return mock

@pytest.mark.asyncio
async def test_dashboard_service_initialization(mock_bigquery_service):
    """Test DashboardService Initialisierung"""
    service = DashboardService(mock_bigquery_service)
    assert service is not None
    assert service.bq == mock_bigquery_service

@pytest.mark.asyncio
async def test_get_kpis_with_mock_data(mock_bigquery_service):
    """Test get_kpis mit Mock-Daten"""
    service = DashboardService(mock_bigquery_service)
    result = await service.get_kpis()
    
    assert "timestamp" in result
    assert "fahrzeuge" in result
    assert "prozesse" in result
    assert "sla" in result
    assert result["fahrzeuge"]["gesamt"] == 0  # Mock gibt 0 zurück

@pytest.mark.asyncio
async def test_get_warteschlangen(mock_bigquery_service):
    """Test get_warteschlangen Methode"""
    service = DashboardService(mock_bigquery_service)
    result = await service.get_warteschlangen()
    
    assert isinstance(result, dict)
    assert "Aufbereitung" in result
    assert "Werkstatt" in result
    assert "Foto" in result
    assert isinstance(result["Aufbereitung"], list)

@pytest.mark.asyncio
async def test_get_sla_overview(mock_bigquery_service):
    """Test get_sla_overview Methode"""
    service = DashboardService(mock_bigquery_service)
    result = await service.get_sla_overview()
    
    assert "überfällig" in result
    assert "kritisch" in result
    assert "statistik" in result
    assert isinstance(result["statistik"], dict)

@pytest.mark.asyncio
async def test_get_bearbeiter_workload(mock_bigquery_service):
    """Test get_bearbeiter_workload Methode"""
    service = DashboardService(mock_bigquery_service)
    result = await service.get_bearbeiter_workload()
    
    assert isinstance(result, list)
    # Mock gibt leere Liste zurück, aber Fallback sollte greifen
    
@pytest.mark.asyncio
async def test_sla_status_calculation():
    """Test _get_sla_status helper Methode"""
    mock_bq = Mock()
    mock_bq.execute_query = AsyncMock(return_value=[])
    service = DashboardService(mock_bq)
    
    assert service._get_sla_status(-1) == "überfällig"
    assert service._get_sla_status(0) == "kritisch"
    assert service._get_sla_status(2) == "warnung"
    assert service._get_sla_status(5) == "ok"
    assert service._get_sla_status(None) == "unbekannt"

@pytest.mark.asyncio
async def test_get_kpis_with_query_error():
    """Test get_kpis wenn BigQuery einen Fehler wirft"""
    mock_bq = Mock()
    mock_bq.execute_query = AsyncMock(side_effect=Exception("BigQuery Error"))
    
    service = DashboardService(mock_bq)
    result = await service.get_kpis()
    
    # Bei Fehler sollte Mock-Daten zurückgeben
    assert "fahrzeuge" in result
    assert result["fahrzeuge"]["gesamt"] == 45  # Mock-Wert

@pytest.mark.asyncio
async def test_calculate_auslastung():
    """Test _calculate_auslastung helper Methode"""
    mock_bq = Mock()
    service = DashboardService(mock_bq)
    
    assert service._calculate_auslastung(2) == "niedrig"
    assert service._calculate_auslastung(5) == "mittel"
    assert service._calculate_auslastung(10) == "hoch"
    assert service._calculate_auslastung(15) == "überlastet"