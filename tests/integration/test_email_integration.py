"""Integration Tests für Email-Verarbeitung"""

import pytest
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

@pytest.mark.integration
class TestEmailIntegrationMocked:
    """Integration Tests mit gemockten Services"""
    
    @pytest.fixture
    async def mock_services(self):
        """Setup mit korrekten Parametern"""
        mock_bigquery = Mock()
        mock_bigquery.dataset_ref = 'test.dataset'
        mock_bigquery.get_fahrzeug_by_fin = AsyncMock(return_value=None)
        
        mock_vehicle = Mock()
        mock_vehicle.get_vehicle_details = AsyncMock(return_value=None)
        mock_vehicle.create_complete_vehicle = AsyncMock()
        
        from src.services.email_service import EmailService
        email_service = EmailService(
            mock_vehicle,
            mock_bigquery,
            'test@test.com',    # email
            'password',         # password  
            'imap.test.com'     # server
        )
        
        return email_service, mock_vehicle, mock_bigquery
    
    @pytest.mark.asyncio
    async def test_email_creates_new_vehicle(self, mock_services):
        """Test: Email legt neues Fahrzeug an"""
        email_service, mock_vehicle, mock_bigquery = mock_services
        
        # Mock _parse_email_content direkt
        parsed_data = {
            'fahrzeug': {
                'fin': 'WBAYF8C55DD123456',
                'marke': 'BMW',
                'modell': '320d',
                'km_stand': 45000,
                'ek_netto': 28500.0
            },
            'prozess': {
                'prozess_typ': 'Einkauf',
                'status': 'gestartet'
            }
        }
        
        with patch.object(email_service, '_parse_email_content', 
                         return_value=parsed_data):
            
            result = await email_service._process_single_email({
                'body': 'Test Email',
                'subject': 'Neues Fahrzeug'
            })
        
        # Verifiziere Aufrufe
        mock_vehicle.get_vehicle_details.assert_called_with('WBAYF8C55DD123456')
        mock_vehicle.create_complete_vehicle.assert_called_once()
        
        # Prüfe Ergebnis
        assert result['fahrzeuge_created'] == 1
        assert result['errors'] == []
    
    @pytest.mark.asyncio
    async def test_email_updates_existing_vehicle(self, mock_services):
        """Test: Email aktualisiert existierendes Fahrzeug"""
        email_service, mock_vehicle, mock_bigquery = mock_services
        
        # Mock: Fahrzeug existiert bereits
        existing_vehicle = Mock()
        existing_vehicle.fin = 'WBAYF8C55DD123456'
        mock_vehicle.get_vehicle_details = AsyncMock(return_value=existing_vehicle)
        
        parsed_data = {
            'fahrzeug': {
                'fin': 'WBAYF8C55DD123456',
                'km_stand': 50000
            },
            'prozess': None
        }
        
        with patch.object(email_service, '_parse_email_content',
                         return_value=parsed_data):
            
            result = await email_service._process_single_email({
                'body': 'Update Email',
                'subject': 'Update'
            })
        
        # Verifiziere Update wurde aufgerufen
        mock_vehicle.update_vehicle.assert_called_once()
        call_args = mock_vehicle.update_vehicle.call_args
        assert call_args[0][0] == 'WBAYF8C55DD123456'  # FIN
        assert call_args[0][1]['km_stand'] == 50000    # Update-Daten
        
        assert result['fahrzeuge_updated'] == 1
        assert result['fahrzeuge_created'] == 0