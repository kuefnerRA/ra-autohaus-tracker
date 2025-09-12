"""Integration Tests für Zapier Webhook"""

import os
import pytest
import httpx
import pytest

pytestmark = pytest.mark.skip(reason="Needs running server")


from datetime import datetime

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv('RUN_INTEGRATION_TESTS'),
    reason="Integration tests need running server"
)
class TestZapierIntegration:
    """Integration Tests für Zapier Webhook Endpoint"""
    
    @pytest.fixture
    def base_url(self):
        """Test-Server URL"""
        return "http://localhost:8080"
    
    @pytest.mark.asyncio
    async def test_zapier_webhook_complete_flow(self, base_url):
        """Test: Kompletter Zapier Webhook Flow"""
        test_fin = f"TEST_ZAPIER_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        async with httpx.AsyncClient() as client:
            # Sende Webhook
            response = await client.post(
                f"{base_url}/api/v1/integration/zapier/webhook",
                json={
                    "fahrzeug_fin": test_fin,
                    "prozess_name": "einkauf",
                    "neuer_status": "AKTIV",
                    "bearbeiter_name": "Thomas K.",
                    "prioritaet": "2",
                    "notizen": "Integration Test",
                    "marke": "Audi",
                    "modell": "A4"
                }
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result['success'] is True
            assert result['fin'] == test_fin
            
            # Verifiziere Fahrzeug wurde angelegt
            vehicle_response = await client.get(
                f"{base_url}/api/v1/vehicles/{test_fin}"
            )
            
            if vehicle_response.status_code == 200:
                vehicle = vehicle_response.json()
                assert vehicle['fin'] == test_fin
                assert vehicle['prozess_typ'] == 'Einkauf'
    
    @pytest.mark.asyncio
    async def test_zapier_process_transition(self, base_url):
        """Test: Prozesswechsel via Zapier"""
        test_fin = f"TEST_TRANSITION_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        async with httpx.AsyncClient() as client:
            # Erstelle Fahrzeug mit Einkauf
            await client.post(
                f"{base_url}/api/v1/integration/zapier/webhook",
                json={
                    "fahrzeug_fin": test_fin,
                    "prozess_name": "einkauf",
                    "neuer_status": "AKTIV"
                }
            )
            
            # Wechsel zu Aufbereitung
            response = await client.post(
                f"{base_url}/api/v1/integration/zapier/webhook",
                json={
                    "fahrzeug_fin": test_fin,
                    "prozess_name": "gwa",
                    "neuer_status": "AKTIV"
                }
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result['success'] is True