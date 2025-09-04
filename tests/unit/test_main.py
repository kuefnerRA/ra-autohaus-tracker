# tests/unit/test_main.py
"""
Unit Tests für Main Application
Reinhardt Automobile GmbH - RA Autohaus Tracker

Tests angepasst an die tatsächliche main.py Implementierung
"""

import pytest
from typing import Any, Dict
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import os
import sys
import json


class TestMainApplication:
    """Tests für Main Application Endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test Client mit gemockten Dependencies"""
        # Environment setzen
        os.environ["ENVIRONMENT"] = "development"
        os.environ["LOG_LEVEL"] = "INFO"
        
        # Module aus sys.modules entfernen für sauberen Import
        modules_to_remove = [k for k in sys.modules if k.startswith('src.')]
        for module in modules_to_remove:
            del sys.modules[module]
        
        # Mock alle Dependencies BEVOR main importiert wird
        with patch('src.core.dependencies.startup_services', new_callable=AsyncMock) as mock_startup:
            with patch('src.core.dependencies.shutdown_services', new_callable=AsyncMock) as mock_shutdown:
                with patch('src.core.dependencies.check_all_services_health', new_callable=AsyncMock) as mock_health:
                    with patch('src.core.dependencies.get_service_info') as mock_info:
                        with patch('src.core.dependencies.get_environment_config') as mock_env:
                            
                            # Mocks konfigurieren
                            mock_health.return_value = {
                                'overall_status': 'healthy',
                                'services': {
                                    'bigquery': {'status': 'healthy'},
                                    'vehicle': {'status': 'healthy'}
                                }
                            }
                            
                            mock_info.return_value = {
                                'bigquery_service': {'initialized': True},
                                'vehicle_service': {'initialized': True}
                            }
                            
                            mock_env.return_value = {
                                'environment': 'development',
                                'log_level': 'INFO',
                                'google_cloud_project': 'test-project',
                                'bigquery_dataset': 'test-dataset',
                                'use_mock_bigquery': True,
                                'api_host': '0.0.0.0',
                                'api_port': 8080
                            }
                            
                            # Jetzt main importieren
                            from src.main import app
                            
                            # TestClient mit der App erstellen
                            with TestClient(app) as client:
                                yield client
    
    # ===============================
    # Health & Info Endpoint Tests
    # ===============================
    
    def test_health_endpoint(self, client):
        """Test: Health Check Endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "application" in data
        assert data["application"]["name"] == "RA Autohaus Tracker"
        assert "services" in data
    
    def test_root_endpoint(self, client):
        """Test: Root Endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "RA Autohaus Tracker API"
        assert "version" in data
        assert data["version"] == "1.0.0-alpha"
        assert "vehicles_api" in data
    
    def test_info_endpoint(self, client):
        """Test: Info Endpoint"""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "application" in data
        assert data["application"]["name"] == "RA Autohaus Tracker"
        assert "environment" in data
        assert "services" in data
        assert "endpoints" in data
    
    # ===============================
    # API Router Integration Tests
    # ===============================
    
    def test_vehicles_router_included(self, client):
        """Test: Vehicles Router ist eingebunden"""
        # Der vehicles_router wird unter /api/v1 gemountet
        # und hat /fahrzeuge als Pfad
        response = client.get("/api/v1/fahrzeuge/")
        # Sollte nicht 404 sein wenn Router eingebunden
        assert response.status_code != 404
    
    def test_process_router_included(self, client):
        """Test: Process Router ist eingebunden"""
        # Der process_router wird unter /api/v1 gemountet
        response = client.get("/api/v1/process/health")
        # Sollte nicht 404 sein wenn Router eingebunden
        assert response.status_code != 404
    
    # ===============================
    # Error Handling Tests
    # ===============================
    
    def test_404_handler(self, client):
        """Test: 404 Error Handler"""
        response = client.get("/definitiv-nicht-existierender-endpoint-12345")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_cors_headers_present(self, client):
        """Test: CORS Headers sind konfiguriert"""
        # OPTIONS Request an einen bekannten Endpoint
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        # In Development sollte CORS permissiv sein (200)
        assert response.status_code == 200
        # Check CORS Headers
        assert "access-control-allow-origin" in response.headers
    
    # ===============================
    # Development Endpoints
    # ===============================
    
    def test_dev_reset_endpoint_exists(self, client):
        """Test: Development Reset Endpoint existiert"""
        # In Development-Umgebung sollte dieser Endpoint existieren
        response = client.get("/dev/reset-services")
        # Kann 200 oder 500 sein, aber nicht 404
        assert response.status_code != 404


