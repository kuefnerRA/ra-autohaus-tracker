# src/routers/vehicles.py
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fahrzeuge", tags=["Fahrzeuge"])

# Placeholder - wird später aus main.py extrahiert
@router.get("/")
async def list_fahrzeuge():
    return {"message": "Fahrzeuge-Router - wird aus main.py migriert"}

@router.get("/{fin}")
async def get_fahrzeug(fin: str):
    return {"message": f"Fahrzeug {fin} - wird aus main.py migriert"}