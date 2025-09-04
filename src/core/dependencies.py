"""
Dependencies Configuration - Service Injection für FastAPI
Reinhardt Automobile GmbH - RA Autohaus Tracker

Zentrale Dependency Injection für alle Services mit Singleton-Pattern.
"""

import os
from functools import lru_cache
from typing import Optional

import structlog
from src.services.bigquery_service import BigQueryService
from src.services.vehicle_service import VehicleService
from src.services.process_service import ProcessService

# Strukturiertes Logging
logger = structlog.get_logger(__name__)

# Global Service Instances (Singleton Pattern)
_bigquery_service: Optional[BigQueryService] = None
_vehicle_service: Optional[VehicleService] = None
_process_service: Optional[ProcessService] = None

@lru_cache()
def get_bigquery_service() -> BigQueryService:
    """
    Singleton BigQuery Service mit Lazy Loading.
    
    Returns:
        BigQueryService: Zentrale BigQuery Service Instanz
    """
    global _bigquery_service
    
    if _bigquery_service is None:
        try:
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            dataset_name = os.getenv('BIGQUERY_DATASET')
            
            _bigquery_service = BigQueryService(
                project_id=project_id,
                dataset_name=dataset_name
            )
            
            logger.info("✅ BigQuery Service initialisiert", 
                       project=project_id, 
                       dataset=dataset_name)
            
        except Exception as e:
            logger.error("❌ BigQuery Service Initialisierung fehlgeschlagen", error=str(e))
            # Fallback zu Mock-Service
            _bigquery_service = BigQueryService()
            logger.warning("🔄 Fallback zu Mock BigQuery Service")
    
    return _bigquery_service

@lru_cache()  
def get_vehicle_service() -> VehicleService:
    """
    Singleton Vehicle Service mit BigQuery Dependency.
    
    Returns:
        VehicleService: Business Logic Service für Fahrzeuge
    """
    global _vehicle_service
    
    if _vehicle_service is None:
        try:
            bigquery_service = get_bigquery_service()
            _vehicle_service = VehicleService(bigquery_service=bigquery_service)
            
            logger.info("✅ Vehicle Service initialisiert")
            
        except Exception as e:
            logger.error("❌ Vehicle Service Initialisierung fehlgeschlagen", error=str(e))
            raise
    
    return _vehicle_service

@lru_cache()
def get_process_service() -> ProcessService:
    """
    Singleton Process Service mit Dependencies.
    
    Returns:
        ProcessService: Business Logic Service für Prozesse
    """
    global _process_service
    
    if _process_service is None:
        try:
            vehicle_service = get_vehicle_service()
            bigquery_service = get_bigquery_service()
            _process_service = ProcessService(
                vehicle_service=vehicle_service,
                bigquery_service=bigquery_service
            )
            
            logger.info("✅ Process Service initialisiert")
            
        except Exception as e:
            logger.error("❌ Process Service Initialisierung fehlgeschlagen", error=str(e))
            raise
    
    return _process_service

# Health Check für alle Services
async def check_all_services_health() -> dict:
    """
    Führt Health Check für alle initialisierten Services durch.
    
    Returns:
        dict: Status aller Services
    """
    health_status = {
        'overall_status': 'healthy',
        'services': {}
    }
    
    # BigQuery Service Check
    try:
        bigquery_service = get_bigquery_service()
        bigquery_health = await bigquery_service.health_check()
        health_status['services']['bigquery'] = bigquery_health
        
        if bigquery_health['status'] != 'healthy':
            health_status['overall_status'] = 'degraded'
            
    except Exception as e:
        health_status['services']['bigquery'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['overall_status'] = 'unhealthy'
    
    # Vehicle Service Check
    try:
        vehicle_service = get_vehicle_service()
        vehicle_health = await vehicle_service.health_check()
        health_status['services']['vehicle'] = vehicle_health
        
        if vehicle_health['status'] != 'healthy':
            health_status['overall_status'] = 'degraded'
            
    except Exception as e:
        health_status['services']['vehicle'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['overall_status'] = 'unhealthy'
    
    return health_status

# Configuration & Environment
def get_environment_config() -> dict:
    """
    Liefert aktuelle Environment-Konfiguration.
    
    Returns:
        dict: Environment-Einstellungen
    """
    return {
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'google_cloud_project': os.getenv('GOOGLE_CLOUD_PROJECT'),
        'bigquery_dataset': os.getenv('BIGQUERY_DATASET'),
        'use_mock_bigquery': os.getenv('USE_MOCK_BIGQUERY', 'false').lower() == 'true',
        'api_host': os.getenv('API_HOST', '0.0.0.0'),
        'api_port': int(os.getenv('API_PORT', 8080))
    }

# Startup & Shutdown Hooks
async def startup_services():
    """
    Initialisiert alle Services beim Application Startup.
    """
    try:
        logger.info("🚀 Services werden initialisiert...")
        
        # Environment-Info loggen
        config = get_environment_config()
        logger.info("📋 Environment-Konfiguration", **config)
        
        # Core Services initialisieren
        bigquery_service = get_bigquery_service()
        vehicle_service = get_vehicle_service()
        
        # Health Check durchführen
        health = await check_all_services_health()
        logger.info("🏥 Startup Health Check", **health)
        
        if health['overall_status'] == 'unhealthy':
            logger.error("❌ Services sind nicht gesund - Application könnte nicht korrekt funktionieren")
        
        logger.info("✅ Services erfolgreich initialisiert")
        
    except Exception as e:
        logger.error("💥 Kritischer Fehler beim Service-Startup", error=str(e))
        raise

async def shutdown_services():
    """
    Räumt Services beim Application Shutdown auf.
    """
    try:
        logger.info("🛑 Services werden heruntergefahren...")
        
        # Services cleanup (falls erforderlich)
        # Aktuell keine spezielle Cleanup-Logik erforderlich
        
        logger.info("✅ Services erfolgreich heruntergefahren")
        
    except Exception as e:
        logger.error("❌ Fehler beim Service-Shutdown", error=str(e))

# Development Utilities

def reset_services():
    """
    Setzt alle Service-Singletons zurück (Development only).
    
    ⚠️ Nur für Development/Testing verwenden!
    """
    global _bigquery_service, _vehicle_service
    
    logger.info("🔄 Services werden zurückgesetzt...")
    
    # Cache der lru_cache Funktionen leeren
    get_bigquery_service.cache_clear()
    get_vehicle_service.cache_clear()
    
    # Global Singletons zurücksetzen
    _bigquery_service = None
    _vehicle_service = None
    
    logger.info("✅ Services erfolgreich zurückgesetzt")


def get_service_info() -> dict:
    """
    Liefert Informationen über alle Services für Debugging.
    
    Returns:
        dict: Service-Informationen
    """
    return {
        'bigquery_service': {
            'initialized': _bigquery_service is not None,
            'class': str(type(_bigquery_service)) if _bigquery_service else None,
            'cache_info': str(get_bigquery_service.cache_info())
        },
        'vehicle_service': {
            'initialized': _vehicle_service is not None,  
            'class': str(type(_vehicle_service)) if _vehicle_service else None,
            'cache_info': str(get_vehicle_service.cache_info())
        },
        'environment': get_environment_config()
    }

