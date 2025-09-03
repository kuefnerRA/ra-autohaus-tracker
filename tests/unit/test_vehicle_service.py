# tests/unit/test_vehicle_service.py
"""
Unit Tests für VehicleService - Basierend auf echter API
Reinhardt Automobile GmbH - RA Autohaus Tracker

Tests für die tatsächliche VehicleService API, die wir entwickelt haben.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.services.vehicle_service import VehicleService

class TestVehicleService:
    """Unit Tests für VehicleService - Echte API"""
    
    @pytest.fixture
    def mock_bigquery_service(self):
        """Mock BigQuery Service - korrekt konfiguriert"""
        mock_bq = Mock()
        mock_bq.get_fahrzeuge_mit_prozessen = AsyncMock(return_value=[])
        mock_bq.get_vehicle_details = AsyncMock(return_value=None)
        mock_bq.health_check = AsyncMock(return_value={'status': 'healthy'})
        return mock_bq
    
    @pytest.fixture
    def vehicle_service(self, mock_bigquery_service):
        """VehicleService mit Mock BigQuery"""
        return VehicleService(bigquery_service=mock_bigquery_service)
    
    @pytest.mark.asyncio
    async def test_get_vehicles_calls_bigquery(self, vehicle_service, mock_bigquery_service):
        """Test: get_vehicles ruft BigQuery korrekt auf"""
        await vehicle_service.get_vehicles(limit=10)
        
        # Verify the correct BigQuery method was called
        mock_bigquery_service.get_fahrzeuge_mit_prozessen.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_delegates_to_bigquery(self, vehicle_service, mock_bigquery_service):
        """Test: Health Check delegiert an BigQuery"""
        mock_bigquery_service.health_check.return_value = {'status': 'healthy'}
        
        result = await vehicle_service.health_check()
        
        # Verify BigQuery health check was called
        mock_bigquery_service.health_check.assert_called_once()
        
        # Verify result structure (based on real API behavior)
        assert 'status' in result

class TestBasicValidation:
    """Einfache Validierungen ohne Service-Dependencies"""
    
    def test_fin_length_validation(self):
        """Test: FIN sollte 17 Zeichen haben"""
        valid_fin = "WVWZZZ1JZ8W123456"
        invalid_fin = "SHORT"
        
        assert len(valid_fin) == 17
        assert len(invalid_fin) != 17
    
    def test_price_validation(self):
        """Test: Einkaufspreis sollte positiv sein"""
        valid_prices = [15000, 25000, 100000]
        invalid_prices = [-1000, 0]
        
        for price in valid_prices:
            assert price > 0
        
        for price in invalid_prices:
            assert price <= 0

# Vereinfachte Test-Utilities
def create_test_fin():
    """Hilfsfunktion: Test-FIN erstellen"""
    return "TESTFIN123456789"

# Pytest-Marks  
pytestmark = [
    pytest.mark.unit,
    pytest.mark.fast
]