"""
Flowers Handler für Email-Integration
Verarbeitet Emails von Flowers und extrahiert strukturierte Daten
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime
from src.handlers.unified_handler import UnifiedHandler

logger = logging.getLogger(__name__)

class FlowersHandler:
    """Handler für Flowers Email-Integration"""
    
    def __init__(self, unified_handler: UnifiedHandler):
        self.unified = unified_handler
        logger.info("✅ FlowersHandler initialisiert")
    
    async def process_email(self, email_content: str, subject: str = "") -> Dict[str, Any]:
        """
        Verarbeitet Flowers-Email und extrahiert Daten
        
        Args:
            email_content: Email-Body
            subject: Email-Betreff
            
        Returns:
            Verarbeitungsergebnis
        """
        try:
            logger.info(f"📧 Flowers-Email empfangen: {subject}")
            
            # Extrahiere Daten aus Email
            data = self._parse_email_content(email_content, subject)
            
            if not data.get("fin"):
                logger.warning("⚠️ Keine FIN in Email gefunden")
                return {"success": False, "error": "Keine FIN gefunden"}
            
            # Verarbeite über UnifiedHandler
            result = await self.unified.process_data(data, source="flowers_email")
            
            logger.info(f"✅ Flowers-Email verarbeitet: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Flowers-Email-Verarbeitung fehlgeschlagen: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "flowers_email"
            }
    
    def _parse_email_content(self, content: str, subject: str) -> Dict[str, Any]:
        """Extrahiert strukturierte Daten aus Email-Text"""
        
        data = {}
        
        # FIN extrahieren (17 Zeichen, alphanumerisch)
        fin_match = re.search(r'\b([A-Z0-9]{17})\b', content)
        if fin_match:
            data["fin"] = fin_match.group(1)
        
        # Prozess aus Betreff extrahieren
        if "aufbereitung" in subject.lower():
            data["prozess_typ"] = "Aufbereitung"
        elif "werkstatt" in subject.lower():
            data["prozess_typ"] = "Werkstatt"
        
        # Status extrahieren
        if "abgeschlossen" in content.lower():
            data["status"] = "abgeschlossen"
        elif "gestartet" in content.lower():
            data["status"] = "in_bearbeitung"
        
        return data