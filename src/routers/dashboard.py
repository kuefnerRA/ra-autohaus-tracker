# src/routers/dashboard.py
from fastapi import APIRouter  
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Placeholder - wird später aus main.py extrahiert
@router.get("/kpis")
async def get_dashboard_kpis():
    return {"message": "Dashboard KPIs - wird aus main.py migriert"}

@router.get("/warteschlangen")
async def get_warteschlangen():
    return {"message": "Warteschlangen - wird aus main.py migriert"}