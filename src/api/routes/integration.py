# src/api/routes/integration.py - KORRIGIERT für autohaus Dataset
"""Integration API Routes für Webhooks und externe Systeme"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Import für bereits vorhandene Services
try:
    from src.services.process_service import ProcessService
except ImportError:
    # Fallback wenn Services noch nicht existieren
    ProcessService = None

# BigQuery Client wird zur Laufzeit geholt
def get_bigquery_service():
    """BigQuery Service zur Laufzeit abrufen"""
    try:
        from src.core.dependencies import get_bigquery_service as get_bq_service
        return get_bq_service()
    except ImportError:
        return None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integration", tags=["Integration"])

# Pydantic Models für Request Validation
class ZapierWebhookData(BaseModel):
    fahrzeug_fin: Optional[str] = Field(None, description="Fahrzeug FIN")
    fin: Optional[str] = Field(None, description="Alternative FIN")
    prozess_name: Optional[str] = Field(None, description="Prozess Name")
    prozess: Optional[str] = Field(None, description="Alternative Prozess")
    neuer_status: Optional[str] = Field(None, description="Neuer Status")
    status: Optional[str] = Field(None, description="Alternative Status")
    bearbeiter_name: Optional[str] = Field(None, description="Bearbeiter Name")
    bearbeiter: Optional[str] = Field(None, description="Alternative Bearbeiter")
    notizen: Optional[str] = Field(None, description="Zusätzliche Notizen")

class FlowersEmailData(BaseModel):
    fin: str = Field(..., description="Fahrzeug FIN")
    prozess_typ: str = Field(..., description="Prozess Typ")
    status: str = Field(..., description="Status")
    bearbeiter: Optional[str] = Field(None, description="Bearbeiter")
    email_subject: Optional[str] = Field(None, description="E-Mail Betreff")
    timestamp: Optional[str] = Field(None, description="Zeitstempel")

# Prozess-Mapping (aus ursprünglicher main.py)
PROZESS_MAPPING = {
    "gwa": "Aufbereitung",
    "garage": "Werkstatt", 
    "photos": "Foto",
    "sales": "Verkauf",
    "purchase": "Einkauf",
    "delivery": "Anlieferung"
}

def normalize_prozess_typ(prozess: str) -> str:
    """Normalisiert Prozess-Typen aus verschiedenen Quellen"""
    if not prozess:
        return "Unbekannt"
    
    prozess_lower = prozess.lower().strip()
    return PROZESS_MAPPING.get(prozess_lower, prozess.title())

async def save_to_bigquery(data: Dict[str, Any], source: str) -> bool:
    """Speichert Daten in BigQuery - KORRIGIERT für autohaus Dataset"""
    try:
        bq_service = get_bigquery_service()
        if not bq_service:
            logger.warning("BigQuery Service nicht verfügbar")
            return False
        bq_client = bq_service.client
        
        # Event-Daten für BigQuery vorbereiten
        event_data = {
            "fin": data.get("fin"),
            "prozess_typ": data.get("prozess_typ"),
            "status": data.get("status"),
            "bearbeiter": data.get("bearbeiter"),
            "datenquelle": source,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "zusatz_daten": data.get("zusatz_daten", {})
        }
        
        # In BigQuery einfügen - KORRIGIERT für autohaus Dataset
        table_ref = bq_client.dataset("autohaus").table("fahrzeug_prozesse")
        table = bq_client.get_table(table_ref)
        
        errors = bq_client.insert_rows_json(table, [event_data])
        
        if errors:
            logger.error(f"BigQuery Insert Fehler: {errors}")
            return False
            
        logger.info(f"Daten erfolgreich in BigQuery gespeichert: {data.get('fin')}")
        return True
        
    except Exception as e:
        logger.error(f"BigQuery Speichern Fehler: {e}")
        return False

# ================================
# ZAPIER INTEGRATION ENDPOINTS
# ================================

@router.post("/zapier/webhook")
async def zapier_webhook(
    data: ZapierWebhookData,
    background_tasks: BackgroundTasks
):
    """
    Zapier Webhook Endpoint mit Pydantic Validation
    """
    try:
        # FIN extrahieren
        fin = data.fahrzeug_fin or data.fin
        if not fin:
            raise HTTPException(status_code=400, detail="FIN ist erforderlich")
        
        # Prozess extrahieren und normalisieren
        prozess_raw = data.prozess_name or data.prozess
        if not prozess_raw:
            raise HTTPException(status_code=400, detail="Prozess ist erforderlich")
        
        prozess = normalize_prozess_typ(prozess_raw)
        
        # Status extrahieren
        status = data.neuer_status or data.status
        if not status:
            raise HTTPException(status_code=400, detail="Status ist erforderlich")
        
        # Bearbeiter extrahieren
        bearbeiter = data.bearbeiter_name or data.bearbeiter or "System"
        
        # Daten strukturieren
        event_data = {
            "fin": fin,
            "prozess_typ": prozess,
            "status": status,
            "bearbeiter": bearbeiter,
            "zusatz_daten": {
                "ursprung_prozess": prozess_raw,
                "notizen": data.notizen,
                "zapier_data": data.dict()
            }
        }
        
        # In Background Task speichern
        background_tasks.add_task(save_to_bigquery, event_data, "zapier_webhook")
        
        logger.info(f"Zapier Webhook verarbeitet: {fin} -> {prozess} -> {status}")
        
        return {
            "status": "success",
            "message": "Daten erfolgreich verarbeitet",
            "fin": fin,
            "prozess_typ": prozess,
            "status": status,
            "bearbeiter": bearbeiter,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Zapier Webhook Fehler: {e}")
        raise HTTPException(status_code=500, detail=f"Verarbeitungsfehler: {str(e)}")

@router.post("/zapier/flexible")
async def zapier_flexible_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Flexibler Zapier Webhook der jedes JSON akzeptiert (Legacy Support)
    """
    try:
        json_data = await request.json()
        logger.info(f"Flexible Zapier Webhook: {json_data}")
        
        # FIN extrahieren (verschiedene mögliche Feldnamen)
        fin = (json_data.get('fahrzeug_fin') or 
               json_data.get('fin') or 
               json_data.get('vehicle_fin') or 
               json_data.get('FIN'))
        
        # Prozess extrahieren
        prozess_raw = (json_data.get('prozess_name') or 
                      json_data.get('prozess') or 
                      json_data.get('process_name'))
        
        # Status extrahieren  
        status = (json_data.get('neuer_status') or 
                 json_data.get('status') or 
                 json_data.get('new_status'))
        
        if not fin or not prozess_raw or not status:
            return {
                "status": "error",
                "message": "Required fields missing (fin, prozess, status)",
                "received_fields": list(json_data.keys()),
                "expected_fields": ["fin/fahrzeug_fin", "prozess/prozess_name", "status/neuer_status"]
            }
        
        # Normalisierte Verarbeitung
        prozess = normalize_prozess_typ(prozess_raw)
        bearbeiter = (json_data.get('bearbeiter_name') or 
                     json_data.get('bearbeiter') or 
                     "System")
        
        # Daten strukturieren
        event_data = {
            "fin": fin,
            "prozess_typ": prozess,
            "status": status,
            "bearbeiter": bearbeiter,
            "zusatz_daten": {
                "ursprung_prozess": prozess_raw,
                "raw_zapier_data": json_data
            }
        }
        
        # In Background Task speichern
        background_tasks.add_task(save_to_bigquery, event_data, "zapier_flexible")
        
        logger.info(f"Flexible Zapier Webhook verarbeitet: {fin} -> {prozess} -> {status}")
        
        return {
            "status": "success",
            "fin": fin,
            "prozess_typ": prozess,
            "status": status,
            "bearbeiter": bearbeiter,
            "message": "Daten erfolgreich über flexible API verarbeitet"
        }
        
    except Exception as e:
        logger.error(f"Flexible Zapier Webhook Fehler: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "hint": "Prüfen Sie das JSON-Format und erforderliche Felder"
        }

