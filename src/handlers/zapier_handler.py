"""
Zapier Handler für Webhook-Integration
Verarbeitet Daten von Zapier und leitet sie an UnifiedHandler weiter
"""

import logging
import json
from typing import Dict, Any
from src.handlers.unified_handler import UnifiedHandler
from src.handlers.data_transformer import DataTransformer  # NEU

logger = logging.getLogger(__name__)

class ZapierHandler:
    """Handler für Zapier-Webhooks"""
    
    def __init__(self, unified_handler: UnifiedHandler):
        self.unified = unified_handler
        self.transformer = DataTransformer()
        self.logger = logger  # Wichtig für Pylance
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
            logger.info(f"🔍 FIN: {payload.get('fin')}")
            logger.info(f"🔍 Prozess: {payload.get('prozess_name')} / {payload.get('prozess_typ')}")
            logger.info(f"🔍 Status: {payload.get('status')} / {payload.get('neuer_status')}")
            logger.info(f"🔍 Marke: {payload.get('marke')}")
            logger.info(f"🔍 Modell: {payload.get('modell')}")
            logger.info(f"  - EK Netto: {payload.get('ek_netto')} EUR")
            logger.info(f"  - Bearbeiter: {payload.get('bearbeiter', 'FEHLT!')}")
            
            # Extrahiere Rohdaten
            raw_data = self._extract_zapier_data(payload)
            
            # TRANSFORMIERE Daten vor Verarbeitung
            transformed_data = self.transformer.transform_zapier_data(raw_data)
            
            logger.info(f"📊 Transformierte Daten: {json.dumps({k: str(v) for k, v in transformed_data.items()}, indent=2)}")
            
            # Verarbeite über UnifiedHandler mit transformierten Daten
            result = await self.unified.process_data(transformed_data, source="zapier")
            
            logger.info(f"✅ Zapier-Daten verarbeitet: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Zapier-Verarbeitung fehlgeschlagen: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "source": "zapier"
            }
    
    def _extract_zapier_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extrahiert relevante Daten aus Zapier-Payload"""

        logger.info(f"📥 Zapier Raw Payload: {json.dumps(payload, indent=2)}")
        
        # Alle Fahrzeugdaten extrahieren - OHNE Transformation!
        extracted_data = {
            # Basis - BEIDE Varianten durchreichen
            "fin": payload.get("fahrzeug_fin") or payload.get("fin"),
            "prozess_typ": payload.get("prozess_typ"),
            "prozess_name": payload.get("prozess_name"),  # NEU: Originalname beibehalten
            "status": payload.get("status"),
            "neuer_status": payload.get("neuer_status"),  # NEU: Auch neuer_status durchreichen
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
            "anzahl_fahrzeugschluessel": payload.get("anzahl_fahrzeugschluessel") or payload.get("anzahl_fahrzeugschlüssel"),
            "anzahl_vorhalter": payload.get("anzahl_vorhalter"),
            "bereifungsart": payload.get("bereifungsart"),
            "besteuerungsart": payload.get("besteuerungsart"),
        }
        
        # Debug: Extrahierte Daten loggen
        logger.info(f"📤 Extrahierte Daten: Marke={extracted_data.get('marke')}, Modell={extracted_data.get('modell')}")
        
        return extracted_data