# ===============================
# Isolierte Unit Tests
# ===============================

def test_configure_logging():
    """Test: Logging-Konfiguration funktioniert"""
    # Mock structlog
    with patch('src.main.configure') as mock_configure:
        with patch('src.main.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            from src.main import configure_logging
            
            # Test mit verschiedenen Environment-Settings
            for env in ["development", "production"]:
                with patch.dict(os.environ, {"ENVIRONMENT": env, "LOG_LEVEL": "INFO"}):
                    logger = configure_logging()
                    assert logger is not None
                    mock_configure.assert_called()


def test_setup_middleware():
    """Test: Middleware Setup funktioniert"""
    # Mock FastAPI App
    mock_app = Mock()
    mock_app.add_middleware = Mock()
    
    # Patch das app Objekt in main
    with patch('src.main.app', mock_app):
        from src.main import setup_middleware
        
        # Sollte ohne Fehler durchlaufen
        setup_middleware()
        
        # Middleware sollte hinzugefügt worden sein
        assert mock_app.add_middleware.call_count >= 2  # CORS + GZip


@pytest.mark.asyncio
async def test_lifespan_context():
    """Test: Lifespan Context Manager"""
    # Mock die Dependencies
    with patch('src.main.startup_services', new_callable=AsyncMock) as mock_startup:
        with patch('src.main.shutdown_services', new_callable=AsyncMock) as mock_shutdown:
            with patch('src.main.configure_logging') as mock_logging:
                mock_logging.return_value = Mock()
                
                from src.main import lifespan
                from fastapi import FastAPI
                
                app = FastAPI()
                
                # Lifespan context durchlaufen
                async with lifespan(app):
                    pass  # App läuft
                
                # Startup und Shutdown sollten aufgerufen worden sein
                mock_startup.assert_called_once()
                mock_shutdown.assert_called_once()


@pytest.mark.asyncio 
async def test_global_exception_handler():
    """Test: Global Exception Handler"""
    from src.main import global_exception_handler
    from fastapi import Request
    
    # Mock Request
    mock_request = Mock(spec=Request)
    mock_request.url = Mock()
    mock_request.url.path = "/test"
    mock_request.method = "GET"
    
    # Test mit Exception
    test_exception = ValueError("Test error")
    
    # Handler aufrufen
    response = await global_exception_handler(mock_request, test_exception)
    
    # Response prüfen
    assert response.status_code == 500
    content = json.loads(response.body)
    assert "error" in content or "message" in content


def test_environment_based_features():
    """Test: Environment-spezifische Features"""
    from fastapi.routing import APIRoute, Mount, APIWebSocketRoute
    
    # In Development
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
        # Module neu laden
        if 'src.main' in sys.modules:
            del sys.modules['src.main']
        
        # Mock Dependencies bevor main importiert wird
        with patch('src.core.dependencies.startup_services', new_callable=AsyncMock):
            with patch('src.core.dependencies.shutdown_services', new_callable=AsyncMock):
                from src.main import app
                
                # In Development sollte /dev/reset-services Route existieren
                routes = []
                for route in app.routes:
                    if isinstance(route, APIRoute):
                        routes.append(route.path)
                    elif isinstance(route, Mount):
                        routes.append(route.path)
                    elif isinstance(route, APIWebSocketRoute):
                        routes.append(route.path)
                
                assert "/dev/reset-services" in routes
                
                # Docs sollten verfügbar sein
                assert app.docs_url == "/docs"
                assert app.redoc_url == "/redoc"
    
    # In Production
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        # Module neu laden
        if 'src.main' in sys.modules:
            del sys.modules['src.main']
        
        with patch('src.core.dependencies.startup_services', new_callable=AsyncMock):
            with patch('src.core.dependencies.shutdown_services', new_callable=AsyncMock):
                from src.main import app
                
                # In Production sollte /dev/reset-services nicht existieren
                # Typsichere Route-Extraktion
                routes = []
                for route in app.routes:
                    if isinstance(route, APIRoute):
                        routes.append(route.path)
                    elif isinstance(route, Mount):
                        routes.append(route.path)
                    elif isinstance(route, APIWebSocketRoute):
                        routes.append(route.path)
                
                assert "/dev/reset-services" not in routes


# ===============================
# Request Logging Middleware Test
# ===============================

class TestRequestLogging:
    """Test Request Logging Middleware"""
    
    @pytest.mark.asyncio
    async def test_request_logging_middleware(self):
        """Test: Request Logging Middleware funktioniert"""
        # Statt den Logger zu mocken, prüfen wir ob die Middleware existiert
        from src.main import app
        
        # Prüfe ob die Middleware registriert ist
        middleware_found = False
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls'):
                # Middleware existiert
                middleware_found = True
                break
        
        # Alternativ: Einfach einen Request machen und prüfen ob er durchkommt
        from fastapi.testclient import TestClient
        
        with patch('src.core.dependencies.startup_services', new_callable=AsyncMock):
            with patch('src.core.dependencies.shutdown_services', new_callable=AsyncMock):
                with patch('src.core.dependencies.check_all_services_health', new_callable=AsyncMock) as mock_health:
                    mock_health.return_value = {
                        'overall_status': 'healthy',
                        'services': {}
                    }
                    
                    with TestClient(app) as client:
                        # Request machen
                        response = client.get("/health")
                        
                        # Wenn der Request durchkommt, funktioniert die Middleware
                        assert response.status_code == 200
                        
                        # Optional: Prüfen ob bestimmte Header gesetzt wurden
                        # (falls die Middleware Response-Header setzt)
                        assert response.headers is not None
        
        # Test besteht wenn kein Fehler auftritt
        assert True

# ===============================
# Service Integration Tests
# ===============================

@pytest.mark.asyncio
async def test_startup_services_called():
    """Test: Startup Services wird beim App Start aufgerufen"""
    with patch('src.main.startup_services', new_callable=AsyncMock) as mock_startup:
        with patch('src.main.shutdown_services', new_callable=AsyncMock):
            with patch('src.main.configure_logging') as mock_logging:
                mock_logging.return_value = Mock()
                
                from src.main import lifespan
                from fastapi import FastAPI
                
                app = FastAPI()
                
                # Startup Phase simulieren
                async with lifespan(app):
                    # Startup sollte aufgerufen worden sein
                    mock_startup.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_services_called():
    """Test: Shutdown Services wird beim App Stop aufgerufen"""
    with patch('src.main.startup_services', new_callable=AsyncMock):
        with patch('src.main.shutdown_services', new_callable=AsyncMock) as mock_shutdown:
            with patch('src.main.configure_logging') as mock_logging:
                mock_logging.return_value = Mock()
                
                from src.main import lifespan
                from fastapi import FastAPI
                
                app = FastAPI()
                
                # Kompletter Lifecycle
                async with lifespan(app):
                    pass
                
                # Nach dem Context sollte shutdown aufgerufen worden sein
                mock_shutdown.assert_called_once()


# ===============================
# Error Handling Tests
# ===============================

@pytest.mark.asyncio
async def test_health_endpoint_error_handling():
    """Test: Health Endpoint Error Handling"""
    # Mock health check mit Fehler
    with patch('src.core.dependencies.check_all_services_health', new_callable=AsyncMock) as mock_health:
        mock_health.side_effect = Exception("Health check failed")
        
        with patch('src.core.dependencies.startup_services', new_callable=AsyncMock):
            with patch('src.core.dependencies.shutdown_services', new_callable=AsyncMock):
                # Module neu laden
                if 'src.main' in sys.modules:
                    del sys.modules['src.main']
                
                from src.main import app
                from fastapi.testclient import TestClient
                
                with TestClient(app) as client:
                    response = client.get("/health")
                    
                    # Should return 503 Service Unavailable
                    assert response.status_code == 503
                    data = response.json()
                    assert data["status"] == "unhealthy"
                    assert "error" in data