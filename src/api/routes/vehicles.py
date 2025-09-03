"""
Vehicle API Routes - REST Endpunkte
Reinhardt Automobile GmbH - RA Autohaus Tracker

REST-API für Fahrzeugverwaltung mit vollständiger CRUD-Funktionalität.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
import structlog

from src.core.dependencies import get_vehicle_service
from src.services.vehicle_service import VehicleService
from src.models.integration import (
    FahrzeugStammCreate, FahrzeugStammResponse,
    FahrzeugProzessCreate, FahrzeugProzessResponse,
    FahrzeugMitProzess, KPIData, StandardResponse
)

# Router Setup
router = APIRouter(prefix="/fahrzeuge", tags=["Fahrzeuge"])
logger = structlog.get_logger(__name__)

@router.get(
    "/",
    response_model=List[FahrzeugMitProzess],
    summary="Fahrzeuge abrufen",
    description="Holt eine gefilterte Liste von Fahrzeugen mit aktuellen Prozess-Informationen."
)
async def get_vehicles(
    limit: int = Query(100, ge=1, le=1000, description="Maximale Anzahl Ergebnisse"),
    prozess_typ: Optional[str] = Query(None, description="Filter nach Prozesstyp"),
    bearbeiter: Optional[str] = Query(None, description="Filter nach Bearbeiter"),
    sla_critical: bool = Query(False, description="Nur SLA-kritische Fahrzeuge"),
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> List[FahrzeugMitProzess]:
    """
    Fahrzeuge mit erweiterten Filteroptionen abrufen.
    
    **Filter-Optionen:**
    - `limit`: Maximale Anzahl Ergebnisse (1-1000)
    - `prozess_typ`: Einkauf, Aufbereitung, Foto, Werkstatt, Verkauf
    - `bearbeiter`: Name des zuständigen Bearbeiters  
    - `sla_critical`: Nur Fahrzeuge mit kritischen SLA-Deadlines
    
    **Rückgabe:** Liste von Fahrzeugen mit Stamm- und Prozessdaten
    """
    try:
        fahrzeuge = await vehicle_service.get_vehicles(
            limit=limit,
            prozess_typ=prozess_typ,
            bearbeiter=bearbeiter,
            sla_critical_only=sla_critical
        )
        
        logger.info("✅ Fahrzeuge erfolgreich abgerufen",
                   count=len(fahrzeuge),
                   filters={
                       "prozess_typ": prozess_typ,
                       "bearbeiter": bearbeiter,
                       "sla_critical": sla_critical
                   })
        
        return fahrzeuge
        
    except Exception as e:
        logger.error("❌ Fehler beim Abrufen der Fahrzeuge", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Abrufen der Fahrzeuge: {str(e)}"
        )

@router.get(
    "/{fin}",
    response_model=FahrzeugMitProzess,
    summary="Fahrzeug-Details",
    description="Holt detaillierte Informationen zu einem spezifischen Fahrzeug anhand der FIN."
)
async def get_vehicle_details(
    fin: str,
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> FahrzeugMitProzess:
    """
    Detaillierte Fahrzeugdaten für eine spezifische FIN.
    
    **Parameter:**
    - `fin`: 17-stellige Fahrzeugidentifizierungsnummer
    
    **Rückgabe:** Vollständige Fahrzeug- und Prozessdaten
    """
    try:
        fahrzeug = await vehicle_service.get_vehicle_details(fin)
        
        if not fahrzeug:
            logger.info("ℹ️ Fahrzeug nicht gefunden", fin=fin)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fahrzeug mit FIN {fin} nicht gefunden"
            )
        
        logger.info("✅ Fahrzeug-Details erfolgreich abgerufen", fin=fin)
        return fahrzeug
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Fehler beim Abrufen der Fahrzeug-Details", fin=fin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Abrufen der Fahrzeug-Details: {str(e)}"
        )

@router.post(
    "/",
    response_model=FahrzeugMitProzess,
    status_code=status.HTTP_201_CREATED,
    summary="Fahrzeug erstellen",
    description="Erstellt ein neues Fahrzeug mit Stammdaten und optionalem Prozess."
)
async def create_vehicle(
    fahrzeug_data: FahrzeugStammCreate,
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> FahrzeugMitProzess:
    """
    Erstellt ein neues Fahrzeug mit Stammdaten.
    
    **Request Body:**
    - `fahrzeug_data`: Fahrzeugstammdaten (FIN ist erforderlich)
    
    **Rückgabe:** Erstelltes Fahrzeug mit allen Daten
    """
    try:
        created_vehicle = await vehicle_service.create_complete_vehicle(
            fahrzeug_data=fahrzeug_data
        )
        
        logger.info("✅ Fahrzeug erfolgreich erstellt", fin=fahrzeug_data.fin)
        
        return created_vehicle
        
    except ValueError as e:
        logger.error("❌ Validierungsfehler beim Erstellen", fin=fahrzeug_data.fin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("❌ Fehler beim Erstellen des Fahrzeugs", fin=fahrzeug_data.fin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Erstellen des Fahrzeugs: {str(e)}"
        )

@router.put(
    "/{fin}/status",
    response_model=StandardResponse,
    summary="Fahrzeugstatus ändern",
    description="Aktualisiert den Status eines Fahrzeugprozesses."
)
async def update_vehicle_status(
    fin: str,
    new_status: str = Query(..., description="Neuer Prozess-Status"),
    bearbeiter: Optional[str] = Query(None, description="Neuer Bearbeiter"),
    notizen: Optional[str] = Query(None, description="Notizen zum Statuswechsel"),
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> StandardResponse:
    """
    Aktualisiert den Prozess-Status eines Fahrzeugs.
    
    **Parameter:**
    - `fin`: Fahrzeugidentifizierungsnummer
    - `new_status`: Neuer Prozess-Status
    - `bearbeiter`: Optional - Neuer Bearbeiter
    - `notizen`: Optional - Notizen zum Statuswechsel
    
    **Rückgabe:** Erfolgs-Bestätigung
    """
    try:
        success = await vehicle_service.update_vehicle_status(
            fin=fin,
            new_status=new_status,
            bearbeiter=bearbeiter,
            notizen=notizen
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status-Update fehlgeschlagen"
            )
        
        logger.info("✅ Fahrzeugstatus erfolgreich aktualisiert", 
                   fin=fin, 
                   new_status=new_status,
                   bearbeiter=bearbeiter)
        
        return StandardResponse(
            success=True,
            message=f"Fahrzeugstatus für {fin} erfolgreich auf '{new_status}' aktualisiert",
            timestamp=datetime.now()
        )
        
    except ValueError as e:
        logger.error("❌ Validierungsfehler beim Status-Update", fin=fin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("❌ Fehler beim Status-Update", fin=fin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Status-Update: {str(e)}"
        )

@router.get(
    "/kpis/overview",
    response_model=List[KPIData],
    summary="Fahrzeug-KPIs",
    description="Liefert Key Performance Indicators für alle Fahrzeuge."
)
async def get_vehicle_kpis(
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> List[KPIData]:
    """
    Fahrzeug-bezogene Key Performance Indicators.
    
    **KPIs enthalten:**
    - Gesamtanzahl Fahrzeuge
    - Fahrzeuge nach Prozesstyp
    - SLA-kritische Fahrzeuge
    - Durchschnittliche Einkaufspreise
    - Weitere Geschäftskennzahlen
    
    **Rückgabe:** Liste von KPI-Objekten
    """
    try:
        kpis = await vehicle_service.get_vehicle_kpis()
        
        logger.info("📊 Fahrzeug-KPIs erfolgreich berechnet", kpi_count=len(kpis))
        return kpis
        
    except Exception as e:
        logger.error("❌ Fehler beim Berechnen der Fahrzeug-KPIs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Berechnen der KPIs: {str(e)}"
        )

@router.get(
    "/statistics/summary",
    summary="Fahrzeug-Statistiken",
    description="Liefert zusammengefasste Statistiken aller Fahrzeuge für Dashboard."
)
async def get_vehicle_statistics(
    vehicle_service: VehicleService = Depends(get_vehicle_service)
):
    """
    Zusammengefasste Fahrzeug-Statistiken für Dashboard.
    
    **Statistiken enthalten:**
    - Anzahl Fahrzeuge nach Status
    - Durchschnittspreise nach Marke
    - SLA-Performance
    - Prozesstyp-Verteilung
    
    **Rückgabe:** Statistik-Objekt
    """
    try:
        vehicles = await vehicle_service.get_vehicles(limit=1000)
        
        # Statistiken berechnen
        stats = {
            'total_vehicles': len(vehicles),
            'by_status': {},
            'by_marke': {},
            'by_prozess_typ': {},
            'sla_summary': {
                'critical': 0,
                'warning': 0,
                'ok': 0
            }
        }
        
        for vehicle in vehicles:
            # Status-Verteilung
            vehicle_status = vehicle.status or 'Unbekannt'  # ✅ Neuer Variablenname
            stats['by_status'][vehicle_status] = stats['by_status'].get(vehicle_status, 0) + 1
                        
            # Marken-Verteilung
            marke = vehicle.marke or 'Unbekannt'
            stats['by_marke'][marke] = stats['by_marke'].get(marke, 0) + 1
            
            # Prozesstyp-Verteilung
            prozess = vehicle.prozess_typ or 'Kein Prozess'
            stats['by_prozess_typ'][prozess] = stats['by_prozess_typ'].get(prozess, 0) + 1
            
            # SLA-Status
            if vehicle.tage_bis_sla_deadline is not None:
                if vehicle.tage_bis_sla_deadline <= 0:
                    stats['sla_summary']['critical'] += 1
                elif vehicle.tage_bis_sla_deadline <= 2:
                    stats['sla_summary']['warning'] += 1
                else:
                    stats['sla_summary']['ok'] += 1
        
        logger.info("📈 Fahrzeug-Statistiken erfolgreich berechnet", 
                   total=stats['total_vehicles'])
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error("❌ Fehler beim Berechnen der Statistiken", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Berechnen der Statistiken: {str(e)}"
        )

# Health Check für Vehicle API
@router.get(
    "/health",
    summary="Vehicle API Health",
    description="Gesundheitscheck für die Vehicle-API."
)
async def vehicle_api_health_check(
    vehicle_service: VehicleService = Depends(get_vehicle_service)
):
    """
    Gesundheitscheck für Vehicle-API und zugehörige Services.
    
    **Prüfungen:**
    - Service-Verbindungen
    - Basis-Funktionalität
    - Datenbank-Zugriff
    
    **Rückgabe:** Detaillierter Health-Status
    """
    try:
        service_health = await vehicle_service.health_check()
        
        return JSONResponse(
            content={
                'status': 'healthy',
                'api': 'vehicle',
                'timestamp': datetime.now().isoformat(),
                'service_health': service_health
            }
        )
        
    except Exception as e:
        logger.error("❌ Vehicle API Health Check fehlgeschlagen", error=str(e))
        return JSONResponse(
            content={
                'status': 'unhealthy',
                'api': 'vehicle',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )