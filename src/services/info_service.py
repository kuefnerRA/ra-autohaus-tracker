# src/services/info_service.py - Zeichenkodierung korrigiert
"""Info Service für System-Informationen"""

from typing import Dict, Any

class InfoService:
    
    @staticmethod
    def get_prozesse_info() -> Dict[str, Any]:
        """Info über alle verfügbaren Prozesse"""
        prozesse = {
            "einkauf": {
                "beschreibung": "Fahrzeug-Einkauf und Ankauf",
                "status_optionen": ["gestartet", "in_verhandlung", "abgeschlossen", "abgelehnt"],
                "durchschnittsdauer_tage": 5,
                "sla_stunden": 48
            },
            "anlieferung": {
                "beschreibung": "Fahrzeug-Anlieferung und Transport",
                "status_optionen": ["geplant", "unterwegs", "angekommen", "verzögert"],
                "durchschnittsdauer_tage": 2,
                "sla_stunden": 24
            },
            "aufbereitung": {
                "beschreibung": "Fahrzeug-Aufbereitung und Reinigung",
                "status_optionen": ["warteschlange", "in_bearbeitung", "abgeschlossen", "nachbesserung"],
                "durchschnittsdauer_tage": 3,
                "sla_stunden": 72
            },
            "foto": {
                "beschreibung": "Professionelle Fahrzeug-Fotografie",
                "status_optionen": ["warteschlange", "fotoshooting", "bearbeitung", "fertig"],
                "durchschnittsdauer_tage": 1,
                "sla_stunden": 24
            },
            "werkstatt": {
                "beschreibung": "Reparatur und technische Prüfung",
                "status_optionen": ["diagnose", "reparatur", "qualitätskontrolle", "abgenommen"],
                "durchschnittsdauer_tage": 7,
                "sla_stunden": 168
            },
            "verkauf": {
                "beschreibung": "Vermarktung und Verkauf",
                "status_optionen": ["inseriert", "interessenten", "probefahrt", "verkauft"],
                "durchschnittsdauer_tage": 30,
                "sla_stunden": 720
            }
        }
        
        return {
            "prozesse": prozesse,
            "anzahl": len(prozesse),
            "gesamtdurchlauf_tage": sum(p["durchschnittsdauer_tage"] for p in prozesse.values())
        }
    
    @staticmethod
    def get_bearbeiter_info() -> Dict[str, Any]:
        """Info über alle Bearbeiter"""
        bearbeiter = {
            "Thomas Küfner": {"bereich": "Einkauf", "kuerzel": "TK"},
            "Maximilian Reinhardt": {"bereich": "Management", "kuerzel": "MR"},
            "Hans Müller": {"bereich": "Aufbereitung", "kuerzel": "HM"},
            "Anna Klein": {"bereich": "Foto", "kuerzel": "AK"},
            "Thomas Weber": {"bereich": "Werkstatt", "kuerzel": "TW"},
            "Stefan Bauer": {"bereich": "Verkauf", "kuerzel": "SB"}
        }
        
        return {
            "bearbeiter": bearbeiter,
            "anzahl": len(bearbeiter)
        }
    
    @staticmethod
    def get_system_config() -> Dict[str, Any]:
        """System-Konfiguration und Einstellungen"""
        return {
            "version": "2.0.0",
            "architektur": "modular_mit_zentraler_bigquery_service",
            "services": ["BigQueryService", "VehicleService", "DashboardService", "ProcessService", "InfoService"],
            "datenbank_struktur": {
                "fahrzeuge_stamm": "Stammdaten (marke, modell, farbe, etc.)",
                "fahrzeug_prozesse": "Prozess-Tracking (status, bearbeiter, SLA, etc.)"
            },
            "integrationen": [
                {"name": "Zapier", "endpoint": "/integration/zapier/webhook", "status": "aktiv"},
                {"name": "Flowers Email", "endpoint": "/integration/email/webhook", "status": "aktiv"}
            ]
        }