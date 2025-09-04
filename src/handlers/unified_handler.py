"""
Unified Handler für einheitliche Datenverarbeitung
Zentrale Verarbeitung für alle Datenquellen (Zapier, Flowers, Direct)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from src.services.process_service import ProcessService
from src.services.vehicle_service import VehicleService
from src.services.process_service import ProcessingSource

logger = logging.getLogger(__name__)

class UnifiedHandler:
    """Zentrale Datenverarbeitung für alle Quellen"""
    
    # Prozess-Mapping für verschiedene Schreibweisen
    PROZESS_MAPPING = {
        "gwa": "Aufbereitung",
        "garage": "Werkstatt",
        "photos": "Foto",
        "sales": "Verkauf",
        "purchase": "Einkauf",
        "delivery": "Anlieferung"
    }
    
    # Bearbeiter-Mapping
    BEARBEITER_MAPPING = {
        "Thomas K.": "Thomas Küfner",
        "Max R.": "Maximilian Reinhardt",
        "Thomas": "Thomas Küfner",
        "Max": "Maximilian Reinhardt"
    }
    
    def __init__(self, process_service: ProcessService, vehicle_service: VehicleService):
        self.process_service = process_service
        self.vehicle_service = vehicle_service
        logger.info("✅ UnifiedHandler initialisiert")

    async def process_data(self, data: Dict[str, Any], source: str = "unknown") -> Dict[str, Any]:
        """
        Verarbeitet Daten aus beliebiger Quelle einheitlich
        
        Args:
            data: Eingangsdaten
            source: Quelle (zapier, email, direct)
            
        Returns:
            Verarbeitungsergebnis
        """
        try:
            logger.info(f"📥 Verarbeite Daten von {source}: {data.get('fin', 'Unbekannt')}")
            
            # Normalisiere Daten
            normalized = self._normalize_data(data)
            
            # Erstelle oder aktualisiere Fahrzeug
            if normalized.get("fin"):
                vehicle = await self._ensure_vehicle_exists(normalized)
                
                # Erstelle Prozess wenn Status vorhanden
                if normalized.get("status"):
                    process = await self._create_or_update_process(normalized)
                    
            return {
                "success": True,
                "fin": normalized.get("fin"),
                "source": source,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Fehler bei Datenverarbeitung: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": source
            }
    
    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisiert Eingangsdaten"""
        
        # Prozess-Typ normalisieren
        prozess = data.get("prozess_typ", data.get("prozess", ""))
        if prozess:
            prozess = self.PROZESS_MAPPING.get(prozess.lower(), prozess)
        else:
            prozess = ""
        
        # Bearbeiter normalisieren
        bearbeiter = data.get("bearbeiter", data.get("bearbeiter_name", ""))
        bearbeiter = self.BEARBEITER_MAPPING.get(bearbeiter, bearbeiter)
        
        return {
            "fin": data.get("fin", data.get("fahrzeug_fin", "")),
            "prozess_typ": prozess,
            "status": data.get("status", data.get("neuer_status", "")),
            "bearbeiter": bearbeiter,
            "marke": data.get("marke"),
            "modell": data.get("modell")
        }
    
    async def _ensure_vehicle_exists(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Stellt sicher dass Fahrzeug existiert"""
            fin = data.get("fin")
            if not fin:
                return None
                
            # Prüfe ob Fahrzeug existiert
            vehicle = await self.vehicle_service.get_vehicle_details(fin)
            
            if not vehicle:
                # Für jetzt loggen wir nur - create_complete_vehicle erwartet FahrzeugStammCreate
                logger.info(f"🚗 Fahrzeug {fin} existiert nicht - würde erstellt werden")
                return None
            
            # Konvertiere zu Dict wenn FahrzeugMitProzess zurückkommt
            if hasattr(vehicle, 'dict'):
                return vehicle.dict()
            return {"fin": fin, "exists": True}
        
    async def _create_or_update_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
            """Erstellt oder aktualisiert einen Prozess"""
            
            # ProcessService erwartet diese Struktur für process_unified_data
            unified_data = {
                "fin": data.get("fin"),
                "prozess_typ": data.get("prozess_typ"),
                "status": data.get("status"),
                "bearbeiter": data.get("bearbeiter"),
                "source": "unified_handler"
            }
            
            logger.info(f"📋 Verarbeite Prozess: {unified_data['prozess_typ']} für {unified_data['fin']}")
            return await self.process_service.process_unified_data(unified_data, ProcessingSource.API)