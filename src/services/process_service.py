# src/services/process_service.py - Korrigiert mit zentraler BigQueryService
"""Process Service für Prozess-Management - nutzt zentrale BigQueryService"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from src.models.integration import UnifiedProcessData
from src.services.bigquery_service import BigQueryService
from src.handlers.flowers_handler import FlowersHandler

logger = logging.getLogger(__name__)

# Bearbeiter-Mapping für Normalisierung
BEARBEITER_MAPPING = {
    "Thomas K.": "Thomas Küfner",
    "Max R.": "Maximilian Reinhardt", 
    "Hans M.": "Hans Müller",
    "Anna K.": "Anna Klein", 
    "Thomas W.": "Thomas Weber",
    "Stefan B.": "Stefan Becker",
    "Mike S.": "Michael Schmidt",
    "Jürgen": "Jürgen Hoffmann",
    "Klaus": "Klaus Neumann",
    "Sandra": "Sandra Richter",
    "Alex": "Alexander König",
}

class ProcessService:
    """Zentrale Geschäftslogik für alle Prozess-Operationen"""
    
    def __init__(self, bq_service: Optional[BigQueryService] = None):
        self.bq_service = bq_service or BigQueryService()
        self.flowers_handler = FlowersHandler()
    
    async def process_unified_data(self, unified_data: UnifiedProcessData) -> Dict[str, Any]:
        """Einheitliche Datenverarbeitung für alle Integrationen (Zapier, E-Mail, Webhook)"""
        try:
            process_id = f"PROC_{uuid.uuid4().hex[:8]}"
            warnings = []
            
            logger.info(f"Verarbeite {unified_data.datenquelle}-Daten: FIN={unified_data.fin}, Prozess={unified_data.prozess_typ}")
            
            # 1. Prozess-Typ normalisieren
            normalized_prozess = self.flowers_handler.normalize_prozess_typ(unified_data.prozess_typ)
            if normalized_prozess != unified_data.prozess_typ:
                logger.info(f"Prozess normalisiert: '{unified_data.prozess_typ}' -> '{normalized_prozess}'")
                warnings.append(f"Prozess-Typ angepasst: {unified_data.prozess_typ} -> {normalized_prozess}")
            
            # 2. Bearbeiter-Namen normalisieren
            mapped_bearbeiter = self.resolve_bearbeiter(unified_data.bearbeiter)
            if mapped_bearbeiter != unified_data.bearbeiter:
                logger.info(f"Bearbeiter gemappt: '{unified_data.bearbeiter}' -> '{mapped_bearbeiter}'")
                warnings.append(f"Bearbeiter angepasst: {unified_data.bearbeiter} -> {mapped_bearbeiter}")
            
            # 3. Fahrzeug-Stammdaten erstellen falls nötig
            vehicle_created = False
            if unified_data.marke and unified_data.modell:
                vehicle_exists = await self._check_vehicle_exists(unified_data.fin)
                
                if not vehicle_exists:
                    vehicle_data = self._build_vehicle_data(unified_data)
                    vehicle_created = await self.bq_service.create_fahrzeug_stamm(vehicle_data)
                    
                    if vehicle_created:
                        logger.info(f"✅ Fahrzeug automatisch erstellt: {unified_data.fin}")
                    else:
                        warnings.append(f"Fahrzeug-Stammdaten konnten nicht erstellt werden: {unified_data.fin}")
                else:
                    logger.info(f"Fahrzeug {unified_data.fin} bereits vorhanden")
            
            # 4. Prozess erstellen
            process_data = self._build_process_data(unified_data, process_id, normalized_prozess, mapped_bearbeiter)
            process_saved = await self.bq_service.create_fahrzeug_prozess(process_data)
            
            if not process_saved:
                raise Exception("Prozess konnte nicht in BigQuery gespeichert werden")
            
            return {
                "success": True,
                "message": "Prozess erfolgreich verarbeitet",
                "process_id": process_id,
                "fin": unified_data.fin,
                "prozess_typ": normalized_prozess,
                "status": unified_data.status,
                "bearbeiter": mapped_bearbeiter,
                "vehicle_created": vehicle_created,
                "warnings": warnings,
                "datenquelle": unified_data.datenquelle,
                "verarbeitet_am": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Unified Data Processing fehlgeschlagen: {e}")
            return {
                "success": False,
                "message": f"Verarbeitungsfehler: {str(e)}",
                "fin": unified_data.fin,
                "prozess_typ": unified_data.prozess_typ,
                "status": unified_data.status,
                "datenquelle": unified_data.datenquelle,
                "error": str(e)
            }
    
    async def create_process(self, process_data: Dict[str, Any]) -> Dict[str, Any]:
        """Neuen Prozess erstellen"""
        try:
            # Prozess-ID generieren falls nicht vorhanden
            if "prozess_id" not in process_data:
                process_data["prozess_id"] = f"PROC_{uuid.uuid4().hex[:8]}"
            
            success = await self.bq_service.create_fahrzeug_prozess(process_data)
            
            return {
                "success": success,
                "process_id": process_data["prozess_id"],
                "message": "Prozess erfolgreich erstellt" if success else "Prozess-Erstellung fehlgeschlagen",
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Prozess-Erstellung fehlgeschlagen: {e}")
            return {
                "success": False,
                "message": f"Fehler: {str(e)}",
                "error": str(e)
            }
    
    async def update_process_status(
        self, 
        prozess_id: str, 
        new_status: str, 
        bearbeiter: Optional[str] = None, 
        notizen: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prozess-Status aktualisieren"""
        try:
            update_data = {"status": new_status}
            
            if bearbeiter:
                update_data["bearbeiter"] = self.resolve_bearbeiter(bearbeiter)
            if notizen:
                update_data["notizen"] = notizen
            
            # Zeitstempel für Status-Änderungen
            if new_status.lower() == "abgeschlossen":
                update_data["ende_timestamp"] = datetime.now()
            elif new_status.lower() in ["in_bearbeitung", "gestartet"]:
                update_data["start_timestamp"] = datetime.now()
            
            success = await self.bq_service.update_fahrzeug_prozess(prozess_id, update_data)
            
            return {
                "success": success,
                "process_id": prozess_id,
                "new_status": new_status,
                "message": "Status erfolgreich aktualisiert" if success else "Status-Update fehlgeschlagen",
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Status-Update fehlgeschlagen: {e}")
            return {
                "success": False,
                "process_id": prozess_id,
                "message": f"Fehler: {str(e)}",
                "error": str(e)
            }
    
    async def complete_process(self, prozess_id: str, completion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prozess abschließen mit Zeitberechnung"""
        try:
            # Aktuellen Prozess abrufen für Zeitberechnung
            prozesse = await self.bq_service.get_fahrzeug_prozesse(completion_data.get("fin", ""))
            current_process = None
            
            for prozess in prozesse:
                if prozess.get("prozess_id") == prozess_id:
                    current_process = prozess
                    break
            
            update_data = {
                "status": "abgeschlossen",
                "ende_timestamp": datetime.now()
            }
            
            # Dauer berechnen falls Start-Timestamp vorhanden
            if current_process and current_process.get("start_timestamp"):
                try:
                    start_time = datetime.fromisoformat(current_process["start_timestamp"].replace('Z', '+00:00'))
                    end_time = datetime.now()
                    duration_minutes = int((end_time - start_time).total_seconds() / 60)
                    update_data["dauer_minuten"] = duration_minutes
                except Exception as duration_error:
                    logger.warning(f"Dauer-Berechnung fehlgeschlagen: {duration_error}")
            
            # Completion-spezifische Daten hinzufügen
            if completion_data.get("notizen"):
                update_data["notizen"] = completion_data["notizen"]
            if completion_data.get("bearbeiter"):
                update_data["bearbeiter"] = self.resolve_bearbeiter(completion_data["bearbeiter"])
            
            success = await self.bq_service.update_fahrzeug_prozess(prozess_id, update_data)
            
            return {
                "success": success,
                "process_id": prozess_id,
                "completion_time": update_data["ende_timestamp"].isoformat(),
                "duration_minutes": update_data.get("dauer_minuten"),
                "message": "Prozess erfolgreich abgeschlossen" if success else "Prozess-Abschluss fehlgeschlagen"
            }
            
        except Exception as e:
            logger.error(f"Prozess-Abschluss fehlgeschlagen: {e}")
            return {
                "success": False,
                "process_id": prozess_id,
                "message": f"Fehler: {str(e)}",
                "error": str(e)
            }
    
    # ========================================
    # UTILITY Methoden
    # ========================================
    
    def resolve_bearbeiter(self, bearbeiter_input: Optional[str]) -> Optional[str]:
        """Bearbeiter-Namen normalisieren mit Mapping"""
        if not bearbeiter_input:
            return None
        
        # Direkte Zuordnung
        if bearbeiter_input in BEARBEITER_MAPPING:
            return BEARBEITER_MAPPING[bearbeiter_input]
        
        # Fuzzy-Matching für unvollständige Namen
        input_lower = bearbeiter_input.lower()
        for flowers_key, full_name in BEARBEITER_MAPPING.items():
            if input_lower in flowers_key.lower() or flowers_key.lower() in input_lower:
                return full_name
        
        # Keine Zuordnung gefunden - Original zurückgeben
        return bearbeiter_input
    
    async def _check_vehicle_exists(self, fin: str) -> bool:
        """Prüft ob Fahrzeug in Stammdaten existiert"""
        try:
            stammdaten = await self.bq_service.get_fahrzeug_stamm(fin)
            return stammdaten is not None
        except Exception as e:
            logger.error(f"Vehicle Existenz-Check fehlgeschlagen: {e}")
            return False
    
    def _build_vehicle_data(self, unified_data: UnifiedProcessData) -> Dict[str, Any]:
        """Fahrzeug-Stammdaten aus UnifiedProcessData erstellen"""
        return {
            "fin": unified_data.fin,
            "marke": unified_data.marke or "Unbekannt",
            "modell": unified_data.modell or "Unbekannt",
            "antriebsart": unified_data.antriebsart or "Unbekannt",
            "farbe": unified_data.farbe or "Unbekannt",
            "baujahr": unified_data.baujahr,
            "datum_erstzulassung": unified_data.datum_erstzulassung,
            "kw_leistung": unified_data.kw_leistung,
            "km_stand": unified_data.km_stand,
            "anzahl_fahrzeugschluessel": unified_data.anzahl_fahrzeugschluessel,
            "bereifungsart": unified_data.bereifungsart or "Unbekannt",
            "anzahl_vorhalter": unified_data.anzahl_vorhalter,
            "ek_netto": unified_data.ek_netto,
            "besteuerungsart": unified_data.besteuerungsart or "Unbekannt",
            "erstellt_aus_email": unified_data.datenquelle == "email",
            "datenquelle_fahrzeug": unified_data.datenquelle
        }
    
    def _build_process_data(
        self, 
        unified_data: UnifiedProcessData, 
        process_id: str, 
        normalized_prozess: str, 
        mapped_bearbeiter: Optional[str]
    ) -> Dict[str, Any]:
        """Prozess-Daten aus UnifiedProcessData erstellen"""
        process_data = {
            "prozess_id": process_id,
            "fin": unified_data.fin,
            "prozess_typ": normalized_prozess,
            "status": unified_data.status,
            "bearbeiter": mapped_bearbeiter,
            "prioritaet": unified_data.prioritaet or 5,
            "datenquelle": unified_data.datenquelle,
            "notizen": unified_data.notizen
        }
        
        # Zeitstempel setzen basierend auf Status
        if unified_data.external_timestamp:
            if unified_data.status.lower() == "abgeschlossen":
                process_data["ende_timestamp"] = unified_data.external_timestamp
            elif unified_data.status.lower() in ["in_bearbeitung", "gestartet"]:
                process_data["start_timestamp"] = unified_data.external_timestamp
        
        # Zusatzdaten als Notizen anhängen
        if unified_data.zusatz_daten:
            import json
            zusatz_json = json.dumps(unified_data.zusatz_daten, default=str, ensure_ascii=False)
            existing_notizen = process_data.get("notizen", "")
            process_data["notizen"] = f"{existing_notizen} | Zusatzdaten: {zusatz_json}".strip(" |")
        
        return process_data