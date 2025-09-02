# src/api/routes/dashboard.py
"""Dashboard API Routes"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

from src.services.dashboard_service import DashboardService
from src.core.dependencies import get_dashboard_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/kpis")
async def get_kpis(
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Haupt-KPIs für das Dashboard abrufen
    """
    try:
        return await dashboard_service.get_kpis()
    except Exception as e:
        logger.error(f"KPI Abruf Fehler: {e}")
        raise HTTPException(status_code=500, detail="KPIs konnten nicht abgerufen werden")

@router.get("/warteschlangen")
async def get_warteschlangen(
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Warteschlangen-Status für alle Prozesse
    """
    try:
        return await dashboard_service.get_warteschlangen()
    except Exception as e:
        logger.error(f"Warteschlangen Abruf Fehler: {e}")
        raise HTTPException(status_code=500, detail="Warteschlangen konnten nicht abgerufen werden")

@router.get("/health")
async def dashboard_health():
    """Dashboard Service Gesundheitscheck"""
    return {
        "service": "DashboardService",
        "status": "healthy",
        "endpoints": ["/dashboard/kpis", "/dashboard/warteschlangen"]
    }