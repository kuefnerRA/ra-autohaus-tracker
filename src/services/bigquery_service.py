# src/services/bigquery_service.py
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.cloud import bigquery

logger = logging.getLogger(__name__)


class BigQueryService:
    def __init__(self):
        try:
            self.client = bigquery.Client()
            self.project_id = (os.getenv("PROJECT_ID") or os.getenv("GCP_PROJECT_ID") or "ra-autohaus-tracker")
            self.dataset_id = "autohaus"
            logger.info("✅ BigQuery Service initialized")
        except Exception as e:
            logger.error(f"❌ BigQuery initialization failed: {e}")
            self.client = None

    async def health_check(self) -> bool:
        """BigQuery Verbindung prüfen"""
        if not self.client:
            return False
        try:
            # Einfache Query zum Testen
            query = "SELECT 1 as test"
            result = self.client.query(query)
            list(result)  # Query ausführen
            return True
        except Exception as e:
            logger.error(f"BigQuery health check failed: {e}")
            return False

    async def create_vehicle(self, vehicle_data: Dict[str, Any]) -> bool:
        """Fahrzeug in BigQuery speichern"""
        if not self.client:
            return False
        try:
            table_id = f"{self.project_id}.{self.dataset_id}.fahrzeuge_stamm"
            table = self.client.get_table(table_id)

            row = {
                "fin": vehicle_data["fin"],
                "marke": vehicle_data["marke"],
                "modell": vehicle_data["modell"],
                "antriebsart": vehicle_data["antriebsart"],
                "farbe": vehicle_data["farbe"],
                "baujahr": vehicle_data.get("baujahr"),
                "ersterfassung_datum": datetime.now().isoformat(),
                "aktiv": True,
            }

            errors = self.client.insert_rows_json(table, [row])
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
                return False

            logger.info(f"✅ Vehicle created in BigQuery: {vehicle_data['fin']}")
            return True
        except Exception as e:
            logger.error(f"❌ BigQuery vehicle creation failed: {e}")
            return False

    async def create_process(self, process_data: Dict[str, Any]) -> bool:
        """Prozess in BigQuery speichern"""
        if not self.client:
            return False
        try:
            table_id = f"{self.project_id}.{self.dataset_id}.fahrzeug_prozesse"
            table = self.client.get_table(table_id)

            row = {
                "prozess_id": process_data["prozess_id"],
                "fin": process_data["fin"],
                "prozess_typ": process_data["prozess_typ"],
                "status": process_data["status"],
                "bearbeiter": process_data.get("bearbeiter"),
                "prioritaet": process_data.get("prioritaet", 5),
                "anlieferung_datum": process_data.get("anlieferung_datum"),
                "start_timestamp": (
                    process_data["start_timestamp"].isoformat()
                    if isinstance(process_data.get("start_timestamp"), datetime)
                    else process_data.get("start_timestamp")
                ),
                "datenquelle": process_data.get("datenquelle", "api"),
                "notizen": process_data.get("notizen"),
            }

            # None-Werte entfernen
            row = {k: v for k, v in row.items() if v is not None}

            errors = self.client.insert_rows_json(table, [row])
            if errors:
                logger.error(f"BigQuery process insert errors: {errors}")
                return False

            logger.info(f"✅ Process created in BigQuery: {process_data['prozess_id']}")
            return True
        except Exception as e:
            logger.error(f"❌ BigQuery process creation failed: {e}")
            return False

    async def get_vehicle_with_processes(self, fin: str) -> Optional[Dict]:
        """Fahrzeug mit allen Prozessen abrufen"""
        if not self.client:
            return None
        try:
            query = f"""
            SELECT
                v.*,
                ARRAY_AGG(
                    STRUCT(
                        p.prozess_id,
                        p.prozess_typ,
                        p.status,
                        p.bearbeiter,
                        p.start_timestamp,
                        p.ende_timestamp
                    )
                ) as prozesse
            FROM `{self.project_id}.{self.dataset_id}.fahrzeuge_stamm` v
            LEFT JOIN `{self.project_id}.{self.dataset_id}.fahrzeug_prozesse` p
                ON v.fin = p.fin
            WHERE v.fin = @fin
            GROUP BY v.fin, v.marke, v.modell, v.antriebsart, v.farbe, v.baujahr, v.ersterfassung_datum, v.aktiv
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("fin", "STRING", fin)]
            )

            result = self.client.query(query, job_config=job_config)
            vehicles = [dict(row) for row in result]

            return vehicles[0] if vehicles else None
        except Exception as e:
            logger.error(f"❌ Vehicle query failed: {e}")
            return None

    async def get_current_queues(self) -> Dict[str, Any]:
        """Aktuelle Warteschlangen abrufen"""
        if not self.client:
            return {"warteschlangen": [], "source": "bigquery_unavailable"}
        try:
            query = f"""
            SELECT
                prozess_typ,
                COUNT(*) as anzahl_wartend,
                AVG(prioritaet) as avg_prioritaet
            FROM `{self.project_id}.{self.dataset_id}.fahrzeug_prozesse`
            WHERE status = 'warteschlange'
            GROUP BY prozess_typ
            ORDER BY anzahl_wartend DESC
            """

            result = self.client.query(query)
            queues = [dict(row) for row in result]

            return {"warteschlangen": queues, "source": "bigquery"}
        except Exception as e:
            logger.error(f"❌ Queue query failed: {e}")
            return {"warteschlangen": [], "source": "bigquery_error"}

    async def get_dashboard_kpis(self) -> Dict[str, Any]:
        """Dashboard KPIs abrufen"""
        if not self.client:
            return {"kpis": {}, "source": "bigquery_unavailable"}
        try:
            # Verschiedene KPI-Queries
            queries = {
                "total_vehicles": f"SELECT COUNT(*) as count FROM `{self.project_id}.{self.dataset_id}.fahrzeuge_stamm`",
                "total_processes": f"SELECT COUNT(*) as count FROM `{self.project_id}.{self.dataset_id}.fahrzeug_prozesse`",
                "active_processes": f"SELECT COUNT(*) as count FROM `{self.project_id}.{self.dataset_id}.fahrzeug_prozesse` WHERE status IN ('gestartet', 'in_bearbeitung', 'warteschlange')",
            }

            kpis = {}
            for kpi_name, query in queries.items():
                result = self.client.query(query)
                rows = list(result)
                kpis[kpi_name] = rows[0]["count"] if rows else 0

            return {
                "kpis": kpis,
                "timestamp": datetime.now().isoformat(),
                "source": "bigquery",
            }
        except Exception as e:
            logger.error(f"❌ KPI query failed: {e}")
            return {"kpis": {}, "source": "bigquery_error"}

    async def get_sla_alerts(self) -> List[Dict[str, Any]]:
        """SLA-Verletzungen abrufen"""
        if not self.client:
            return []
        try:
            # Vereinfachte SLA-Query für jetzt
            query = f"""
            SELECT
                fin,
                prozess_typ,
                status,
                bearbeiter,
                DATE_DIFF(CURRENT_DATE(), DATE(start_timestamp), DAY) as tage_laufend
            FROM `{self.project_id}.{self.dataset_id}.fahrzeug_prozesse`
            WHERE status IN ('gestartet', 'in_bearbeitung', 'warteschlange')
            AND start_timestamp IS NOT NULL
            AND (
                (prozess_typ = 'Transport' AND DATE_DIFF(CURRENT_DATE(), DATE(start_timestamp), DAY) > 7) OR
                (prozess_typ = 'Aufbereitung' AND DATE_DIFF(CURRENT_DATE(), DATE(start_timestamp), DAY) > 2) OR
                (prozess_typ = 'Werkstatt' AND DATE_DIFF(CURRENT_DATE(), DATE(start_timestamp), DAY) > 10) OR
                (prozess_typ = 'Foto' AND DATE_DIFF(CURRENT_DATE(), DATE(start_timestamp), DAY) > 3)
            )
            ORDER BY tage_laufend DESC
            """

            result = self.client.query(query)
            alerts = [dict(row) for row in result]

            return alerts
        except Exception as e:
            logger.error(f"❌ SLA alerts query failed: {e}")
            return []
