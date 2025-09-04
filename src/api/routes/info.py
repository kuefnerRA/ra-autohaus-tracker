# src/api/routes/info.py
"""
Info API Endpoints
Stellt System-Konfiguration und statische Informationen bereit
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from datetime import datetime
import logging

from src.core.dependencies import get_info_service
from src.services.info_service import InfoService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/info", tags=["System Info"])

@router.get("/prozesse", response_model=Dict[str, Any])
async def get_prozesse(
    service: InfoService = Depends(get_info_service)
) -> Dict[str, Any]:
    """
    Gibt alle verfügbaren Prozess-Definitionen zurück
    
    Returns:
        Dict mit allen Prozessen und deren Konfiguration
    """
    try:
        logger.info("ℹ️ Prozess-Definitionen werden abgerufen")
        prozesse = await service.get_prozesse()
        return prozesse
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Prozesse: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prozesse/{prozess_typ}", response_model=Dict[str, Any])
async def get_prozess_details(
    prozess_typ: str,
    service: InfoService = Depends(get_info_service)
) -> Dict[str, Any]:
    """
    Gibt Details zu einem spezifischen Prozess zurück
    
    Args:
        prozess_typ: Name des Prozesses
        
    Returns:
        Detaillierte Prozess-Information
    """
    try:
        logger.info(f"ℹ️ Details für Prozess {prozess_typ} werden abgerufen")
        details = await service.get_prozess_details(prozess_typ)
        
        if "error" in details:
            raise HTTPException(status_code=404, detail=details["error"])
            
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Prozess-Details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bearbeiter", response_model=Dict[str, Any])
async def get_bearbeiter(
    service: InfoService = Depends(get_info_service)
) -> Dict[str, Any]:
    """
    Gibt alle Bearbeiter-Informationen zurück
    
    Returns:
        Dict mit allen Bearbeitern und deren Konfiguration
    """
    try:
        logger.info("ℹ️ Bearbeiter-Informationen werden abgerufen")
        bearbeiter = await service.get_bearbeiter()
        return bearbeiter
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Bearbeiter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bearbeiter/{name}", response_model=Dict[str, Any])
async def get_bearbeiter_details(
    name: str,
    service: InfoService = Depends(get_info_service)
) -> Dict[str, Any]:
    """
    Gibt Details zu einem spezifischen Bearbeiter zurück
    
    Args:
        name: Name des Bearbeiters
        
    Returns:
        Detaillierte Bearbeiter-Information
    """
    try:
        logger.info(f"ℹ️ Details für Bearbeiter {name} werden abgerufen")
        details = await service.get_bearbeiter_details(name)
        
        if "error" in details:
            raise HTTPException(status_code=404, detail=details["error"])
            
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Bearbeiter-Details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=Dict[str, Any])
async def get_status_definitionen(
    service: InfoService = Depends(get_info_service)
) -> Dict[str, Any]:
    """
    Gibt alle Status-Definitionen zurück
    
    Returns:
        Dict mit allen verfügbaren Status und deren Bedeutung
    """
    try:
        logger.info("ℹ️ Status-Definitionen werden abgerufen")
        status = await service.get_status_definitionen()
        return status
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Status-Definitionen: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system", response_model=Dict[str, Any])
async def get_system_config(
    service: InfoService = Depends(get_info_service)
) -> Dict[str, Any]:
    """
    Gibt die komplette System-Konfiguration zurück
    
    Returns:
        Dict mit System-Einstellungen und Features
    """
    try:
        logger.info("ℹ️ System-Konfiguration wird abgerufen")
        config = await service.get_system_config()
        return config
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der System-Config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mappings", response_model=Dict[str, Any])
async def get_mappings(
    service: InfoService = Depends(get_info_service)
) -> Dict[str, Any]:
    """
    Gibt alle Mappings für Integrationen zurück
    
    Returns:
        Dict mit Prozess-, Bearbeiter- und Status-Mappings
    """
    try:
        logger.info("ℹ️ Integration-Mappings werden abgerufen")
        mappings = await service.get_mappings()
        return mappings
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", response_model=Dict[str, Any])
async def get_health_status(
    service: InfoService = Depends(get_info_service)
) -> Dict[str, Any]:
    """
    Health-Check Endpoint für System-Status
    
    Returns:
        Dict mit Health-Status aller Services
    """
    try:
        logger.info("ℹ️ Health-Status wird abgerufen")
        health = await service.get_health_status()
        return health
    except Exception as e:
        logger.error(f"❌ Fehler beim Health-Check: {e}")
        # Bei Health-Check-Fehler trotzdem eine Response zurückgeben
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }