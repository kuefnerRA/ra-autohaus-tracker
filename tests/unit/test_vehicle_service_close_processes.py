"""Unit Tests für die neue Prozess-Schließungs-Logik"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.vehicle_service import VehicleService

class TestVehicleServiceCloseProcesses:
    """Tests für _close_open_processes Methode"""
    
    @pytest.fixture
    def mock_bigquery_service(self):
        """Mock BigQueryService"""
        mock = Mock()
        mock.dataset_ref = 'test-project.test-dataset'
        mock.execute_query = AsyncMock()
        return mock
    
    @pytest.fixture
    def vehicle_service(self, mock_bigquery_service):
        """VehicleService mit gemocktem BigQuery"""
        return VehicleService(mock_bigquery_service)
    
    @pytest.mark.asyncio
    async def test_close_old_processes_found(self, vehicle_service, mock_bigquery_service):
        """Test: Alte Prozesse werden gefunden und beendet"""
        # Mock: 2 alte Prozesse gefunden
        mock_bigquery_service.execute_query.side_effect = [
            [{'count': 2}],  # Check-Query Result
            None  # Update-Query Result
        ]
        
        await vehicle_service._close_open_processes('TEST_FIN', 'Verkauf')
        
        # Beide Queries sollten ausgeführt werden
        assert mock_bigquery_service.execute_query.call_count == 2
        
        # Prüfe Check-Query
        check_query = mock_bigquery_service.execute_query.call_args_list[0][0][0]
        assert 'SELECT COUNT(*) as count' in check_query
        assert "fin = 'TEST_FIN'" in check_query
        assert 'DATETIME_SUB(CURRENT_DATETIME(), INTERVAL 2 HOUR)' in check_query
        
        # Prüfe Update-Query
        update_query = mock_bigquery_service.execute_query.call_args_list[1][0][0]
        assert 'UPDATE' in update_query
        assert "status = 'BEENDET'" in update_query
    
    @pytest.mark.asyncio
    async def test_no_old_processes_skip_update(self, vehicle_service, mock_bigquery_service):
        """Test: Keine alten Prozesse, kein Update"""
        # Mock: Keine alten Prozesse
        mock_bigquery_service.execute_query.return_value = [{'count': 0}]
        
        await vehicle_service._close_open_processes('TEST_FIN', 'Verkauf')
        
        # Nur Check-Query, kein Update
        assert mock_bigquery_service.execute_query.call_count == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_continues(self, vehicle_service, mock_bigquery_service):
        """Test: Bei Fehler wird trotzdem fortgefahren"""
        # Mock: Query schlägt fehl
        mock_bigquery_service.execute_query.side_effect = Exception("Query failed")
        
        # Sollte keine Exception werfen
        await vehicle_service._close_open_processes('TEST_FIN', 'Verkauf')
        
        # Fehler wird nur geloggt, Prozess läuft weiter
        assert mock_bigquery_service.execute_query.called