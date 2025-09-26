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
    FahrzeugProzessCreate, FahrzeugProzessResponse, FahrzeugProzessRequest,
    FahrzeugMitProzess, KPIData, StandardResponse
)

# Router Setup
router = APIRouter(prefix="/fahrzeuge", tags=["Fahrzeuge"])
logger = structlog.get_logger(__name__)

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

@router.post(
    "/{fin}/prozess",
    response_model=FahrzeugProzessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prozess für Fahrzeug erstellen",
    description="Erstellt einen neuen Prozess für ein bestehendes Fahrzeug."
)
async def create_vehicle_process(
    fin: str,
    prozess_request: FahrzeugProzessRequest,  # <- Verwende FahrzeugProzessRequest
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> FahrzeugProzessResponse:
    """
    Erstellt einen neuen Prozess für ein Fahrzeug.
    
    **Parameter:**
    - `fin`: Fahrzeugidentifizierungsnummer (aus URL)
    - `prozess_request`: Prozessdaten (aus Request Body)
    
    **Request Body:**
    - `prozess_typ`: Art des Prozesses (Einkauf, Aufbereitung, Foto, etc.)
    - `status`: Prozess-Status
    - `bearbeiter`: Optional - Zuständiger Bearbeiter
    - `prioritaet`: Optional - Priorität (1-9)
    - `notizen`: Optional - Notizen zum Prozess
    
    **Rückgabe:** Erstellter Prozess mit allen Daten inkl. SLA
    """
    try:
        # Prüfen ob Fahrzeug existiert
        fahrzeug = await vehicle_service.get_vehicle_details(fin)
        if not fahrzeug:
            logger.error("❌ Fahrzeug nicht gefunden für Prozess-Erstellung", fin=fin)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fahrzeug mit FIN {fin} nicht gefunden"
            )
        
        # Konvertiere Request zu vollständigem FahrzeugProzessCreate
        prozess_data = FahrzeugProzessCreate(
            prozess_id=vehicle_service._generate_process_id(fin, prozess_request.prozess_typ),
            fin=fin,
            **prozess_request.model_dump()
        )
        
        # Prozess erstellen
        created_process = await vehicle_service.create_vehicle_process(
            fin=fin,
            prozess_data=prozess_data
        )
        
        logger.info("✅ Fahrzeugprozess erfolgreich erstellt", 
                   fin=fin,
                   prozess_id=created_process.prozess_id,
                   prozess_typ=prozess_request.prozess_typ)
        
        return created_process
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error("❌ Validierungsfehler beim Prozess-Erstellen", 
                    fin=fin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("❌ Fehler beim Erstellen des Fahrzeugprozesses", 
                    fin=fin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Erstellen des Prozesses: {str(e)}"
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


@router.get(
    "/{fin}/prozesse",
    response_model=List[FahrzeugProzessResponse],
    summary="Prozess-Historie abrufen",
    description="Holt alle Prozesse eines Fahrzeugs (chronologisch sortiert)."
)
async def get_vehicle_processes(
    fin: str,
    limit: int = Query(50, ge=1, le=200, description="Maximale Anzahl Ergebnisse"),
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> List[FahrzeugProzessResponse]:
    """
    Holt die komplette Prozess-Historie eines Fahrzeugs.
    
    **Parameter:**
    - `fin`: Fahrzeugidentifizierungsnummer
    - `limit`: Maximale Anzahl Prozesse (1-200)
    
    **Rückgabe:** Liste aller Prozesse chronologisch sortiert
    """
    try:
        prozesse = await vehicle_service.get_vehicle_process_history(fin, limit)
        
        if not prozesse:
            logger.info("ℹ️ Keine Prozesse für Fahrzeug gefunden", fin=fin)
            return []
        
        logger.info("✅ Prozess-Historie abgerufen", 
                   fin=fin, 
                   prozess_count=len(prozesse))
        
        return prozesse
        
    except Exception as e:
        logger.error("❌ Fehler beim Abrufen der Prozess-Historie", 
                    fin=fin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Abrufen der Prozess-Historie: {str(e)}"
        )    
    
@router.put(
"/{fin}/prozess/{prozess_id}",
response_model=FahrzeugProzessResponse,
summary="Prozess aktualisieren",
description="Aktualisiert einen bestehenden Fahrzeugprozess."
)

async def update_vehicle_process(
    fin: str,
    prozess_id: str,
    prozess_update: FahrzeugProzessRequest,
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> FahrzeugProzessResponse:
    """
    Aktualisiert einen bestehenden Prozess.
    
    **Parameter:**
    - `fin`: Fahrzeugidentifizierungsnummer
    - `prozess_id`: Prozess-ID
    - `prozess_update`: Neue Prozessdaten
    
    **Rückgabe:** Aktualisierter Prozess
    """
    try:
        updated_process = await vehicle_service.update_vehicle_process(
            fin=fin,
            prozess_id=prozess_id,
            prozess_update=prozess_update
        )
        
        if not updated_process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prozess {prozess_id} für Fahrzeug {fin} nicht gefunden"
            )
        
        logger.info("✅ Prozess erfolgreich aktualisiert", 
                   fin=fin,
                   prozess_id=prozess_id,
                   new_status=prozess_update.status)
        
        return updated_process
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Fehler beim Aktualisieren des Prozesses", 
                    fin=fin, 
                    prozess_id=prozess_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Aktualisieren: {str(e)}"
        )
    
@router.delete(
"/{fin}/prozess/{prozess_id}",
response_model=StandardResponse,
summary="Prozess beenden",
description="Beendet einen Fahrzeugprozess (setzt Status auf 'Abgeschlossen')."
)

async def complete_vehicle_process(
    fin: str,
    prozess_id: str,
    abschluss_notiz: Optional[str] = Query(None, description="Abschluss-Notiz"),
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> StandardResponse:
    """
    Beendet einen Prozess (markiert als abgeschlossen).
    
    **Parameter:**
    - `fin`: Fahrzeugidentifizierungsnummer
    - `prozess_id`: Prozess-ID
    - `abschluss_notiz`: Optional - Notiz zum Abschluss
    
    **Rückgabe:** Erfolgs-Bestätigung
    """
    try:
        success = await vehicle_service.complete_vehicle_process(
            fin=fin,
            prozess_id=prozess_id,
            abschluss_notiz=abschluss_notiz
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prozess {prozess_id} nicht gefunden"
            )
        
        logger.info("✅ Prozess erfolgreich abgeschlossen", 
                   fin=fin,
                   prozess_id=prozess_id)
        
        return StandardResponse(
            success=True,
            message=f"Prozess {prozess_id} erfolgreich abgeschlossen",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Fehler beim Abschließen des Prozesses", 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Abschließen: {str(e)}"
        )