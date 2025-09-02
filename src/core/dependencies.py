# src/core/dependencies.py - Angepasst für BigQueryService
"""Dependencies für Service-Injection"""

import logging
from typing import Optional
from src.services.bigquery_service import BigQueryService
from src.services.vehicle_service import VehicleService
from src.services.dashboard_service import DashboardService
from src.services.process_service import ProcessService
from src.services.info_service import InfoService

logger = logging.getLogger(__name__)

# Globale Service-Instanzen
_bq_service: Optional[BigQueryService] = None
_vehicle_service: Optional[VehicleService] = None
_dashboard_service: Optional[DashboardService] = None
_process_service: Optional[ProcessService] = None
_info_service: Optional[InfoService] = None

def set_bigquery_service(bq_service: BigQueryService):
    """BigQuery Service für alle anderen Services setzen"""
    global _bq_service, _vehicle_service, _dashboard_service, _process_service, _info_service
    
    _bq_service = bq_service
    
    # Alle anderen Services mit BigQueryService initialisieren
    _vehicle_service = VehicleService(bq_service=bq_service)
    _dashboard_service = DashboardService(bq_service=bq_service)
    _process_service = ProcessService(bq_service=bq_service)
    _info_service = InfoService()  # InfoService braucht keine BigQuery-Verbindung
    
    logger.info("✅ Alle Services mit BigQueryService initialisiert")

def get_bigquery_service() -> Optional[BigQueryService]:
    """BigQuery Service abrufen"""
    return _bq_service

def get_vehicle_service() -> Optional[VehicleService]:
    """Vehicle Service abrufen"""
    return _vehicle_service

def get_dashboard_service() -> Optional[DashboardService]:
    """Dashboard Service abrufen"""
    return _dashboard_service

def get_process_service() -> Optional[ProcessService]:
    """Process Service abrufen"""
    return _process_service

def get_info_service() -> Optional[InfoService]:
    """Info Service abrufen"""
    return _info_service

def get_services_health() -> dict:
    """Health Status aller Services"""
    return {
        'bigquery_service': _bq_service is not None,
        'vehicle_service': _vehicle_service is not None,
        'dashboard_service': _dashboard_service is not None,
        'process_service': _process_service is not None,
        'info_service': _info_service is not None
    }

# Legacy-Funktionen für Rückwärtskompatibilität
def set_bigquery_client(bq_client):
    """Legacy - erstellt BigQueryService aus Client"""
    if bq_client:
        bq_service = BigQueryService()
        bq_service.client = bq_client  # Bestehenden Client übernehmen
        set_bigquery_service(bq_service)
    else:
        set_bigquery_service(None)