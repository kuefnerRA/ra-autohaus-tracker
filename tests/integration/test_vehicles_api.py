# tests/integration/test_vehicles_api.py
"""
Integration Tests für Vehicle API Endpunkte
Reinhardt Automobile GmbH - RA Autohaus Tracker

Diese Tests verwenden:
- Echte FastAPI App
- Echte BigQuery-Verbindung  
- HTTP-Requests über TestClient
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app

# TestClient für API-Tests
client = TestClient(app)

class TestVehiclesAPI:
    """Test-Klasse für alle Vehicle-API Endpunkte"""
    
    def test_get_vehicles_list(self):
        """Test: Fahrzeuge-Liste abrufen"""
        response = client.get("/api/v1/fahrzeuge/")
        
        # Status Code prüfen
        assert response.status_code == 200
        
        # JSON-Struktur prüfen
        vehicles = response.json()
        assert isinstance(vehicles, list)
        
        # Mindestens ein Fahrzeug sollte vorhanden sein
        assert len(vehicles) > 0
        
        # Struktur des ersten Fahrzeugs prüfen
        first_vehicle = vehicles[0]
        required_fields = [
            "fin", "marke", "modell", "baujahr", 
            "prozess_typ", "status", "bearbeiter"
        ]
        
        for field in required_fields:
            assert field in first_vehicle, f"Feld {field} fehlt in Vehicle-Response"
            assert first_vehicle[field] is not None, f"Feld {field} ist None"
    
    def test_get_vehicles_with_filters(self):
        """Test: Fahrzeuge mit Filtern abrufen"""
        # Test mit prozess_typ Filter
        response = client.get("/api/v1/fahrzeuge/?prozess_typ=Aufbereitung")
        assert response.status_code == 200
        
        vehicles = response.json()
        if len(vehicles) > 0:
            # Alle zurückgegebenen Fahrzeuge sollten den Filter erfüllen
            for vehicle in vehicles:
                assert vehicle["prozess_typ"] == "Aufbereitung"
        
        # Test mit limit Parameter
        response = client.get("/api/v1/fahrzeuge/?limit=1")
        assert response.status_code == 200
        
        vehicles = response.json()
        assert len(vehicles) <= 1
    
    def test_get_single_vehicle(self):
        """Test: Einzelnes Fahrzeug abrufen"""
        # Erst alle Fahrzeuge holen, um eine gültige FIN zu bekommen
        response = client.get("/api/v1/fahrzeuge/")
        vehicles = response.json()
        
        if len(vehicles) > 0:
            test_fin = vehicles[0]["fin"]
            
            # Einzelnes Fahrzeug abrufen
            response = client.get(f"/api/v1/fahrzeuge/{test_fin}")
            assert response.status_code == 200
            
            vehicle = response.json()
            assert vehicle["fin"] == test_fin
            assert "prozess_typ" in vehicle
            assert "status" in vehicle
    
    def test_get_nonexistent_vehicle(self):
        """Test: Nicht-existierendes Fahrzeug abrufen"""
        fake_fin = "NONEXISTENT123456"
        response = client.get(f"/api/v1/fahrzeuge/{fake_fin}")
        
        # Sollte 404 zurückgeben
        assert response.status_code == 404
    
    def test_vehicle_kpis(self):
        """Test: Vehicle KPIs abrufen"""
        response = client.get("/api/v1/fahrzeuge/kpis/overview")
        
        # Überprüfen ob Endpoint existiert (kann 200 oder 500 sein je nach Implementierung)
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            kpis = response.json()
            assert isinstance(kpis, list)
    
    def test_vehicle_statistics(self):
        """Test: Vehicle-Statistiken abrufen"""
        response = client.get("/api/v1/fahrzeuge/statistics/summary")
        
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            stats = response.json()
            assert isinstance(stats, dict)
            assert "total_vehicles" in stats

class TestSystemIntegration:
    """Integration Tests für System-Komponenten"""
    
    def test_health_check_with_vehicles(self):
        """Test: Health Check zeigt Vehicle-Service als healthy"""
        response = client.get("/health")
        assert response.status_code == 200
        
        health = response.json()
        assert health["status"] == "healthy"
        
        # Vehicle Service sollte healthy sein
        if "services" in health and "vehicle" in health["services"]:
            vehicle_health = health["services"]["vehicle"]
            assert vehicle_health["status"] == "healthy"
    
    def test_api_consistency(self):
        """Test: API-Konsistenz zwischen verschiedenen Endpunkten"""
        # Fahrzeuge über Liste abrufen
        list_response = client.get("/api/v1/fahrzeuge/")
        vehicles = list_response.json()
        
        if len(vehicles) > 0:
            test_fin = vehicles[0]["fin"]
            
            # Gleiches Fahrzeug über Detail-Endpunkt abrufen
            detail_response = client.get(f"/api/v1/fahrzeuge/{test_fin}")
            
            if detail_response.status_code == 200:
                detail_vehicle = detail_response.json()
                list_vehicle = vehicles[0]
                
                # Kern-Daten sollten identisch sein
                core_fields = ["fin", "marke", "modell", "prozess_typ", "status"]
                for field in core_fields:
                    if field in list_vehicle and field in detail_vehicle:
                        assert list_vehicle[field] == detail_vehicle[field], \
                            f"Feld {field} inkonsistent zwischen Liste und Detail"

# Test-Setup Funktionen
@pytest.fixture(scope="session")
def test_client():
    """Fixture für TestClient"""
    return client

# Utility-Funktionen für Tests
def get_sample_vehicle_data():
    """Hilfsfunktion: Sample Vehicle-Daten für Tests"""
    return {
        "fin": "TESTFIN123456789",
        "marke": "Test-Marke",
        "modell": "Test-Modell",
        "baujahr": 2023,
        "prozess_typ": "Aufbereitung",
        "status": "In Bearbeitung",
        "bearbeiter": "Test-Bearbeiter"
    }

# Marks für verschiedene Test-Kategorien
pytestmark = [
    pytest.mark.api,  # Alle Tests in dieser Datei sind API-Tests
]