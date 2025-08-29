# src/routers/dashboard.py
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import logging
from datetime import datetime, timedelta

from services.bigquery_service import BigQueryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# BigQuery Service initialisieren
bq_service = BigQueryService()

@router.get("/kpis")
async def get_dashboard_kpis():
    """Dashboard KPIs für Looker Studio"""
    try:
        kpis = await bq_service.get_dashboard_kpis()
        return {
            "status": "success",
            "data": kpis,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"KPI-Abfrage fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/warteschlangen")
async def get_warteschlangen_status():
    """Status aller Warteschlangen"""
    try:
        warteschlangen = await bq_service.get_warteschlangen_overview()
        return {
            "status": "success",
            "warteschlangen": warteschlangen,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Warteschlangen-Abfrage fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sla-status")
async def get_sla_status():
    """SLA-Status für alle Prozesse"""
    try:
        sla_status = await bq_service.get_sla_violations()
        return {
            "status": "success", 
            "sla_violations": sla_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"SLA-Status-Abfrage fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prozess-overview")
async def get_prozess_overview():
    """Übersicht aller Prozesse mit Statistiken"""
    try:
        overview = await bq_service.get_process_statistics()
        return {
            "status": "success",
            "prozess_statistiken": overview,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Prozess-Overview fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bearbeiter-workload")
async def get_bearbeiter_workload():
    """Arbeitsauslastung pro Bearbeiter"""
    try:
        workload = await bq_service.get_bearbeiter_workload()
        return {
            "status": "success",
            "bearbeiter_workload": workload,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Bearbeiter-Workload-Abfrage fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))