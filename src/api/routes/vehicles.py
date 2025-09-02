# src/api/routes/vehicles.py
"""Vehicle API Routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
import logging

from src.services.vehicle_service import VehicleService
from src.core.dependencies import get_vehicle_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fahrzeuge", tags=["Fahrzeuge"])

@router.get("")
async def get_fahrzeuge(
    status: Optional[str] = Query(None, description="Filter nach Status"),
    prozess: Optional[str] = Query(None, description="Filter nach Prozess"),
    limit: int = Query(50, ge=1, le=1000, description="Anzahl Ergebnisse"),
    vehicle_service: VehicleService = Depends(get_vehicle_service)
):
    """
    Alle Fahrzeuge mit optionalen Filtern abrufen
    """
    try:
        return await vehicle_service.get_vehicles(
            status=status,
            prozess=prozess,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Fahrzeuge abrufen Fehler: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Fahrzeuge konnten nicht abgerufen werden: {str(e)}"
        )

@router.get("/{fin}")
async def get_fahrzeug_details(
    fin: str,
    vehicle_service: VehicleService = Depends(get_vehicle_service)
):
    """
    Details eines spezifischen Fahrzeugs abrufen
    """
    try:
        vehicle = await vehicle_service.get_vehicle_details(fin)
        
        if not vehicle:
            raise HTTPException(
                status_code=404, 
                detail=f"Fahrzeug mit FIN {fin} nicht gefunden"
            )
            
        return vehicle
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fahrzeug Details Fehler für FIN {fin}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Fahrzeug-Details konnten nicht abgerufen werden: {str(e)}"
        )