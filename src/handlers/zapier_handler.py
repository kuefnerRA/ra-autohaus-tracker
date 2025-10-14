"""
Zapier Handler für Webhook-Integration
Verarbeitet Daten von Zapier und leitet sie an UnifiedHandler weiter
"""

import logging
import json
from typing import Dict, Any, Optional
from src.handlers.unified_handler import UnifiedHandler
from src.handlers.data_transformer import DataTransformer

from models.integration import ZapierWebhookIn

logger = logging.getLogger(__name__)

class ZapierHandler:
    """Handler für Zapier-Webhooks"""
    
    def __init__(self, unified_handler: UnifiedHandler):
        self.unified = unified_handler
        self.transformer = DataTransformer()
        self.logger = logger
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
            logger.info(f"  - Bearbeiter: {payload.get('bearbeiter_name', payload.get('bearbeiter', 'FEHLT!'))}")
            logger.info(f"  - Priorität: {payload.get('prioritaet', 'FEHLT!')}")
            logger.info(f"  - Notizen: {payload.get('notizen', 'LEER')}")
            
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
        """
        Extrahiert relevante Daten aus Zapier-Payload
        
        WICHTIG: Diese Methode extrahiert ALLE relevanten Felder aus dem Payload,
        inkl. bearbeiter_name, prioritaet, notizen und zusatz_daten
        """
        logger.info(f"📥 Zapier Raw Payload Keys: {list(payload.keys())}")
        
        # Alle Fahrzeugdaten extrahieren - OHNE Transformation!
        extracted_data = {
            # === BASIS-FELDER ===
            "fin": payload.get("fahrzeug_fin") or payload.get("fin"),
            "prozess_typ": payload.get("prozess_typ"),
            "prozess_name": payload.get("prozess_name"),
            "status": payload.get("status"),
            "neuer_status": payload.get("neuer_status"),
            
            # === KRITISCHE PROZESS-FELDER (vorher fehlten diese!) ===
            "bearbeiter": payload.get("bearbeiter"),
            "bearbeiter_name": payload.get("bearbeiter_name"),  # NEU: Zapier sendet oft bearbeiter_name statt bearbeiter
            "prioritaet": payload.get("prioritaet"),  # NEU: Wurde nicht extrahiert!
            "notizen": payload.get("notizen"),  # NEU: Wurde nicht extrahiert!
            
            # === FAHRZEUGSTAMMDATEN ===
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
            
            # === PROZESS-ZEITSTEMPEL ===
            "start_timestamp": payload.get("start_timestamp"),
            "ende_timestamp": payload.get("ende_timestamp"),
            "anlieferung_datum": payload.get("anlieferung_datum"),
            "sla_tage": payload.get("sla_tage"),
            "individuelle_deadline": payload.get("individuelle_deadline"),
            
            # === ZUSATZDATEN (können aus verschiedenen Quellen kommen) ===
            "zusatz_daten": payload.get("zusatz_daten") or self._extract_zusatz_daten(payload),
        }
        
        # Debug: Extrahierte kritische Felder loggen
        logger.info(f"📤 Extrahierte kritische Felder:")
        logger.info(f"  - Bearbeiter: {extracted_data.get('bearbeiter')} / bearbeiter_name: {extracted_data.get('bearbeiter_name')}")
        logger.info(f"  - Priorität: {extracted_data.get('prioritaet')}")
        logger.info(f"  - Notizen: {extracted_data.get('notizen')}")
        logger.info(f"  - Zusatzdaten: {extracted_data.get('zusatz_daten')}")
        logger.info(f"  - Marke={extracted_data.get('marke')}, Modell={extracted_data.get('modell')}")
        
        return extracted_data
    
    def _extract_zusatz_daten(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extrahiert zusätzliche Daten, die nicht in den Hauptfeldern sind
        
        Falls Zapier die Fahrzeugdaten in einem separaten 'zusatz_daten' Objekt sendet,
        oder falls bestimmte Felder zusätzlich gespeichert werden sollen
        """
        zusatz = {}
        
        # Falls es bereits ein zusatz_daten Objekt gibt, verwenden
        if "zusatz_daten" in payload and isinstance(payload["zusatz_daten"], dict):
            return payload["zusatz_daten"]
        
        # Alternativ: Spezielle Felder, die als Zusatzdaten gespeichert werden sollen
        zusatz_felder = [
            "kommentar", "interne_notiz", "kundenhinweis", 
            "sonderausstattung", "schaeden", "maengel"
        ]
        
        for feld in zusatz_felder:
            if feld in payload and payload[feld]:
                zusatz[feld] = payload[feld]
        
        return zusatz if zusatz else None