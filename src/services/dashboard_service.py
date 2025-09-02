# src/services/dashboard_service.py - Analytics Layer mit BigQueryService
"""Dashboard Service für KPIs und Statistiken - nutzt zentrale BigQueryService"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from src.services.bigquery_service import BigQueryService

logger = logging.getLogger(__name__)

class DashboardService:
    """Dashboard-Service für Analytics und KPIs"""
    
    def __init__(self, bq_service: Optional[BigQueryService] = None):
        self.bq_service = bq_service or BigQueryService()
    
    async def get_kpis(self) -> Dict[str, Any]:
        """Haupt-KPIs für das Dashboard abrufen"""
        try:
            # Zentrale KPIs über BigQueryService
            kpis = await self.bq_service.get_dashboard_kpis()
            
            # Zusätzliche Dashboard-Logik
            if kpis.get("status") == "live_data":
                # SLA-Ampel-Status berechnen
                sla_violations = kpis.get("sla_verletzungen", 0)
                kpis["sla_ampel"] = self._calculate_sla_ampel(sla_violations)
                
                # Auslastungs-Bewertung
                aktive_fahrzeuge = kpis.get("aktive_fahrzeuge", 0)
                kpis["auslastung_bewertung"] = self._calculate_auslastung(aktive_fahrzeuge)
            
            return {
                "kpis": kpis,
                "dashboard_status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Dashboard KPI Fehler: {e}")
            return {
                "kpis": self._get_fallback_kpis(),
                "dashboard_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_warteschlangen(self) -> Dict[str, Any]:
        """Warteschlangen-Status für alle Prozesse"""
        try:
            warteschlangen_data = await self.bq_service.get_warteschlangen_status()
            
            # Geschäftslogik: Zusammenfassung und Bewertung
            if warteschlangen_data.get("status") == "live_data":
                warteschlangen = warteschlangen_data.get("warteschlangen", {})
                
                # Gesamtanzahl wartender Fahrzeuge berechnen
                total_wartend = 0
                total_in_bearbeitung = 0
                
                for prozess_typ, status_data in warteschlangen.items():
                    warteschlange_count = status_data.get("warteschlange", {}).get("anzahl", 0)
                    bearbeitung_count = status_data.get("in_bearbeitung", {}).get("anzahl", 0)
                    
                    total_wartend += warteschlange_count
                    total_in_bearbeitung += bearbeitung_count
                
                # Kapazitäts-Bewertung hinzufügen
                warteschlangen_data["zusammenfassung"] = {
                    "total_wartend": total_wartend,
                    "total_in_bearbeitung": total_in_bearbeitung,
                    "kapazitaets_status": self._calculate_capacity_status(total_wartend, total_in_bearbeitung)
                }
            
            return warteschlangen_data
            
        except Exception as e:
            logger.error(f"Warteschlangen Fehler: {e}")
            return {
                "warteschlangen": {},
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_sla_overview(self) -> Dict[str, Any]:
        """SLA-Übersicht und kritische Fälle"""
        try:
            # Würde eine spezielle SLA-Query über BigQueryService machen
            # Hier vereinfacht als Beispiel
            fahrzeuge = await self.bq_service.get_fahrzeuge_mit_prozessen(limit=100)
            
            sla_critical = []
            sla_warning = []
            sla_ok = []
            
            for fahrzeug in fahrzeuge:
                tage_bis_deadline = fahrzeug.get("tage_bis_sla_deadline")
                if tage_bis_deadline is not None:
                    if tage_bis_deadline < 0:
                        sla_critical.append(fahrzeug)
                    elif tage_bis_deadline <= 1:
                        sla_warning.append(fahrzeug)
                    else:
                        sla_ok.append(fahrzeug)
            
            return {
                "sla_overview": {
                    "critical": {
                        "anzahl": len(sla_critical),
                        "fahrzeuge": sla_critical[:5]  # Top 5 kritische
                    },
                    "warning": {
                        "anzahl": len(sla_warning),
                        "fahrzeuge": sla_warning[:5]  # Top 5 Warnung
                    },
                    "ok": {
                        "anzahl": len(sla_ok)
                    }
                },
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"SLA-Übersicht Fehler: {e}")
            return {
                "sla_overview": {},
                "status": "error",
                "error": str(e)
            }
    
    async def get_bearbeiter_workload(self) -> Dict[str, Any]:
        """Arbeitsbelastung pro Bearbeiter"""
        try:
            fahrzeuge = await self.bq_service.get_fahrzeuge_mit_prozessen(limit=200)
            
            bearbeiter_stats = {}
            
            for fahrzeug in fahrzeuge:
                bearbeiter = fahrzeug.get("bearbeiter")
                if bearbeiter:
                    if bearbeiter not in bearbeiter_stats:
                        bearbeiter_stats[bearbeiter] = {
                            "aktive_prozesse": 0,
                            "warteschlange": 0,
                            "sla_critical": 0,
                            "avg_standzeit": 0,
                            "prozesse": []
                        }
                    
                    stats = bearbeiter_stats[bearbeiter]
                    status = fahrzeug.get("status")
                    
                    if status == "in_bearbeitung":
                        stats["aktive_prozesse"] += 1
                    elif status == "warteschlange":
                        stats["warteschlange"] += 1
                    
                    if fahrzeug.get("tage_bis_sla_deadline", 0) < 0:
                        stats["sla_critical"] += 1
                    
                    stats["prozesse"].append(fahrzeug)
            
            # Durchschnittliche Standzeit berechnen
            for bearbeiter, stats in bearbeiter_stats.items():
                if stats["prozesse"]:
                    standzeiten = [p.get("standzeit_tage", 0) for p in stats["prozesse"] if p.get("standzeit_tage")]
                    stats["avg_standzeit"] = round(sum(standzeiten) / len(standzeiten), 1) if standzeiten else 0
                    # Prozesse-Liste für Übersicht entfernen (zu viele Daten)
                    del stats["prozesse"]
            
            return {
                "bearbeiter_workload": bearbeiter_stats,
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Bearbeiter Workload Fehler: {e}")
            return {
                "bearbeiter_workload": {},
                "status": "error",
                "error": str(e)
            }
    
    # ========================================
    # UTILITY Methoden für Geschäftslogik
    # ========================================
    
    def _calculate_sla_ampel(self, sla_violations: int) -> str:
        """SLA-Ampel-Status berechnen"""
        if sla_violations == 0:
            return "grün"
        elif sla_violations <= 3:
            return "gelb"
        else:
            return "rot"
    
    def _calculate_auslastung(self, aktive_fahrzeuge: int) -> str:
        """Auslastungs-Bewertung berechnen"""
        # Diese Werte könnten konfigurierbar sein
        if aktive_fahrzeuge < 20:
            return "niedrig"
        elif aktive_fahrzeuge <= 50:
            return "normal"
        elif aktive_fahrzeuge <= 80:
            return "hoch"
        else:
            return "überlastet"
    
    def _calculate_capacity_status(self, wartend: int, in_bearbeitung: int) -> str:
        """Kapazitäts-Status der Warteschlangen"""
        total = wartend + in_bearbeitung
        
        if total < 10:
            return "entspannt"
        elif total <= 25:
            return "normal"
        elif total <= 50:
            return "ausgelastet"
        else:
            return "überlastet"
    
    def _get_fallback_kpis(self) -> Dict[str, Any]:
        """Fallback KPIs wenn BigQuery nicht verfügbar"""
        return {
            "aktive_fahrzeuge": 42,
            "heute_gestartet": 3,
            "sla_verletzungen": 2,
            "avg_standzeit": 15.5,
            "anzahl_marken": 8,
            "anzahl_bearbeiter": 6,
            "sla_ampel": "gelb",
            "auslastung_bewertung": "normal",
            "status": "fallback_data"
        }