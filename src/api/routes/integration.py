"""
Integration API Endpoints
Webhooks für Zapier, Flowers und direkte API-Calls
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any
import logging

from src.core.dependencies import (
    get_unified_handler, 
    get_zapier_handler, 
    get_flowers_handler
)
from src.handlers.unified_handler import UnifiedHandler
from src.handlers.zapier_handler import ZapierHandler
from src.handlers.flowers_handler import FlowersHandler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integration", tags=["Integration"])

# Handler-Instanzen (werden bei ersten Request initialisiert)
_unified_handler = None
_zapier_handler = None
_flowers_handler = None

@router.post("/zapier/webhook")
async def zapier_webhook(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    handler: ZapierHandler = Depends(get_zapier_handler)  # Nutzt jetzt dependencies.py
) -> Dict[str, Any]:
    """
    Zapier Webhook Endpoint
    
    Empfängt Daten von Zapier und verarbeitet sie asynchron
    """
    try:
        logger.info(f"🔗 Zapier-Webhook empfangen")
        result = await handler.process_webhook(payload)
        return result
    except Exception as e:
        logger.error(f"❌ Zapier-Webhook-Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/flowers/email")
async def flowers_email_webhook(
    email_data: Dict[str, Any],
    handler: FlowersHandler = Depends(get_flowers_handler)  # Nutzt jetzt dependencies.py
) -> Dict[str, Any]:
    """
    Flowers Email Webhook Endpoint
    
    Empfängt Email-Daten von Flowers
    """
    try:
        logger.info(f"📧 Flowers-Email-Webhook empfangen")
        
        content = email_data.get("body", email_data.get("content", ""))
        subject = email_data.get("subject", "")
        
        result = await handler.process_email(content, subject)
        return result
    except Exception as e:
        logger.error(f"❌ Flowers-Email-Webhook-Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))