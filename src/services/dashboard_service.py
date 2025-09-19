# src/services/dashboard_service.py
"""
Dashboard Service für KPIs, Statistiken und Analytics
Orchestriert Dashboard-Daten über BigQueryService
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.services.bigquery_service import BigQueryService

logger = logging.getLogger(__name__)

class DashboardService:
    """Service für Dashboard-KPIs und Analytics - orchestriert BigQuery-Abfragen"""
    
    def __init__(self, bigquery_service: BigQueryService):
        self.bq = bigquery_service
        logger.info("✅ DashboardService initialisiert")
    
    async def get_kpis(self) -> Dict[str, Any]:
        """
        Haupt-KPIs für Executive Dashboard
        
        Returns:
            Dict mit wichtigsten KPIs
        """
        try:
            # Delegiere an BigQueryService
            prozess_stats = await self.bq.get_dashboard_prozess_stats()
            sla_stats = await self.bq.get_dashboard_sla_stats()
            durchlauf_stats = await self.bq.get_dashboard_durchlaufzeiten()
            
            # Daten aufbereiten und strukturieren
            kpis = {
                "timestamp": datetime.now().isoformat(),
                "fahrzeuge": {
                    "gesamt": prozess_stats[0]["fahrzeuge_gesamt"] if prozess_stats else 0,
                    "aktiv": prozess_stats[0]["fahrzeuge_aktiv"] if prozess_stats else 0,
                    "verkaufsbereit": prozess_stats[0]["verkaufsbereit"] if prozess_stats else 0
                },
                "prozesse": {
                    "in_aufbereitung": prozess_stats[0]["in_aufbereitung"] if prozess_stats else 0,
                    "in_werkstatt": prozess_stats[0]["in_werkstatt"] if prozess_stats else 0,
                    "in_foto": prozess_stats[0]["in_foto"] if prozess_stats else 0
                },
                "sla": {
                    "ueberfaellig": sla_stats[0]["sla_ueberfaellig"] if sla_stats else 0,
                    "kritisch": sla_stats[0]["sla_kritisch"] if sla_stats else 0,
                    "warnung": sla_stats[0]["sla_warnung"] if sla_stats else 0,
                    "avg_prozessdauer_stunden": round(sla_stats[0]["avg_prozessdauer_stunden"] or 0, 2) if sla_stats else 0
                },
                "durchlaufzeiten": self._format_durchlaufzeiten(durchlauf_stats)
            }
            
            logger.info(f"📊 KPIs abgerufen: {kpis['fahrzeuge']['aktiv']} aktive Fahrzeuge")
            return kpis
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Abrufen der KPIs: {e}")
            return self._get_mock_kpis()
    
    async def get_warteschlangen(self) -> Dict[str, List[Dict]]:
        """
        Warteschlangen-Status für alle Prozesse
        
        Returns:
            Dict mit Warteschlangen pro Prozess
        """
        try:
            # Rohdaten von BigQueryService holen
            results = await self.bq.get_warteschlangen_detail()
            
            # Nach Prozesstyp gruppieren und formatieren
            warteschlangen = {
                "Einkauf": [],
                "Anlieferung": [],
                "Aufbereitung": [],
                "Foto": [],
                "Werkstatt": [],
                "Verkauf": []
            }
            
            for row in results:
                prozess_typ = row.get("prozess_typ")
                if prozess_typ in warteschlangen:
                    warteschlangen[prozess_typ].append({
                        "fin": row.get("fin"),
                        "fahrzeug": f"{row.get('marke', '')} {row.get('modell', '')} ({row.get('baujahr', '')})",
                        "status": row.get("status"),
                        "bearbeiter": row.get("bearbeiter"),
                        "prioritaet": row.get("prioritaet"),
                        "wartend_seit_stunden": row.get("wartend_seit_stunden", 0),
                        "sla_status": self._get_sla_status(row.get("tage_bis_sla_deadline", 999))
                    })
            
            logger.info(f"📊 Warteschlangen abgerufen für {len(warteschlangen)} Prozesse")
            return warteschlangen
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Abrufen der Warteschlangen: {e}")
            return self._get_mock_warteschlangen()
    
    async def get_sla_overview(self) -> Dict[str, Any]:
        """
        SLA-Übersicht mit kritischen Fahrzeugen
        
        Returns:
            Dict mit SLA-Statistiken
        """
        try:
            # Rohdaten von BigQueryService
            results = await self.bq.get_sla_critical_vehicles()
            
            # Kategorisieren und aufbereiten
            sla_overview = {
                "überfällig": [],
                "kritisch": [],
                "warnung": [],
                "statistik": {
                    "gesamt": len(results),
                    "überfällig": 0,
                    "kritisch": 0,
                    "warnung": 0,
                    "ok": 0
                }
            }
            
            for row in results:
                kategorie = row.get("sla_kategorie", "ok")
                sla_overview["statistik"][kategorie] += 1
                
                if kategorie in ["überfällig", "kritisch", "warnung"]:
                    sla_overview[kategorie].append({
                        "fin": row.get("fin"),
                        "fahrzeug": f"{row.get('marke', '')} {row.get('modell', '')}",
                        "prozess": row.get("prozess_typ"),
                        "bearbeiter": row.get("bearbeiter"),
                        "tage_bis_deadline": row.get("tage_bis_sla_deadline"),
                        "ek_netto": row.get("ek_netto")
                    })
            
            logger.info(f"📊 SLA-Overview: {sla_overview['statistik']['überfällig']} überfällige Prozesse")
            return sla_overview
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Abrufen der SLA-Overview: {e}")
            return self._get_mock_sla_overview()
    
    async def get_bearbeiter_workload(self) -> List[Dict[str, Any]]:
        """
        Workload-Übersicht pro Bearbeiter
        
        Returns:
            Liste mit Bearbeiter-Statistiken
        """
        try:
            # Rohdaten von BigQueryService
            results = await self.bq.get_bearbeiter_workload_stats()
            
            # Aufbereiten und Auslastung berechnen
            workload = []
            for row in results:
                workload.append({
                    "bearbeiter": row.get("bearbeiter"),
                    "fahrzeuge": row.get("fahrzeuge_anzahl", 0),
                    "prozesse": row.get("prozesse_anzahl", 0),
                    "avg_alter_stunden": round(row.get("avg_alter_stunden", 0), 1),
                    "kritischster_sla_tage": row.get("kritischster_sla"),
                    "prozess_typen": row.get("prozess_typen", "").split(",") if row.get("prozess_typen") else [],
                    "auslastung": self._calculate_auslastung(row.get("prozesse_anzahl", 0))
                })
            
            logger.info(f"📊 Workload für {len(workload)} Bearbeiter abgerufen")
            return workload
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Abrufen der Bearbeiter-Workload: {e}")
            return self._get_mock_workload()
    
    # Hilfsfunktionen bleiben unverändert
    # ... rest of the helper methods ...
    
    # Hilfsfunktionen
    def _format_durchlaufzeiten(self, stats: List[Dict]) -> Dict[str, Dict]:
        """Formatiere Durchlaufzeiten-Statistiken"""
        result = {}
        for stat in stats:
            prozess = stat.get("prozess_typ", "Unbekannt")
            result[prozess] = {
                "avg": round(stat.get("avg_dauer_stunden", 0), 1),
                "min": round(stat.get("min_dauer_stunden", 0), 1),
                "max": round(stat.get("max_dauer_stunden", 0), 1)
            }
        return result
    
    def _get_sla_status(self, tage_bis_deadline: Optional[int]) -> str:
        """Bestimme SLA-Status basierend auf Tagen bis Deadline"""
        if tage_bis_deadline is None:
            return "unbekannt"
        if tage_bis_deadline < 0:
            return "überfällig"
        if tage_bis_deadline <= 1:
            return "kritisch"
        if tage_bis_deadline <= 3:
            return "warnung"
        return "ok"
    
    def _calculate_auslastung(self, prozesse: int) -> str:
        """Berechne Auslastung basierend auf Anzahl Prozesse"""
        if prozesse <= 3:
            return "niedrig"
        if prozesse <= 7:
            return "mittel"
        if prozesse <= 12:
            return "hoch"
        return "überlastet"
    
    # Mock-Daten für Entwicklung
    def _get_mock_kpis(self) -> Dict[str, Any]:
        """Mock-KPIs für Entwicklung"""
        return {
            "timestamp": datetime.now().isoformat(),
            "fahrzeuge": {
                "gesamt": 45,
                "aktiv": 28,
                "verkaufsbereit": 12
            },
            "prozesse": {
                "in_aufbereitung": 8,
                "in_werkstatt": 5,
                "in_foto": 3
            },
            "sla": {
                "ueberfaellig": 2,
                "kritisch": 3,
                "warnung": 5,
                "avg_prozessdauer_stunden": 48.5
            },
            "durchlaufzeiten": {
                "Aufbereitung": {"avg": 72, "min": 24, "max": 168},
                "Werkstatt": {"avg": 96, "min": 48, "max": 240},
                "Foto": {"avg": 24, "min": 8, "max": 48}
            }
        }
    
    def _get_mock_warteschlangen(self) -> Dict[str, List[Dict]]:
        """Mock-Warteschlangen für Entwicklung"""
        return {
            "Aufbereitung": [
                {
                    "fin": "WAUZZZGE1NB038655",
                    "fahrzeug": "Audi A4 (2022)",
                    "status": "wartend",
                    "bearbeiter": "Thomas Küfner",
                    "prioritaet": 2,
                    "wartend_seit_stunden": 12,
                    "sla_status": "warnung"
                }
            ],
            "Werkstatt": [],
            "Foto": [],
            "Einkauf": [],
            "Anlieferung": [],
            "Verkauf": []
        }
    
    def _get_mock_sla_overview(self) -> Dict[str, Any]:
        """Mock-SLA-Overview für Entwicklung"""
        return {
            "überfällig": [
                {
                    "fin": "WAUZZZGE1NB038655",
                    "fahrzeug": "Audi A4",
                    "prozess": "Aufbereitung",
                    "bearbeiter": "Thomas Küfner",
                    "tage_bis_deadline": -2,
                    "ek_netto": 25000
                }
            ],
            "kritisch": [],
            "warnung": [],
            "statistik": {
                "gesamt": 28,
                "überfällig": 1,
                "kritisch": 2,
                "warnung": 3,
                "ok": 22
            }
        }
    
    def _get_mock_workload(self) -> List[Dict[str, Any]]:
        """Mock-Workload für Entwicklung"""
        return [
            {
                "bearbeiter": "Thomas Küfner",
                "fahrzeuge": 8,
                "prozesse": 12,
                "avg_alter_stunden": 36.5,
                "kritischster_sla_tage": -1,
                "prozess_typen": ["Aufbereitung", "Foto"],
                "auslastung": "hoch"
            },
            {
                "bearbeiter": "Maximilian Reinhardt",
                "fahrzeuge": 5,
                "prozesse": 7,
                "avg_alter_stunden": 24.2,
                "kritischster_sla_tage": 2,
                "prozess_typen": ["Verkauf", "Einkauf"],
                "auslastung": "mittel"
            }
        ]