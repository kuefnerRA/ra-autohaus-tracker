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
from src.models.integration import FahrzeugStammCreate, Datenquelle

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
        "delivery": "Anlieferung",
        "anlieferung": "Anlieferung",
        "fahrzeuganlage": "Einkauf", 
        "(1) da fahrzeuganlage": "Einkauf",    
        "(0) start fahrzeugaufbereitung" : "Aufbereitung",
        "(1) Aufbereitung in Arbeit" : "Aufbereitung",    
        "(4.0) werkstattplanung" : "Werkstatt",
        "aufbereitung": "Aufbereitung",  
        "aufbereitung in arbeit": "Aufbereitung",
        "werkstatt": "Werkstatt",  
        "foto": "Foto",  
        "fotoshooting": "Foto"  
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
        
        # Konvertiere alle PROZESS_MAPPING Keys zu lowercase beim Init
        self.prozess_mapping_lower = {
            key.lower(): value 
            for key, value in self.PROZESS_MAPPING.items()
        }

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

        # Debug-Log am Anfang
        logger.info(f"📊 Eingangsdaten in _normalize_data: Marke={data.get('marke')}, Modell={data.get('modell')}")
        
        # Prozess-Typ normalisieren (wie gehabt)
        prozess = data.get("prozess_typ", data.get("prozess", ""))
        if prozess:
            prozess_lower = prozess.lower()
            if prozess_lower in self.prozess_mapping_lower:  # RICHTIG!
                prozess = self.prozess_mapping_lower[prozess_lower]  # RICHTIG!
            else:
                logger.warning(f"⚠️ Unbekannter Prozesstyp: {prozess}")
                prozess = ""  
        
        # Bearbeiter normalisieren
        bearbeiter = data.get("bearbeiter", data.get("bearbeiter_name", ""))
        bearbeiter = self.BEARBEITER_MAPPING.get(bearbeiter, bearbeiter)
        
        # ALLE Daten durchreichen!
        normalized = {
            "fin": data.get("fin", data.get("fahrzeug_fin", "")),
            "prozess_typ": prozess,
            "status": data.get("status", data.get("neuer_status", "")),
            "bearbeiter": bearbeiter,
            # Fahrzeugstammdaten
            "marke": data.get("marke"),
            "modell": data.get("modell"),
            "antriebsart": data.get("antriebsart"),
            "farbe": data.get("farbe"),  # FEHLTE
            "baujahr": data.get("baujahr"),  # FEHLTE
            "datum_erstzulassung": data.get("datum_erstzulassung"),
            "ek_netto": data.get("ek_netto"),
            "km_stand": data.get("km_stand"),
            "kw_leistung": data.get("kw_leistung"),
            "anzahl_fahrzeugschluessel": data.get("anzahl_fahrzeugschluessel"),
            "anzahl_vorhalter": data.get("anzahl_vorhalter"),
            "bereifungsart": data.get("bereifungsart"),
            "besteuerungsart": data.get("besteuerungsart"),
        }

        # Debug-Log am Ende
        logger.info(f"📊 Normalisierte Daten: Marke={normalized.get('marke')}, Modell={normalized.get('modell')}")
        
        return normalized      
        
    async def _ensure_vehicle_exists(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Stellt sicher dass Fahrzeug existiert und aktualisiert Stammdaten"""
        fin = data.get("fin")
        if not fin:
            return None
        
        # Debug-Log
        logger.info(f"🚗 _ensure_vehicle_exists - Eingangsdaten: Marke={data.get('marke')}, Modell={data.get('modell')}")

        # Prüfe ob Fahrzeug existiert
        vehicle = await self.vehicle_service.get_vehicle_details(fin)
        
        # Nur "Unbekannt" setzen wenn wirklich KEINE Daten vorhanden
        marke = data.get("marke") if data.get("marke") else "Unbekannt"
        modell = data.get("modell") if data.get("modell") else "Unbekannt"
        
        logger.info(f"🚗 Finale Werte für Erstellung: Marke={marke}, Modell={modell}")
        
        if not vehicle:
            # Fahrzeug existiert nicht - ERSTELLEN
            logger.info(f"🚗 Erstelle neues Fahrzeug {fin}")
            
            # Bereite Daten vor - filtere None-Werte
            fahrzeug_data = {
                "fin": fin,
                "marke": data.get("marke", "Unbekannt"),
                "modell": data.get("modell", "Unbekannt"),
            }
            
            # Füge optionale Felder nur hinzu, wenn sie vorhanden sind
            optional_fields = [
                "antriebsart", "farbe", "baujahr", "datum_erstzulassung",
                "kw_leistung", "km_stand", "anzahl_fahrzeugschluessel",
                "bereifungsart", "anzahl_vorhalter", "ek_netto", "besteuerungsart"
            ]
            
            for field in optional_fields:
                if field in data and data[field] is not None:
                    fahrzeug_data[field] = data[field]
            
            # Zusätzliche Felder
            fahrzeug_data["erstellt_aus_email"] = False
            fahrzeug_data["datenquelle_fahrzeug"] = Datenquelle.ZAPIER
            
            # FahrzeugStammCreate Objekt erstellen
            fahrzeug_stamm = FahrzeugStammCreate(**fahrzeug_data)
            
            # Fahrzeug erstellen
            vehicle = await self.vehicle_service.create_complete_vehicle(fahrzeug_stamm)
        else:
            # Bestehendes Fahrzeug - Update-Logik bleibt unverändert
            logger.info(f"🔄 Aktualisiere Fahrzeugdaten für {fin}")
            
            update_data = {}
            # Nur Felder mit Werten != "Unbekannt" updaten
            if data.get("marke") and data.get("marke") != "Unbekannt" and vehicle.marke == "Unbekannt":
                update_data["marke"] = data.get("marke")
            if data.get("modell") and data.get("modell") != "Unbekannt" and vehicle.modell == "Unbekannt":
                update_data["modell"] = data.get("modell")
            
            if update_data:
                await self.vehicle_service.update_vehicle(fin, update_data, create_update_process=False)
        
        # Korrekte Konvertierung zu Dict
        if hasattr(vehicle, 'dict'):
            return vehicle.dict()
        elif hasattr(vehicle, 'model_dump'):
            return vehicle.model_dump()
        else:
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