# src/services/vehicle_service.py - Business Layer mit BigQueryService
"""Vehicle Service - Geschäftslogik für Fahrzeug-Management"""

import logging
from typing import Dict, Any, Optional, List
from src.services.bigquery_service import BigQueryService

logger = logging.getLogger(__name__)

class VehicleService:
    """Fahrzeug-Service mit Geschäftslogik - nutzt zentrale BigQueryService"""
    
    def __init__(self, bq_service: Optional[BigQueryService] = None):
        self.bq_service = bq_service or BigQueryService()
    
    async def get_vehicles(
        self, 
        status: Optional[str] = None,
        prozess: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Fahrzeuge mit optionalen Filtern abrufen"""
        try:
            fahrzeuge = await self.bq_service.get_fahrzeuge_mit_prozessen(
                status_filter=status,
                prozess_filter=prozess,
                limit=limit
            )
            
            # Geschäftslogik: Zusätzliche Verarbeitung
            for fahrzeug in fahrzeuge:
                # SLA-Status berechnen
                fahrzeug["sla_status"] = self._calculate_sla_status(fahrzeug.get("tage_bis_sla_deadline"))
                
                # Prioritäts-Label hinzufügen
                fahrzeug["prioritaet_label"] = self._get_priority_label(fahrzeug.get("prioritaet"))
            
            return {
                "fahrzeuge": fahrzeuge,
                "anzahl": len(fahrzeuge),
                "filter": {"status": status, "prozess": prozess, "limit": limit},
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Fahrzeuge abrufen Fehler: {e}")
            return {
                "fahrzeuge": [],
                "anzahl": 0,
                "error": str(e),
                "status": "error"
            }
    
    async def get_vehicle_details(self, fin: str) -> Optional[Dict[str, Any]]:
        """Vollständige Fahrzeug-Details mit allen Prozessen"""
        try:
            # Stammdaten abrufen
            stammdaten = await self.bq_service.get_fahrzeug_stamm(fin)
            if not stammdaten:
                logger.warning(f"Fahrzeug {fin} nicht in Stammdaten gefunden")
                return None
            
            # Alle Prozesse für das Fahrzeug abrufen
            prozesse = await self.bq_service.get_fahrzeug_prozesse(fin)
            
            # Geschäftslogik: Aktueller Prozess und Historie
            aktueller_prozess = None
            prozess_historie = []
            
            for prozess in prozesse:
                if prozess.get("status") not in ["abgeschlossen", "verkauft"]:
                    if not aktueller_prozess:
                        aktueller_prozess = prozess
                else:
                    prozess_historie.append(prozess)
            
            # Kombinierte Antwort
            return {
                **stammdaten,
                "aktueller_prozess": aktueller_prozess,
                "prozess_historie": prozess_historie,
                "anzahl_prozesse": len(prozesse),
                "status_datenquelle": "live_data"
            }
            
        except Exception as e:
            logger.error(f"Fahrzeug Details Fehler: {e}")
            return None
    
    async def create_complete_vehicle(
        self, 
        stammdaten: Dict[str, Any], 
        prozess_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Vollständiges Fahrzeug erstellen (Stammdaten + optional Prozess)"""
        try:
            # 1. Stammdaten erstellen
            stamm_success = await self.bq_service.create_fahrzeug_stamm(stammdaten)
            if not stamm_success:
                return {
                    "success": False,
                    "message": "Fahrzeug-Stammdaten konnten nicht erstellt werden",
                    "fin": stammdaten.get("fin")
                }
            
            # 2. Optional: Ersten Prozess erstellen
            prozess_success = True
            prozess_id = None
            
            if prozess_data:
                # Prozess-ID generieren falls nicht vorhanden
                if "prozess_id" not in prozess_data:
                    import uuid
                    prozess_data["prozess_id"] = f"PROC_{uuid.uuid4().hex[:8]}"
                
                # FIN übernehmen
                prozess_data["fin"] = stammdaten["fin"]
                
                prozess_success = await self.bq_service.create_fahrzeug_prozess(prozess_data)
                prozess_id = prozess_data["prozess_id"]
            
            return {
                "success": stamm_success and prozess_success,
                "message": "Fahrzeug erfolgreich erstellt",
                "fin": stammdaten["fin"],
                "stammdaten_erstellt": stamm_success,
                "prozess_erstellt": prozess_success,
                "prozess_id": prozess_id
            }
            
        except Exception as e:
            logger.error(f"Vollständige Fahrzeug-Erstellung Fehler: {e}")
            return {
                "success": False,
                "message": f"Fehler bei Fahrzeug-Erstellung: {str(e)}",
                "fin": stammdaten.get("fin")
            }
    
    async def update_vehicle_status(self, fin: str, new_status: str, bearbeiter: Optional[str] = None) -> bool:
        """Fahrzeug-Status aktualisieren (aktuellster Prozess)"""
        try:
            # Aktuellsten Prozess für Fahrzeug finden
            prozesse = await self.bq_service.get_fahrzeug_prozesse(fin)
            if not prozesse:
                logger.warning(f"Keine Prozesse für Fahrzeug {fin} gefunden")
                return False
            
            aktueller_prozess = prozesse[0]  # Neuester Prozess (ORDER BY updated_at DESC)
            prozess_id = aktueller_prozess.get("prozess_id")
            
            if not prozess_id:
                logger.error(f"Prozess-ID nicht gefunden für Fahrzeug {fin}")
                return False
            
            # Prozess-Status aktualisieren
            update_data = {"status": new_status}
            if bearbeiter:
                update_data["bearbeiter"] = bearbeiter
            
            return await self.bq_service.update_fahrzeug_prozess(prozess_id, update_data)
            
        except Exception as e:
            logger.error(f"Vehicle Status Update Fehler: {e}")
            return False
    
    async def get_vehicles_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Fahrzeuge nach Status filtern"""
        result = await self.get_vehicles(status=status, limit=100)
        return result.get("fahrzeuge", [])
    
    async def get_vehicles_by_prozess(self, prozess_typ: str) -> List[Dict[str, Any]]:
        """Fahrzeuge nach Prozesstyp filtern"""
        result = await self.get_vehicles(prozess=prozess_typ, limit=100)
        return result.get("fahrzeuge", [])
    
    def _calculate_sla_status(self, tage_bis_deadline: Optional[int]) -> str:
        """SLA-Status basierend auf verbleibenden Tagen berechnen"""
        if tage_bis_deadline is None:
            return "unknown"
        
        if tage_bis_deadline < 0:
            return "violated"
        elif tage_bis_deadline <= 1:
            return "critical"
        elif tage_bis_deadline <= 3:
            return "warning"
        else:
            return "ok"
    
    def _get_priority_label(self, prioritaet: Optional[int]) -> str:
        """Prioritäts-Label für UI"""
        if prioritaet is None:
            return "Normal"
        
        if prioritaet <= 2:
            return "Sehr Hoch"
        elif prioritaet <= 4:
            return "Hoch"
        elif prioritaet <= 6:
            return "Normal"
        elif prioritaet <= 8:
            return "Niedrig"
        else:
            return "Sehr Niedrig"