# ================================
# DEBUG & HEALTH ENDPOINTS
# ================================

@router.get("/debug/mappings")
async def get_debug_mappings():
    """
    Debug-Endpoint für Prozess-Mappings
    """
    return {
        "prozess_mapping": PROZESS_MAPPING,
        "supported_sources": ["zapier_webhook", "zapier_flexible", "flowers_email", "flowers_direct"],
        "bigquery_config": {
            "dataset": "autohaus",
            "table": "fahrzeug_prozesse"
        },
        "example_zapier_data": {
            "fahrzeug_fin": "WAUEXAMPLE123456",
            "prozess_name": "gwa",
            "neuer_status": "abgeschlossen",
            "bearbeiter_name": "Thomas K."
        }
    }

@router.get("/health")
async def integration_health():
    """
    Integration Service Gesundheitscheck - Ohne BigQuery Dependency
    """
    return {
        "service": "IntegrationService",
        "status": "healthy",
        "bigquery_verfügbar": get_bigquery_client() is not None,
        "endpoints": {
            "zapier": [
                "/integration/zapier/webhook",
                "/integration/zapier/flexible"
            ],
            "flowers": [
                "/integration/email/webhook",
                "/integration/flowers/webhook"
            ],
            "debug": [
                "/integration/debug/mappings",
                "/integration/health"
            ]
        },
        "prozess_mappings": len(PROZESS_MAPPING),
        "version": "2.0.0"
    }

# Legacy Support für bestehende URLs
@router.post("/webhooks/zapier")
async def legacy_zapier_webhook(request: Request, background_tasks: BackgroundTasks):
    """Legacy Support - Weiterleitung zum neuen Endpoint"""
    logger.warning("Legacy /integration/webhooks/zapier verwendet - bitte auf /integration/zapier/webhook umsteigen")
    return await zapier_flexible_webhook(request, background_tasks)