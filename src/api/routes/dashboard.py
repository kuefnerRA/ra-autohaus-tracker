# src/api/routes/dashboard.py
"""
Dashboard API Endpoints
Stellt KPIs und Analytics-Daten bereit
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
from datetime import datetime
import logging

from src.core.dependencies import get_dashboard_service
from src.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/kpis", response_model=Dict[str, Any])
async def get_kpis(
    service: DashboardService = Depends(get_dashboard_service)
) -> Dict[str, Any]:
    """
    Haupt-KPIs für Executive Dashboard
    
    Returns:
        - Fahrzeug-Statistiken
        - Prozess-Übersicht  
        - SLA-Metriken
        - Durchlaufzeiten
    """
    try:
        logger.info("📊 KPIs werden abgerufen")
        kpis = await service.get_kpis()
        return kpis
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/warteschlangen", response_model=Dict[str, List[Dict]])
async def get_warteschlangen(
    service: DashboardService = Depends(get_dashboard_service)
) -> Dict[str, List[Dict]]:
    """
    Warteschlangen-Status für alle Prozesse
    
    Returns:
        Warteschlangen gruppiert nach Prozesstyp
    """
    try:
        logger.info("📊 Warteschlangen werden abgerufen")
        warteschlangen = await service.get_warteschlangen()
        return warteschlangen
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Warteschlangen: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sla", response_model=Dict[str, Any])
async def get_sla_overview(
    service: DashboardService = Depends(get_dashboard_service)
) -> Dict[str, Any]:
    """
    SLA-Übersicht mit kritischen Fahrzeugen
    
    Returns:
        - Überfällige Prozesse
        - Kritische Prozesse
        - Warnungen
        - Statistiken
    """
    try:
        logger.info("📊 SLA-Overview wird abgerufen")
        sla_overview = await service.get_sla_overview()
        return sla_overview
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der SLA-Overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bearbeiter", response_model=List[Dict[str, Any]])
async def get_bearbeiter_workload(
    service: DashboardService = Depends(get_dashboard_service)
) -> List[Dict[str, Any]]:
    """
    Workload-Übersicht pro Bearbeiter
    
    Returns:
        Liste mit Bearbeiter-Statistiken und Auslastung
    """
    try:
        logger.info("📊 Bearbeiter-Workload wird abgerufen")
        workload = await service.get_bearbeiter_workload()
        return workload
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Bearbeiter-Workload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistik/{prozess_typ}", response_model=Dict[str, Any])
async def get_prozess_statistik(
    prozess_typ: str,
    service: DashboardService = Depends(get_dashboard_service)
) -> Dict[str, Any]:
    """
    Detaillierte Statistik für einen spezifischen Prozesstyp
    
    Args:
        prozess_typ: Name des Prozesses (z.B. "Aufbereitung")
        
    Returns:
        Prozess-spezifische Statistiken
    """
    try:
        logger.info(f"📊 Statistik für {prozess_typ} wird abgerufen")
        
        # Query für prozess-spezifische Statistiken
        query = f"""
        SELECT 
            COUNT(DISTINCT fin) as fahrzeuge_gesamt,
            COUNT(DISTINCT CASE WHEN status = 'abgeschlossen' THEN fin END) as abgeschlossen,
            COUNT(DISTINCT CASE WHEN status != 'abgeschlossen' THEN fin END) as aktiv,
            AVG(DATETIME_DIFF(ende_timestamp, start_timestamp, HOUR)) as avg_dauer_stunden,
            MIN(DATETIME_DIFF(ende_timestamp, start_timestamp, HOUR)) as min_dauer_stunden,
            MAX(DATETIME_DIFF(ende_timestamp, start_timestamp, HOUR)) as max_dauer_stunden,
            COUNT(DISTINCT bearbeiter) as bearbeiter_anzahl
        FROM fahrzeug_prozesse
        WHERE prozess_typ = @prozess_typ
        AND DATE(erstellt_am) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        """
        
        # Mock-Daten für Entwicklung
        statistik = {
            "prozess_typ": prozess_typ,
            "zeitraum": "letzte_30_tage",
            "fahrzeuge": {
                "gesamt": 45,
                "abgeschlossen": 32,
                "aktiv": 13
            },
            "durchlaufzeiten": {
                "avg_stunden": 48.5,
                "min_stunden": 12.0,
                "max_stunden": 120.0
            },
            "bearbeiter": 3,
            "erfolgsquote": 71.1  # (abgeschlossen / gesamt) * 100
        }
        
        return statistik
        
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Prozess-Statistik: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends", response_model=Dict[str, Any])
async def get_trends(
    tage: int = 30,
    service: DashboardService = Depends(get_dashboard_service)
) -> Dict[str, Any]:
    """
    Trend-Analyse über einen bestimmten Zeitraum
    
    Args:
        tage: Anzahl Tage für Trend-Analyse (Standard: 30)
        
    Returns:
        Trend-Daten für Visualisierung
    """
    try:
        logger.info(f"📊 Trends für {tage} Tage werden abgerufen")
        
        # Mock-Trend-Daten für Entwicklung
        trends = {
            "zeitraum_tage": tage,
            "fahrzeug_trend": {
                "neu_erfasst": [3, 5, 2, 4, 6, 3, 4],  # Pro Woche
                "verkauft": [2, 3, 4, 2, 5, 3, 3]
            },
            "prozess_trend": {
                "aufbereitung": [8, 10, 7, 9, 11, 8, 9],
                "werkstatt": [4, 3, 5, 4, 6, 5, 4],
                "foto": [3, 4, 3, 5, 4, 3, 4]
            },
            "sla_trend": {
                "eingehalten": [85, 88, 82, 90, 87, 89, 91],  # Prozent
                "überschritten": [15, 12, 18, 10, 13, 11, 9]
            }
        }
        
        return trends
        
    except Exception as e:
        logger.error(f"❌ Fehler beim Abrufen der Trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))