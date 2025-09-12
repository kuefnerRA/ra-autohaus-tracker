"""Unit Tests für ZapierHandler"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.handlers.zapier_handler import ZapierHandler

class TestZapierHandler:
    """Unit Tests für ZapierHandler"""
    
    @pytest.fixture
    def mock_unified_handler(self):
        """Mock UnifiedHandler"""
        mock = Mock()
        mock.process_data = AsyncMock(
            return_value={'success': True, 'fin': 'TEST'}
        )
        return mock
    
    @pytest.fixture
    def zapier_handler(self, mock_unified_handler):
        """ZapierHandler mit gemocktem UnifiedHandler"""
        return ZapierHandler(mock_unified_handler)
    
    @pytest.mark.asyncio
    async def test_process_webhook_field_mapping(self, zapier_handler, mock_unified_handler):
        """Test korrekte Feld-Zuordnung von Zapier zu UnifiedHandler"""
        payload = {
            'fahrzeug_fin': 'WBAYF8C55DD123456',
            'prozess_name': 'gwa',
            'neuer_status': 'AKTIV',
            'bearbeiter_name': 'Thomas K.',
            'prioritaet': '3',
            'notizen': 'Test Notiz'
        }
        
        result = await zapier_handler.process_webhook(payload)
        
        assert result['success'] is True
        
        # Prüfe Aufruf-Argumente
        call_args = mock_unified_handler.process_data.call_args[0][0]
        assert call_args['fin'] == 'WBAYF8C55DD123456'
        assert call_args['prozess_typ'] == 'gwa'
        assert call_args['status'] == 'AKTIV'
        assert call_args['bearbeiter'] == 'Thomas K.'
        assert call_args['prioritaet'] == '3'
        assert call_args['notizen'] == 'Test Notiz'
    
    @pytest.mark.asyncio
    async def test_process_webhook_with_nested_data(self, zapier_handler, mock_unified_handler):
        """Test Verarbeitung von verschachtelten Daten"""
        payload = {
            'data': {
                'fin': 'NESTED123456',
                'prozess_typ': 'verkauf',
                'status': 'WARTESCHLANGE'
            }
        }
        
        result = await zapier_handler.process_webhook(payload)
        
        # Bei verschachtelten Daten sollte 'data' direkt verwendet werden
        call_args = mock_unified_handler.process_data.call_args[0][0]
        assert call_args['fin'] == 'NESTED123456'
    
    @pytest.mark.asyncio
    async def test_process_webhook_error_handling(self, zapier_handler, mock_unified_handler):
        """Test Fehlerbehandlung"""
        mock_unified_handler.process_data = AsyncMock(
            side_effect=Exception("Processing failed")
        )
        
        result = await zapier_handler.process_webhook({'fin': 'ERROR'})
        
        assert result['success'] is False
        assert 'Processing failed' in result['error']
        assert result['source'] == 'zapier'