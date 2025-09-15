"""
Zapier Handler für Webhook-Integration
Verarbeitet Daten von Zapier und leitet sie an UnifiedHandler weiter
"""

import logging
import json
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
            logger.info(f"🔗 Zapier-Webhook empfangen - VOLLSTÄNDIGER PAYLOAD:")
            logger.info(json.dumps(payload, indent=2, ensure_ascii=False))
            
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

        logger.info(f"📥 Zapier Raw Payload: {json.dumps(payload, indent=2)}")
        
        # Alle Fahrzeugdaten extrahieren
        extracted_data = {
            # Basis
            "fin": payload.get("fin"),
            "prozess_typ": payload.get("prozess_typ") or payload.get("prozess_name"),
            "status": payload.get("status"),
            "bearbeiter": payload.get("bearbeiter"),
            
            # Fahrzeugstammdaten
            "marke": payload.get("marke"),
            "modell": payload.get("modell"),
            "antriebsart": payload.get("antriebsart"),
            "datum_erstzulassung": payload.get("datum_erstzulassung"),
            "farbe": payload.get("farbe"),  
            "baujahr": payload.get("baujahr"),  
            "ek_netto": payload.get("ek_netto"),
            "km_stand": payload.get("km_stand"),
            "kw_leistung": payload.get("kw_leistung"),
            "anzahl_fahrzeugschluessel": payload.get("anzahl_fahrzeugschluessel") or payload.get("anzahl_fahrzeugschlüssel"),  # Beide Varianten!
            "anzahl_vorhalter": payload.get("anzahl_vorhalter"),
            "bereifungsart": payload.get("bereifungsart"),
            "besteuerungsart": payload.get("besteuerungsart"),
        }
        
        # Debug: Extrahierte Daten loggen
        logger.info(f"📤 Extrahierte Daten: Marke={extracted_data.get('marke')}, Modell={extracted_data.get('modell')}")
        
        return extracted_data