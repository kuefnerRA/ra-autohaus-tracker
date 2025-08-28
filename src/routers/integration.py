# src/routers/integration.py
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException

# Korrekte absolute Imports für Router
from src.services.process_service import ProcessService
from src.adapters.zapier_adapter import ZapierAdapter  
from src.adapters.email_adapter import EmailAdapter
from src.adapters.webhook_adapter import WebhookAdapter
from src.models.integration import EmailInput, WebhookInput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integration", tags=["Integration"])

# Services (werden von main.py injiziert)
process_service: Optional[ProcessService] = None

def init_router(bq_client):
    """Router mit Abhängigkeiten initialisieren"""
    global process_service
    process_service = ProcessService(bq_client)

def get_process_service() -> ProcessService:
    """ProcessService holen mit Fehlerbehandlung"""
    if process_service is None:
        raise HTTPException(
            status_code=500, 
            detail="ProcessService not initialized. Router not properly configured."
        )
    return process_service

@router.post("/zapier/flexible")
async def zapier_flexible_legacy(request: Request, background_tasks: BackgroundTasks):
    """KRITISCH: Legacy-Endpoint für bestehende Zapier-Zaps"""
    if process_service is None:
        raise HTTPException(status_code=500, detail="ProcessService not initialized")
    
    try:
        json_data = await request.json()
        logger.info(f"LEGACY flexible endpoint: {list(json_data.keys())}")
        
        # 1. Flexible Feldextraktion (wie alte main.py)
        fin = (json_data.get('fin') or 
               json_data.get('fahrzeug_fin') or 
               json_data.get('vehicle_fin') or 
               json_data.get('FIN'))
        
        prozess_typ = (json_data.get('prozess_typ') or 
                      json_data.get('prozess_name') or 
                      json_data.get('prozess') or 
                      json_data.get('process_name'))
        
        status = (json_data.get('status') or 
                 json_data.get('neuer_status') or 
                 json_data.get('new_status'))
        
        if not fin or not prozess_typ or not status:
            missing = []
            if not fin: missing.append("fin")
            if not prozess_typ: missing.append("prozess_typ")
            if not status: missing.append("status")
            
            return {
                "status": "error",
                "message": "Required fields missing",
                "missing_fields": missing,
                "received_fields": list(json_data.keys())
            }
        
        # 2. Adapter verwenden (saubere Architektur beibehalten)
        adapter = ZapierAdapter()
        unified_data = adapter.convert_to_unified(json_data)
        
        # 3. Zentrale Verarbeitung (GLEICHE Logik wie neuer Endpoint)
        result = await process_service.process_unified_data(unified_data)
        
        # 4. Legacy-Format Antwort (für Kompatibilität)
        return {
            "status": "success" if result.success else "error",
            "fin": result.fin,
            "prozess": result.prozess_typ,
            "status": result.status,
            "prozess_id": result.prozess_id,
            "vehicle_created": result.vehicle_created,
            "bearbeiter_mapped": result.bearbeiter_mapped,
            "note": "LEGACY ENDPOINT - bitte auf /zapier/webhook umstellen"
        }
        
    except ValueError as e:
        logger.error(f"Legacy flexible validation error: {e}")
        return {"status": "error", "message": str(e), "source": "legacy"}
    except Exception as e:
        logger.error(f"Legacy flexible error: {e}")
        return {"status": "error", "message": str(e), "source": "legacy"}


