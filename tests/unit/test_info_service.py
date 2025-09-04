"""Unit Tests für InfoService"""
import pytest
from src.services.info_service import InfoService

@pytest.mark.asyncio
async def test_info_service_initialization():
    """Test InfoService Initialisierung"""
    service = InfoService()
    assert service is not None

@pytest.mark.asyncio
async def test_get_prozesse():
    """Test get_prozesse Methode"""
    service = InfoService()
    result = await service.get_prozesse()
    
    assert "prozesse" in result
    assert "gesamt" in result
    assert result["gesamt"] == 6
    assert "Aufbereitung" in result["prozesse"]

@pytest.mark.asyncio
async def test_get_prozess_details():
    """Test get_prozess_details für existierenden Prozess"""
    service = InfoService()
    result = await service.get_prozess_details("Aufbereitung")
    
    assert "prozess_typ" in result
    assert result["prozess_typ"] == "Aufbereitung"
    assert "sla_stunden" in result
    assert result["sla_stunden"] == 72

@pytest.mark.asyncio
async def test_get_prozess_details_not_found():
    """Test get_prozess_details für nicht existierenden Prozess"""
    service = InfoService()
    result = await service.get_prozess_details("NichtExistent")
    
    assert "error" in result
    assert "verfuegbare_prozesse" in result

@pytest.mark.asyncio
async def test_get_bearbeiter():
    """Test get_bearbeiter Methode"""
    service = InfoService()
    result = await service.get_bearbeiter()
    
    assert "bearbeiter" in result
    assert "Thomas Küfner" in result["bearbeiter"]
    assert "Maximilian Reinhardt" in result["bearbeiter"]

@pytest.mark.asyncio
async def test_get_status_definitionen():
    """Test get_status_definitionen Methode"""
    service = InfoService()
    result = await service.get_status_definitionen()
    
    assert "status" in result
    assert "neu" in result["status"]
    assert "in_bearbeitung" in result["status"]
    assert result["status"]["neu"]["farbe"] == "#9CA3AF"

@pytest.mark.asyncio
async def test_get_system_config():
    """Test get_system_config Methode"""
    service = InfoService()
    result = await service.get_system_config()
    
    assert "system" in result
    assert result["system"]["name"] == "RA Autohaus Tracker"
    assert "integrationen" in result

@pytest.mark.asyncio
async def test_get_mappings():
    """Test get_mappings Methode"""
    service = InfoService()
    result = await service.get_mappings()
    
    assert "prozess_mapping" in result
    assert result["prozess_mapping"]["gwa"] == "Aufbereitung"
    assert "bearbeiter_mapping" in result

@pytest.mark.asyncio
async def test_get_bearbeiter_details_not_found():
    """Test get_bearbeiter_details mit nicht existierendem Bearbeiter"""
    service = InfoService()
    result = await service.get_bearbeiter_details("Unbekannter Mitarbeiter")
    
    assert "error" in result
    assert "verfuegbare_bearbeiter" in result

@pytest.mark.asyncio
async def test_get_health_status():
    """Test get_health_status Methode"""
    service = InfoService()
    result = await service.get_health_status()
    
    assert result["status"] == "healthy"
    assert "services" in result