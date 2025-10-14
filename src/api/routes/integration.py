"""
Integration API Endpoints
Webhooks für Zapier, Flowers und direkte API-Calls
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request
from google.cloud import bigquery

import logging

from src.core.dependencies import (
    get_unified_handler, 
    get_zapier_handler, 
    get_flowers_handler
)
from src.handlers.unified_handler import UnifiedHandler
from src.handlers.zapier_handler import ZapierHandler
from src.handlers.flowers_handler import FlowersHandler
from src.models.integration import ZapierWebhookIn

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Integration"])

bq = bigquery.Client()
BQ_TABLE = "ra-autohaus-tracker.autohaus.fahrzeug_prozesse"

# Handler-Instanzen (werden bei ersten Request initialisiert)
_unified_handler = None
_zapier_handler = None
_flowers_handler = None

@router.post("/zapier/webhook")
async def zapier_webhook(request: Request):
    body: Dict[str, Any] = await request.json()

    # --- Pflichtfelder/Standardisierung ---
    fin = body.get("fin") or body.get("fahrzeug_fin")
    prozess_raw = body.get("prozess_name") or body.get("prozess") or "Unbekannt"
    status = body.get("neuer_status") or body.get("status") or "UNBEKANNT"
    bearbeiter = body.get("bearbeiter_name") or body.get("bearbeiter") or "System"

    # --- prioritaet robust konvertieren (String/Number) + Bounds 1..5 ---
    prio_raw = body.get("prioritaet") or body.get("priorität") or body.get("prio") or body.get("priority")
    try:
        prio_val = int(prio_raw) if prio_raw is not None else 5
    except Exception:
        prio_val = 5
    if prio_val < 1 or prio_val > 5:
        prio_val = 5

    # --- notizen normalisieren ---
    notizen_val = body.get("notizen") or body.get("notiz") or body.get("notes") or ""
    if isinstance(notizen_val, str):
        notizen_val = notizen_val.strip()
    else:
        notizen_val = ""

    # --- Insert-Payload (Top-Level Felder enthalten prioritaet/notizen!) ---
    created_utc = datetime.now(timezone.utc).replace(tzinfo=None)  # BigQuery TIMESTAMP (naiv, UTC)
    event_data = {
        "fin": fin,
        "prozess_typ": prozess_raw,
        "status": status,
        "bearbeiter": bearbeiter,
        "prioritaet": prio_val,     # <--- NEU: Top-Level
        "notizen": notizen_val,     # <--- NEU: Top-Level
        "datenquelle": "zapier",
        "created_at": created_utc,
        "updated_at": created_utc,
        "zusatz_daten": {
            "zapier_data": body,            # Rohdaten weiter behalten
            "ursprung_prozess": prozess_raw,
            "notizen": body.get("notizen"), # optional zusätzlich in Zusatzdaten
        },
    }

    # --- BigQuery Insert ---
    errors = bq.insert_rows_json(BQ_TABLE, [event_data])
    if errors:
        # Für Cloud Run Logs
        print("BigQuery insert errors:", errors)
        return {"success": False, "error": "bq_insert_failed"}

    return {
        "success": True,
        "fin": fin,
        "prioritaet": prio_val,
        "notizen": notizen_val,
        "source": "zapier",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    
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
    


from pydantic import BaseModel, Field, constr
Vin = constr(pattern=r'^[A-HJ-NPR-Z0-9]{17}$')

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
     prioritaet: Optional[int | str] = Field(None, description="Priorität 1..5 (Zahl oder String)")