@router.post("/zapier/webhook")
async def zapier_unified_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    EINHEITLICHER Zapier-Endpoint - verwendet zentrale Verarbeitungslogik
    Ersetzt sowohl den alten /zapier/webhook als auch /zapier/flexible
    """
    try:
        json_data = await request.json()
        logger.info(f"Zapier Webhook received: {list(json_data.keys())}")
        
        # 1. Zapier-Daten konvertieren
        adapter = ZapierAdapter()
        unified_data = adapter.convert_to_unified(json_data)
        
        # 2. Zentrale Verarbeitung (GLEICH für alle Quellen!)
        result = await get_process_service().process_unified_data(unified_data)
        
        # 3. Standardisierte Antwort
        return {
            "status": "success" if result.success else "error",
            "message": result.message,
            "fin": result.fin,
            "prozess": result.prozess_typ,
            "status_value": result.status,
            "prozess_id": result.prozess_id,
            "vehicle_created": result.vehicle_created,
            "bearbeiter_mapped": result.bearbeiter_mapped,
            "warnings": result.warnings,
            "source": "zapier"
        }
        
    except ValueError as e:
        logger.error(f"Zapier validation error: {e}")
        return {"status": "error", "message": str(e), "source": "zapier"}
    except Exception as e:
        logger.error(f"Zapier webhook error: {e}")
        return {"status": "error", "message": str(e), "source": "zapier"}


@router.post("/email/webhook")
async def email_unified_webhook(email_data: EmailInput, background_tasks: BackgroundTasks):
    """
    EINHEITLICHER E-Mail-Endpoint - verwendet zentrale Verarbeitungslogik
    """
    try:
        logger.info(f"Email webhook: {email_data.betreff}")
        
        # 1. E-Mail-Daten konvertieren
        adapter = EmailAdapter()
        unified_data = adapter.convert_to_unified(email_data.dict())
        
        # 2. Zentrale Verarbeitung (GLEICH für alle Quellen!)
        result = await get_process_service().process_unified_data(unified_data)
        
        # 3. Standardisierte Antwort
        return {
            "status": "success" if result.success else "error", 
            "message": result.message,
            "fin": result.fin,
            "prozess": result.prozess_typ,
            "status_value": result.status,
            "prozess_id": result.prozess_id,
            "vehicle_created": result.vehicle_created,
            "bearbeiter_mapped": result.bearbeiter_mapped,
            "warnings": result.warnings,
            "source": "email"
        }
        
    except ValueError as e:
        logger.error(f"Email validation error: {e}")
        return {"status": "error", "message": str(e), "source": "email"}
    except Exception as e:
        logger.error(f"Email webhook error: {e}")
        return {"status": "error", "message": str(e), "source": "email"}


@router.post("/flowers/webhook") 
async def flowers_unified_webhook(webhook_data: WebhookInput, background_tasks: BackgroundTasks):
    """
    EINHEITLICHER Flowers-Webhook - verwendet zentrale Verarbeitungslogik
    """
    try:
        logger.info(f"Flowers webhook: {webhook_data.prozess} für {webhook_data.fahrzeug_id}")
        
        # 1. Webhook-Daten konvertieren
        adapter = WebhookAdapter()
        unified_data = adapter.convert_to_unified(webhook_data.dict())
        
        # 2. Zentrale Verarbeitung (GLEICH für alle Quellen!)
        result = await get_process_service().process_unified_data(unified_data)
        
        # 3. Standardisierte Antwort
        return {
            "status": "success" if result.success else "error",
            "message": result.message, 
            "fin": result.fin,
            "prozess": result.prozess_typ,
            "status_value": result.status,
            "prozess_id": result.prozess_id,
            "vehicle_created": result.vehicle_created,
            "bearbeiter_mapped": result.bearbeiter_mapped,
            "warnings": result.warnings,
            "source": "flowers_webhook"
        }
        
    except ValueError as e:
        logger.error(f"Flowers webhook validation error: {e}")
        return {"status": "error", "message": str(e), "source": "flowers_webhook"}
    except Exception as e:
        logger.error(f"Flowers webhook error: {e}")
        return {"status": "error", "message": str(e), "source": "flowers_webhook"}


@router.post("/debug/test-all-sources")
async def test_all_sources():
    """Test-Endpoint um zu zeigen, dass alle Quellen identisch verarbeitet werden"""
    
    # Test-Daten für alle drei Quellen (gültige 17-stellige FIN)
    test_fin = "WVWZZZ1JZ3WTEST01"
    
    test_results = []
    
    # 1. Zapier-Test
    try:
        zapier_data = {
            "fin": test_fin,
            "prozess_typ": "Einkauf", 
            "status": "gestartet",
            "bearbeiter": "Thomas K.",
            "marke": "VW",
            "farbe": "Schwarz"
        }
        adapter = ZapierAdapter()
        unified = adapter.convert_to_unified(zapier_data)
        result = await get_process_service().process_unified_data(unified)
        test_results.append({"source": "zapier", "result": result.dict()})
    except Exception as e:
        test_results.append({"source": "zapier", "error": str(e)})
    
    # 2. E-Mail-Test  
    try:
        email_data = {
            "betreff": "Einkauf gestartet",
            "inhalt": f"FIN: {test_fin}\nMarke: VW\nBearbeiter: Thomas K.",
            "absender": "flowers@system.de",
            "empfangen_am": datetime.now()
        }
        adapter = EmailAdapter()
        unified = adapter.convert_to_unified(email_data)
        result = await get_process_service().process_unified_data(unified)
        test_results.append({"source": "email", "result": result.dict()})
    except Exception as e:
        test_results.append({"source": "email", "error": str(e)})
        
    # 3. Webhook-Test
    try:
        webhook_data = {
            "fahrzeug_id": test_fin,
            "fin": test_fin,
            "prozess": "Einkauf",
            "status": "gestartet", 
            "bearbeiter": "Thomas K."
        }
        adapter = WebhookAdapter()
        unified = adapter.convert_to_unified(webhook_data)
        result = await get_process_service().process_unified_data(unified)
        test_results.append({"source": "webhook", "result": result.dict()})
    except Exception as e:
        test_results.append({"source": "webhook", "error": str(e)})
    
    return {
        "message": "Test aller drei Integrationsquellen",
        "test_fin": test_fin,
        "results": test_results,
        "consistency_check": "Alle Quellen verwenden ProcessService.process_unified_data()"
    }