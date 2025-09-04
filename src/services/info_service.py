# src/services/info_service.py
"""
Info Service für System-Konfiguration und statische Daten
Verantwortlich für Prozess-Definitionen, Bearbeiter-Info und System-Config
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class InfoService:
    """Service für System-Information und Konfiguration"""
    
    # Prozess-Definitionen mit SLA und Prioritäten
    PROZESSE = {
        "Einkauf": {
            "sla_stunden": 48,
            "priority_range": [1, 3],
            "beschreibung": "Fahrzeugankauf und Vertragsabwicklung",
            "verantwortlich": "Einkaufsteam",
            "schritte": [
                "Bewertung",
                "Preisverhandlung", 
                "Vertragsabschluss",
                "Zahlungsabwicklung"
            ]
        },
        "Anlieferung": {
            "sla_stunden": 24,
            "priority_range": [2, 4],
            "beschreibung": "Fahrzeugannahme und Ersterfassung",
            "verantwortlich": "Logistikteam",
            "schritte": [
                "Transportkoordination",
                "Fahrzeugannahme",
                "Erstinspektion",
                "Stellplatzzuweisung"
            ]
        },
        "Aufbereitung": {
            "sla_stunden": 72,
            "priority_range": [3, 5],
            "beschreibung": "Reinigung und optische Aufbereitung",
            "verantwortlich": "Aufbereitungsteam",
            "schritte": [
                "Innenreinigung",
                "Außenreinigung",
                "Politur",
                "Qualitätskontrolle"
            ]
        },
        "Foto": {
            "sla_stunden": 24,
            "priority_range": [4, 6],
            "beschreibung": "Fahrzeugfotografie für Online-Präsenz",
            "verantwortlich": "Marketing",
            "schritte": [
                "Positionierung",
                "Außenaufnahmen",
                "Innenraumaufnahmen",
                "Bildbearbeitung"
            ]
        },
        "Werkstatt": {
            "sla_stunden": 168,  # 7 Tage
            "priority_range": [2, 5],
            "beschreibung": "Technische Prüfung und Reparaturen",
            "verantwortlich": "Werkstattteam",
            "schritte": [
                "Diagnose",
                "Reparaturplanung",
                "Durchführung",
                "Endkontrolle"
            ]
        },
        "Verkauf": {
            "sla_stunden": 720,  # 30 Tage
            "priority_range": [1, 3],
            "beschreibung": "Verkaufsprozess und Übergabe",
            "verantwortlich": "Verkaufsteam",
            "schritte": [
                "Online-Inserat",
                "Kundenberatung",
                "Probefahrt",
                "Vertragsabschluss",
                "Fahrzeugübergabe"
            ]
        }
    }
    
    # Bearbeiter-Informationen
    BEARBEITER = {
        "Thomas Küfner": {
            "rolle": "Prozessmanager",
            "bereiche": ["Aufbereitung", "Foto", "Werkstatt"],
            "email": "thomas.kuefner@reinhardt-automobile.de",
            "max_kapazitaet": 15
        },
        "Maximilian Reinhardt": {
            "rolle": "Geschäftsführer",
            "bereiche": ["Einkauf", "Verkauf"],
            "email": "maximilian.reinhardt@reinhardt-automobile.de",
            "max_kapazitaet": 10
        },
        "Team Aufbereitung": {
            "rolle": "Aufbereitungsteam",
            "bereiche": ["Aufbereitung"],
            "email": "aufbereitung@reinhardt-automobile.de",
            "max_kapazitaet": 20
        },
        "Team Werkstatt": {
            "rolle": "Werkstattteam",
            "bereiche": ["Werkstatt"],
            "email": "werkstatt@reinhardt-automobile.de",
            "max_kapazitaet": 12
        }
    }
    
    # Status-Definitionen
    STATUS_DEFINITIONEN = {
        "neu": {
            "beschreibung": "Prozess wurde erstellt, noch nicht gestartet",
            "farbe": "#9CA3AF",  # Grau
            "icon": "clock"
        },
        "wartend": {
            "beschreibung": "Wartet auf Bearbeitung",
            "farbe": "#FCD34D",  # Gelb
            "icon": "pause"
        },
        "in_bearbeitung": {
            "beschreibung": "Wird aktiv bearbeitet",
            "farbe": "#3B82F6",  # Blau
            "icon": "play"
        },
        "pausiert": {
            "beschreibung": "Temporär unterbrochen",
            "farbe": "#FB923C",  # Orange
            "icon": "pause-circle"
        },
        "abgeschlossen": {
            "beschreibung": "Erfolgreich abgeschlossen",
            "farbe": "#10B981",  # Grün
            "icon": "check-circle"
        },
        "abgebrochen": {
            "beschreibung": "Prozess wurde abgebrochen",
            "farbe": "#EF4444",  # Rot
            "icon": "x-circle"
        }
    }
    
    def __init__(self):
        logger.info("✅ InfoService initialisiert")
    
    async def get_prozesse(self) -> Dict[str, Any]:
        """
        Gibt alle Prozess-Definitionen zurück
        
        Returns:
            Dict mit allen Prozess-Definitionen
        """
        return {
            "prozesse": self.PROZESSE,
            "gesamt": len(self.PROZESSE),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_prozess_details(self, prozess_typ: str) -> Dict[str, Any]:
        """
        Gibt Details zu einem spezifischen Prozess zurück
        
        Args:
            prozess_typ: Name des Prozesses
            
        Returns:
            Dict mit Prozess-Details oder None wenn nicht gefunden
        """
        if prozess_typ not in self.PROZESSE:
            return {
                "error": f"Prozess '{prozess_typ}' nicht gefunden",
                "verfuegbare_prozesse": list(self.PROZESSE.keys())
            }
        
        prozess = self.PROZESSE[prozess_typ]
        return {
            "prozess_typ": prozess_typ,
            **prozess,
            "sla_tage": prozess["sla_stunden"] / 24,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_bearbeiter(self) -> Dict[str, Any]:
        """
        Gibt alle Bearbeiter-Informationen zurück
        
        Returns:
            Dict mit allen Bearbeitern
        """
        return {
            "bearbeiter": self.BEARBEITER,
            "gesamt": len(self.BEARBEITER),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_bearbeiter_details(self, bearbeiter_name: str) -> Dict[str, Any]:
        """
        Gibt Details zu einem spezifischen Bearbeiter zurück
        
        Args:
            bearbeiter_name: Name des Bearbeiters
            
        Returns:
            Dict mit Bearbeiter-Details oder Fehler wenn nicht gefunden
        """
        # Normalisiere Bearbeiter-Name
        normalized_name = self._normalize_bearbeiter(bearbeiter_name)
        
        if normalized_name not in self.BEARBEITER:
            return {
                "error": f"Bearbeiter '{bearbeiter_name}' nicht gefunden",
                "verfuegbare_bearbeiter": list(self.BEARBEITER.keys())
            }
        
        bearbeiter = self.BEARBEITER[normalized_name]
        return {
            "name": normalized_name,
            **bearbeiter,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_status_definitionen(self) -> Dict[str, Any]:
        """
        Gibt alle Status-Definitionen zurück
        
        Returns:
            Dict mit allen Status-Definitionen
        """
        return {
            "status": self.STATUS_DEFINITIONEN,
            "gesamt": len(self.STATUS_DEFINITIONEN),
            "verfuegbare_status": list(self.STATUS_DEFINITIONEN.keys()),
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
                "version": "2.0.0",
                "umgebung": "production",
                "bigquery_projekt": "ra-autohaus-tracker",
                "bigquery_dataset": "autohaus",
                "region": "europe-west3"
            },
            "limits": {
                "max_prozesse_pro_fahrzeug": 10,
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
                "audaris": {
                    "enabled": False,
                    "endpoint": "/integration/audaris/sync"
                }
            },
            "features": {
                "auto_sla_calculation": True,
                "email_notifications": False,
                "slack_integration": False,
                "dashboard_enabled": True
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_mappings(self) -> Dict[str, Any]:
        """
        Gibt alle Mappings für Integrationen zurück
        
        Returns:
            Dict mit allen Mappings
        """
        return {
            "prozess_mapping": {
                "gwa": "Aufbereitung",
                "garage": "Werkstatt",
                "photos": "Foto",
                "sales": "Verkauf",
                "purchase": "Einkauf",
                "delivery": "Anlieferung",
                "aufbereitung": "Aufbereitung",
                "werkstatt": "Werkstatt",
                "foto": "Foto",
                "verkauf": "Verkauf",
                "einkauf": "Einkauf",
                "anlieferung": "Anlieferung"
            },
            "bearbeiter_mapping": {
                "Thomas K.": "Thomas Küfner",
                "Max R.": "Maximilian Reinhardt",
                "Thomas": "Thomas Küfner",
                "Max": "Maximilian Reinhardt",
                "Maximilian": "Maximilian Reinhardt"
            },
            "status_mapping": {
                "new": "neu",
                "waiting": "wartend",
                "in_progress": "in_bearbeitung",
                "paused": "pausiert",
                "completed": "abgeschlossen",
                "cancelled": "abgebrochen",
                "done": "abgeschlossen",
                "gestartet": "in_bearbeitung",
                "fertig": "abgeschlossen"
            },
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
                "dashboard": "active"
            },
            "uptime_seconds": 0,  # Würde normalerweise aus Startup-Zeit berechnet
            "timestamp": datetime.now().isoformat()
        }
    
    # Hilfsfunktionen
    def _normalize_bearbeiter(self, name: str) -> str:
        """
        Normalisiert Bearbeiter-Namen
        
        Args:
            name: Ursprünglicher Name
            
        Returns:
            Normalisierter Name
        """
        # Mapping für Kurzformen
        mapping = {
            "Thomas K.": "Thomas Küfner",
            "Max R.": "Maximilian Reinhardt",
            "Thomas": "Thomas Küfner",
            "Max": "Maximilian Reinhardt"
        }
        
        return mapping.get(name, name)