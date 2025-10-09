# src/services/info_service.py
"""
Info Service für System-Konfiguration und statische Daten
Nutzt zentrale Configs statt Daten zu duplizieren
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

from src.core.process_config import ProcessConfig
from src.core.mappings import CentralMappings

logger = logging.getLogger(__name__)

class InfoService:
    """Service für System-Information und Konfiguration - nutzt zentrale Definitionen"""
    
    def __init__(self):
        # Referenziere zentrale Configs statt zu duplizieren
        self.process_config = ProcessConfig
        self.mappings = CentralMappings
        logger.info("✅ InfoService initialisiert (nutzt zentrale Configs)")
    
    async def get_prozesse(self) -> Dict[str, Any]:
        """
        Gibt alle Prozess-Definitionen zurück
        
        Returns:
            Dict mit allen Prozess-Definitionen aus zentraler Config
        """
        # Transformiere ProcessConfig für API-Response
        prozesse = {}
        for prozess_name, config in self.process_config.PROCESS_CONFIG.items():
            prozesse[prozess_name] = {
                "sla_stunden": config["sla_stunden"],
                "priority_range": config["priority_range"],
                "sla_tage": config["sla_stunden"] / 24,
                "beschreibung": self._get_prozess_beschreibung(prozess_name)
            }
        
        return {
            "prozesse": prozesse,
            "gesamt": len(prozesse),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_prozess_details(self, prozess_typ: str) -> Dict[str, Any]:
        """
        Gibt Details zu einem spezifischen Prozess zurück
        
        Args:
            prozess_typ: Name des Prozesses
            
        Returns:
            Dict mit Prozess-Details oder Fehler
        """
        if prozess_typ not in self.process_config.PROCESS_CONFIG:
            return {
                "error": f"Prozess '{prozess_typ}' nicht gefunden",
                "verfuegbare_prozesse": list(self.process_config.PROCESS_CONFIG.keys())
            }
        
        config = self.process_config.PROCESS_CONFIG[prozess_typ]
        return {
            "prozess_typ": prozess_typ,
            "sla_stunden": config["sla_stunden"],
            "priority_range": config["priority_range"],
            "sla_tage": config["sla_stunden"] / 24,
            "beschreibung": self._get_prozess_beschreibung(prozess_typ),
            "ist_spezieller_prozess": self.process_config.is_special_process(prozess_typ),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_bearbeiter(self) -> Dict[str, Any]:
        """
        Gibt alle Bearbeiter-Mappings zurück
        
        Returns:
            Dict mit Bearbeiter-Mappings für Normalisierung
        """
        # Extrahiere unique Bearbeiter aus Mappings
        unique_bearbeiter = set(self.mappings.BEARBEITER_MAPPINGS.values())
        
        return {
            "bearbeiter": list(unique_bearbeiter),
            "gesamt": len(unique_bearbeiter),
            "mappings": self.mappings.BEARBEITER_MAPPINGS,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_bearbeiter_details(self, bearbeiter_name: str) -> Dict[str, Any]:
        """
        Gibt Details zu einem spezifischen Bearbeiter zurück
        
        Args:
            bearbeiter_name: Name des Bearbeiters
            
        Returns:
            Dict mit Bearbeiter-Mappings oder Fehler
        """
        # Normalisiere Bearbeiter-Name
        normalized_name = self.mappings.normalize_bearbeiter(bearbeiter_name)
        
        if not normalized_name:
            return {
                "error": f"Bearbeiter '{bearbeiter_name}' nicht gefunden",
                "verfuegbare_bearbeiter": list(set(self.mappings.BEARBEITER_MAPPINGS.values()))
            }
        
        # Finde alle Varianten, die zu diesem Namen mappen
        varianten = [k for k, v in self.mappings.BEARBEITER_MAPPINGS.items() if v == normalized_name]
        
        return {
            "name": normalized_name,
            "varianten": varianten,
            "timestamp": datetime.now().isoformat()
        }

    async def get_status_definitionen(self) -> Dict[str, Any]:
        """
        Gibt alle Status-Definitionen zurück
        
        Returns:
            Dict mit allen Status-Mappings aus zentraler Config
        """
        # Gruppiere Status nach Kategorie
        status_kategorien = {
            "WARTESCHLANGE": {
                "beschreibung": "Prozess wurde erstellt, wartet auf Bearbeitung",
                "farbe": "#FCD34D",  # Gelb
                "icon": "clock",
                "varianten": [k for k, v in self.mappings.STATUS_MAPPINGS.items() if v == "WARTESCHLANGE"]
            },
            "AKTIV": {
                "beschreibung": "Wird aktiv bearbeitet",
                "farbe": "#3B82F6",  # Blau
                "icon": "play",
                "varianten": [k for k, v in self.mappings.STATUS_MAPPINGS.items() if v == "AKTIV"]
            },
            "BEENDET": {
                "beschreibung": "Erfolgreich abgeschlossen",
                "farbe": "#10B981",  # Grün
                "icon": "check-circle",
                "varianten": [k for k, v in self.mappings.STATUS_MAPPINGS.items() if v == "BEENDET"]
            }
        }
        
        return {
            "status_kategorien": status_kategorien,
            "alle_mappings": self.mappings.STATUS_MAPPINGS,
            "gesamt": len(self.mappings.STATUS_MAPPINGS),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_system_config(self) -> Dict[str, Any]:
        """
        Gibt die komplette System-Konfiguration zurück
        
        Returns:
            Dict mit System-Konfiguration
        """
        return {
            "system": {
                "name": "RA Autohaus Tracker",
                "version": "2.1.0",  # Version erhöht nach Refactoring
                "umgebung": "production",
                "bigquery_projekt": "ra-autohaus-tracker",
                "bigquery_dataset": "autohaus",
                "region": "europe-west3"
            },
            "limits": {
                "max_prozesse_pro_fahrzeug": 50,
                "max_bearbeiter_pro_prozess": 3,
                "max_prioritaet": 10,
                "min_prioritaet": 1,
                "default_prioritaet": 5
            },
            "integrationen": {
                "zapier": {
                    "enabled": True,
                    "endpoint": "/integration/zapier/webhook"
                },
                "flowers": {
                    "enabled": True,
                    "email_endpoint": "/integration/flowers/email",
                    "webhook_endpoint": "/integration/flowers/webhook"
                },
                "email_imap": {
                    "enabled": True,
                    "endpoint": "/email/process"
                }
            },
            "features": {
                "auto_sla_calculation": True,
                "email_notifications": False,
                "slack_integration": False,
                "dashboard_enabled": True,
                "vin_decoder_enabled": True,
                "cleanup_job_enabled": True
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_mappings(self) -> Dict[str, Any]:
        """
        Gibt alle Mappings für Integrationen zurück - direkt aus zentralen Configs
        
        Returns:
            Dict mit allen Mappings
        """
        return {
            "prozess_mapping": self.mappings.PROZESS_MAPPINGS,
            "bearbeiter_mapping": self.mappings.BEARBEITER_MAPPINGS,
            "status_mapping": self.mappings.STATUS_MAPPINGS,
            "special_processes": self.process_config.SPECIAL_PROCESS_TYPES,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Gibt den Health-Status des Systems zurück
        
        Returns:
            Dict mit Health-Status
        """
        return {
            "status": "healthy",
            "services": {
                "api": "running",
                "bigquery": "connected",
                "dashboard": "active",
                "cleanup_job": "scheduled"
            },
            "configs_loaded": {
                "process_config": bool(self.process_config.PROCESS_CONFIG),
                "mappings": bool(self.mappings.PROZESS_MAPPINGS)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    # Hilfsfunktionen für zusätzliche Metadaten
    def _get_prozess_beschreibung(self, prozess_typ: str) -> str:
        """Gibt Beschreibung für Prozesstyp zurück"""
        beschreibungen = {
            "Einkauf": "Fahrzeugankauf und Ersterfassung",
            "Anlieferung": "Fahrzeugannahme und Eingangserfassung",
            "Aufbereitung": "Reinigung und optische Aufbereitung",
            "Foto": "Fahrzeugfotografie für Online-Präsenz",
            "Werkstatt": "Technische Prüfung und Reparaturen",
            "Verkauf": "Verkaufsprozess und Übergabe",
            "Gewährleistung": "Gewährleistungsabwicklung und Reklamationen",
            "Bearbeiterwechsel": "Wechsel des zuständigen Bearbeiters",
            "Deadlinewechsel": "Änderung der Prozess-Deadline"
        }
        return beschreibungen.get(prozess_typ, "Keine Beschreibung verfügbar")
