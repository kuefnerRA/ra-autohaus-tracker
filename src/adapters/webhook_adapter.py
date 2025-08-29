# src/adapters/webhook_adapter.py
import logging
from typing import Dict, Any

# Absolute Imports
from models.integration import WebhookInput, UnifiedProcessData

logger = logging.getLogger(__name__)


class WebhookAdapter:
    """Konvertiert Flowers-Webhook-Daten zu einheitlichem Format"""
    
    @staticmethod
    def convert_to_unified(webhook_data: Dict[str, Any]) -> UnifiedProcessData:
        """Webhook-Daten → UnifiedProcessData"""
        
        webhook_input = WebhookInput(**webhook_data)
        
        # FIN extrahieren/validieren
        fin = webhook_input.fin
        if not fin:
            # Versuche FIN aus fahrzeug_id zu extrahieren
            from handlers.flowers_handler import FlowersHandler
            fin = FlowersHandler.extract_fin_from_text(webhook_input.fahrzeug_id)
        
        if not fin:
            raise ValueError("FIN konnte nicht ermittelt werden")
        
        return UnifiedProcessData(
            fin=fin,
            prozess_typ=webhook_input.prozess,
            status=webhook_input.status,
            bearbeiter=webhook_input.bearbeiter,
            prioritaet=5,  # Default-Priorität für Webhooks
            datenquelle="webhook",
            external_timestamp=webhook_input.timestamp,
            zusatz_daten=webhook_input.zusatz_daten
        )