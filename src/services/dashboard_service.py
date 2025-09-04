# src/services/dashboard_service.py
"""
Dashboard Service für KPIs, Statistiken und Analytics
Verantwortlich für alle Dashboard-bezogenen Daten und Metriken
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from src.services.bigquery_service import BigQueryService

logger = logging.getLogger(__name__)

class DashboardService:
    """Service für Dashboard-KPIs und Analytics"""
    
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
            # Aktuelle Prozesse zählen
            aktive_prozesse_query = """
            SELECT 
                COUNT(DISTINCT fin) as fahrzeuge_gesamt,
                COUNT(DISTINCT CASE WHEN status != 'abgeschlossen' THEN fin END) as fahrzeuge_aktiv,
                COUNT(DISTINCT CASE WHEN prozess_typ = 'Aufbereitung' AND status != 'abgeschlossen' THEN fin END) as in_aufbereitung,
                COUNT(DISTINCT CASE WHEN prozess_typ = 'Werkstatt' AND status != 'abgeschlossen' THEN fin END) as in_werkstatt,
                COUNT(DISTINCT CASE WHEN prozess_typ = 'Foto' AND status != 'abgeschlossen' THEN fin END) as in_foto,
                COUNT(DISTINCT CASE WHEN prozess_typ = 'Verkauf' AND status = 'verfügbar' THEN fin END) as verkaufsbereit
            FROM fahrzeug_prozesse
            WHERE DATE(erstellt_am) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
            """
            
            # SLA-Status
            sla_query = """
            SELECT
                COUNT(CASE WHEN tage_bis_sla_deadline < 0 THEN 1 END) as sla_ueberfaellig,
                COUNT(CASE WHEN tage_bis_sla_deadline BETWEEN 0 AND 1 THEN 1 END) as sla_kritisch,
                COUNT(CASE WHEN tage_bis_sla_deadline BETWEEN 2 AND 3 THEN 1 END) as sla_warnung,
                AVG(dauer_minuten) / 60 as avg_prozessdauer_stunden
            FROM fahrzeug_prozesse
            WHERE status != 'abgeschlossen' 
            AND ende_timestamp IS NULL
            """
            
            # Durchlaufzeiten
            durchlauf_query = """
            SELECT 
                prozess_typ,
                AVG(DATETIME_DIFF(ende_timestamp, start_timestamp, HOUR)) as avg_dauer_stunden,
                MIN(DATETIME_DIFF(ende_timestamp, start_timestamp, HOUR)) as min_dauer_stunden,
                MAX(DATETIME_DIFF(ende_timestamp, start_timestamp, HOUR)) as max_dauer_stunden
            FROM fahrzeug_prozesse
            WHERE ende_timestamp IS NOT NULL
            AND start_timestamp IS NOT NULL
            GROUP BY prozess_typ
            """
            
            # Queries ausführen
            prozess_stats = await self.bq.execute_query(aktive_prozesse_query)
            sla_stats = await self.bq.execute_query(sla_query)
            durchlauf_stats = await self.bq.execute_query(durchlauf_query)
            
            # KPIs zusammenstellen
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
            # Fallback mit Mock-Daten
            return self._get_mock_kpis()
    
    async def get_warteschlangen(self) -> Dict[str, List[Dict]]:
        """
        Warteschlangen-Status für alle Prozesse
        
        Returns:
            Dict mit Warteschlangen pro Prozess
        """
        try:
            query = """
            SELECT 
                p.prozess_typ,
                p.fin,
                p.status,
                p.bearbeiter,
                p.prioritaet,
                p.start_timestamp,
                p.sla_deadline_datum,
                p.tage_bis_sla_deadline,
                f.marke,
                f.modell,
                f.baujahr,
                DATETIME_DIFF(CURRENT_DATETIME(), p.start_timestamp, HOUR) as wartend_seit_stunden
            FROM fahrzeug_prozesse p
            LEFT JOIN fahrzeuge_stamm f ON p.fin = f.fin
            WHERE p.status IN ('wartend', 'in_bearbeitung', 'pausiert')
            AND p.ende_timestamp IS NULL
            ORDER BY p.prioritaet ASC, p.start_timestamp ASC
            """
            
            results = await self.bq.execute_query(query)
            
            # Nach Prozesstyp gruppieren
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
            query = """
            SELECT 
                p.fin,
                p.prozess_typ,
                p.status,
                p.bearbeiter,
                p.sla_deadline_datum,
                p.tage_bis_sla_deadline,
                f.marke,
                f.modell,
                f.ek_netto,
                CASE 
                    WHEN p.tage_bis_sla_deadline < 0 THEN 'überfällig'
                    WHEN p.tage_bis_sla_deadline <= 1 THEN 'kritisch'
                    WHEN p.tage_bis_sla_deadline <= 3 THEN 'warnung'
                    ELSE 'ok'
                END as sla_kategorie
            FROM fahrzeug_prozesse p
            LEFT JOIN fahrzeuge_stamm f ON p.fin = f.fin
            WHERE p.ende_timestamp IS NULL
            ORDER BY p.tage_bis_sla_deadline ASC
            """
            
            results = await self.bq.execute_query(query)
            
            # Kategorisieren
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
            query = """
            SELECT 
                bearbeiter,
                COUNT(DISTINCT fin) as fahrzeuge_anzahl,
                COUNT(DISTINCT prozess_id) as prozesse_anzahl,
                AVG(DATETIME_DIFF(CURRENT_DATETIME(), start_timestamp, HOUR)) as avg_alter_stunden,
                MIN(tage_bis_sla_deadline) as kritischster_sla,
                STRING_AGG(DISTINCT prozess_typ) as prozess_typen
            FROM fahrzeug_prozesse
            WHERE ende_timestamp IS NULL
            AND bearbeiter IS NOT NULL
            GROUP BY bearbeiter
            ORDER BY fahrzeuge_anzahl DESC
            """
            
            results = await self.bq.execute_query(query)
            
            workload = []
            for row in results:
                workload.append({
                    "bearbeiter": row.get("bearbeiter"),
                    "fahrzeuge": row.get("fahrzeuge_anzahl", 0),
                    "prozesse": row.get("prozesse_anzahl", 0),
                    "avg_alter_stunden": round(row.get("avg_alter_stunden", 0), 1),
                    "kritischster_sla_tage": row.get("kritischster_sla"),
                    "prozess_typen": row.get("prozess_typen", "").split(","),
                    "auslastung": self._calculate_auslastung(row.get("prozesse_anzahl", 0))
                })
            
            logger.info(f"📊 Workload für {len(workload)} Bearbeiter abgerufen")
            return workload
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Abrufen der Bearbeiter-Workload: {e}")
            return self._get_mock_workload()
    
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