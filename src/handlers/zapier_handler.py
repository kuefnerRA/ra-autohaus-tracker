"""
Zapier Handler für Webhook-Integration
Verarbeitet Daten von Zapier und leitet sie an UnifiedHandler weiter
"""

import logging
from typing import Dict, Any
from src.handlers.unified_handler import UnifiedHandler

logger = logging.getLogger(__name__)

class ZapierHandler:
    """Handler für Zapier-Webhooks"""
    
    def __init__(self, unified_handler: UnifiedHandler):
        self.unified = unified_handler
        logger.info("✅ ZapierHandler initialisiert")
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet Zapier-Webhook-Daten
        
        Args:
            payload: Zapier-Webhook-Payload
            
        Returns:
            Verarbeitungsergebnis
        """
        try:
            logger.info(f"🔗 Zapier-Webhook empfangen: {payload.get('fin', 'Unbekannt')}")
            
            # Zapier sendet manchmal verschachtelte Daten
            data = self._extract_zapier_data(payload)
            
            # Verarbeite über UnifiedHandler
            result = await self.unified.process_data(data, source="zapier")
            
            logger.info(f"✅ Zapier-Daten verarbeitet: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Zapier-Verarbeitung fehlgeschlagen: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "zapier"
            }
    
    def _extract_zapier_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extrahiert relevante Daten aus Zapier-Payload"""
        
        # Zapier kann Daten in verschiedenen Formaten senden
        if "data" in payload:
            return payload["data"]
        
        # Direkte Felder verwenden - angepasst an process_service.py Erwartungen
        return {
            "fin": payload.get("fin") or payload.get("fahrzeug_fin"),
            "prozess_typ": payload.get("prozess_typ") or payload.get("prozess_name"),  # prozess_name wird zu prozess_typ
            "status": payload.get("status") or payload.get("neuer_status"),
            "bearbeiter": payload.get("bearbeiter") or payload.get("bearbeiter_name"),
            "prioritaet": payload.get("prioritaet"),
            "notizen": payload.get("notizen"),
            "timestamp": payload.get("timestamp"),
            "trigger_type": payload.get("trigger_type"),
            "marke": payload.get("marke"),
            "modell": payload.get("modell")
        }