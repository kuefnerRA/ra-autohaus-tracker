# src/api/routes/info.py
"""Info API Routes für System-Informationen"""

from fastapi import APIRouter
from typing import Dict, Any

from src.services.info_service import InfoService

router = APIRouter(prefix="/info", tags=["System Info"])

@router.get("/prozesse")
async def get_prozesse_info():
    """
    Info über alle verfügbaren Prozesse
    """
    return InfoService.get_prozesse_info()

@router.get("/bearbeiter")
async def get_bearbeiter_info():
    """
    Info über alle Bearbeiter
    """
    return InfoService.get_bearbeiter_info()

@router.get("/system")
async def get_system_info():
    """
    System-Konfiguration und Einstellungen
    """
    return InfoService.get_system_config()

@router.get("/health")
async def info_health():
    """Info Service Gesundheitscheck"""
    return {
        "service": "InfoService",
        "status": "healthy", 
        "endpoints": ["/info/prozesse", "/info/bearbeiter", "/info/system"]
    }