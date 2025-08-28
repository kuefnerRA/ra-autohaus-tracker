from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prozesse", tags=["Prozesse"])

# Placeholder - wird später aus main.py extrahiert
@router.get("/")
async def list_prozesse():
    return {"message": "Prozesse-Router - wird aus main.py migriert"}

@router.post("/start")
async def start_prozess():
    return {"message": "Prozess starten - wird aus main.py migriert"}