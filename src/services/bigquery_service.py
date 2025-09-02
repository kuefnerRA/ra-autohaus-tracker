# src/services/bigquery_service.py - Zentrale Data Layer für normalisierte Tabellen
"""BigQuery Service - Zentrale Datenschicht für alle Tabellen-Operationen"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from google.cloud import bigquery

logger = logging.getLogger(__name__)

class BigQueryService:
    """Zentrale BigQuery-Datenschicht für alle Services"""
    
    def __init__(self):
        self.project_id = "ra-autohaus-tracker"
        self.dataset_id = "autohaus"
        self.client: Optional[bigquery.Client] = None
        
        try:
            self.client = bigquery.Client(project=self.project_id)
            logger.info("✅ BigQuery Client erfolgreich initialisiert")
        except Exception as e:
            logger.error(f"❌ BigQuery Client-Initialisierung fehlgeschlagen: {e}")
            self.client = None
    
    async def health_check(self) -> bool:
        """Health Check für BigQuery-Verbindung"""
        if not self.client:
            return False
            
        try:
            query = "SELECT 1 as test_connection"
            job = self.client.query(query)
            list(job.result())
            return True
        except Exception as e:
            logger.error(f"BigQuery Health Check fehlgeschlagen: {e}")
            return False
    
    # ========================================
    # FAHRZEUGE_STAMM Operationen (Stammdaten)
    # ========================================
    
    async def create_fahrzeug_stamm(self, vehicle_data: Dict[str, Any]) -> bool:
        """Fahrzeug-Stammdaten in fahrzeuge_stamm erstellen"""
        if not self.client:
            logger.warning("BigQuery nicht verfügbar - Mock-Modus")
            return True
            
        try:
            if 'fin' not in vehicle_data:
                raise ValueError("FIN ist erforderlich für Fahrzeug-Erstellung")
            
            table_ref = self.client.dataset(self.dataset_id).table("fahrzeuge_stamm")
            table = self.client.get_table(table_ref)
            
            # Daten für BigQuery vorbereiten
            prepared_data = self._prepare_stamm_data(vehicle_data)
            
            errors = self.client.insert_rows_json(table, [prepared_data])
            if errors:
                logger.error(f"BigQuery Einfüge-Fehler fahrzeuge_stamm: {errors}")
                return False
            
            logger.info(f"✅ Fahrzeug-Stammdaten erstellt: {vehicle_data['fin']}")
            return True
            
        except Exception as e:
            logger.error(f"Fahrzeug-Stammdaten erstellen Fehler: {e}")
            return False
    
    async def get_fahrzeug_stamm(self, fin: str) -> Optional[Dict[str, Any]]:
        """Fahrzeug-Stammdaten nach FIN abrufen"""
        if not self.client:
            return self._get_mock_fahrzeug_stamm(fin)
            
        try:
            query = """
            SELECT *
            FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
            WHERE fin = @fin AND aktiv = TRUE
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("fin", "STRING", fin)]
            )
            
            results = self.client.query(query, job_config=job_config).result()
            
            for row in results:
                return self._convert_row_to_dict(row)
                
            return None
            
        except Exception as e:
            logger.error(f"Fahrzeug-Stammdaten abrufen Fehler: {e}")
            return None
    
    async def update_fahrzeug_stamm(self, fin: str, update_data: Dict[str, Any]) -> bool:
        """Fahrzeug-Stammdaten aktualisieren"""
        if not self.client:
            logger.warning("BigQuery nicht verfügbar - Mock-Modus")
            return True
            
        try:
            # Valide Stammdaten-Felder
            stamm_fields = [
                'marke', 'modell', 'antriebsart', 'farbe', 'baujahr',
                'datum_erstzulassung', 'kw_leistung', 'km_stand',
                'anzahl_fahrzeugschluessel', 'bereifungsart',
                'anzahl_vorhalter', 'ek_netto', 'besteuerungsart'
            ]
            
            set_clauses = []
            parameters = []
            
            for key, value in update_data.items():
                if key in stamm_fields and value is not None:
                    set_clauses.append(f"{key} = @{key}")
                    parameters.append(self._create_query_parameter(key, value))
            
            if not set_clauses:
                logger.warning("Keine gültigen Stammdaten-Felder zu aktualisieren")
                return False
            
            parameters.append(bigquery.ScalarQueryParameter("fin", "STRING", fin))
            
            query = f"""
            UPDATE `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP()
            WHERE fin = @fin AND aktiv = TRUE
            """
            
            job_config = bigquery.QueryJobConfig(query_parameters=parameters)
            query_job = self.client.query(query, job_config=job_config)
            query_job.result()
            
            logger.info(f"✅ Fahrzeug-Stammdaten aktualisiert: {fin}")
            return True
            
        except Exception as e:
            logger.error(f"Fahrzeug-Stammdaten Update Fehler: {e}")
            return False
    
    # ==========================================
    # FAHRZEUG_PROZESSE Operationen (Prozesse)
    # ==========================================
    
    async def create_fahrzeug_prozess(self, process_data: Dict[str, Any]) -> bool:
        """Fahrzeug-Prozess in fahrzeug_prozesse erstellen"""
        if not self.client:
            logger.warning("BigQuery nicht verfügbar - Mock-Modus")
            return True
            
        try:
            required_fields = ['prozess_id', 'fin', 'prozess_typ', 'status']
            for field in required_fields:
                if field not in process_data:
                    raise ValueError(f"{field} ist erforderlich für Prozess-Erstellung")
            
            table_ref = self.client.dataset(self.dataset_id).table("fahrzeug_prozesse")
            table = self.client.get_table(table_ref)
            
            # Daten für BigQuery vorbereiten
            prepared_data = self._prepare_prozess_data(process_data)
            
            errors = self.client.insert_rows_json(table, [prepared_data])
            if errors:
                logger.error(f"BigQuery Einfüge-Fehler fahrzeug_prozesse: {errors}")
                return False
            
            logger.info(f"✅ Fahrzeug-Prozess erstellt: {process_data['prozess_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Fahrzeug-Prozess erstellen Fehler: {e}")
            return False
    
    async def get_fahrzeug_prozesse(self, fin: str) -> List[Dict[str, Any]]:
        """Alle Prozesse für ein Fahrzeug abrufen"""
        if not self.client:
            return self._get_mock_fahrzeug_prozesse(fin)
            
        try:
            query = """
            SELECT *
            FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE fin = @fin
            ORDER BY updated_at DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("fin", "STRING", fin)]
            )
            
            results = self.client.query(query, job_config=job_config).result()
            
            prozesse = []
            for row in results:
                prozesse.append(self._convert_row_to_dict(row))
                
            return prozesse
            
        except Exception as e:
            logger.error(f"Fahrzeug-Prozesse abrufen Fehler: {e}")
            return []
    
    async def update_fahrzeug_prozess(self, prozess_id: str, update_data: Dict[str, Any]) -> bool:
        """Fahrzeug-Prozess aktualisieren"""
        if not self.client:
            logger.warning("BigQuery nicht verfügbar - Mock-Modus")
            return True
            
        try:
            # Valide Prozess-Felder
            prozess_fields = [
                'status', 'bearbeiter', 'prioritaet', 'anlieferung_datum',
                'start_timestamp', 'ende_timestamp', 'dauer_minuten',
                'sla_tage', 'sla_deadline_datum', 'tage_bis_sla_deadline',
                'standzeit_tage', 'notizen'
            ]
            
            set_clauses = []
            parameters = []
            
            for key, value in update_data.items():
                if key in prozess_fields and value is not None:
                    set_clauses.append(f"{key} = @{key}")
                    parameters.append(self._create_query_parameter(key, value))
            
            if not set_clauses:
                logger.warning("Keine gültigen Prozess-Felder zu aktualisieren")
                return False
            
            parameters.append(bigquery.ScalarQueryParameter("prozess_id", "STRING", prozess_id))
            
            query = f"""
            UPDATE `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP()
            WHERE prozess_id = @prozess_id
            """
            
            job_config = bigquery.QueryJobConfig(query_parameters=parameters)
            query_job = self.client.query(query, job_config=job_config)
            query_job.result()
            
            logger.info(f"✅ Fahrzeug-Prozess aktualisiert: {prozess_id}")
            return True
            
        except Exception as e:
            logger.error(f"Fahrzeug-Prozess Update Fehler: {e}")
            return False
    
    # ========================================
    # JOIN-Operationen (Business Queries)
    # ========================================
    
    async def get_fahrzeuge_mit_prozessen(
        self, 
        status_filter: Optional[str] = None,
        prozess_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fahrzeuge mit aktuellen Prozessen (JOIN Query)"""
        if not self.client:
            return self._get_mock_fahrzeuge_mit_prozessen()
            
        try:
            where_conditions = ["1=1"]
            
            if status_filter:
                where_conditions.append(f"p.status = '{status_filter}'")
            if prozess_filter:
                where_conditions.append(f"p.prozess_typ = '{prozess_filter}'")
                
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
            SELECT 
              p.fin,
              s.marke,
              s.modell,
              s.antriebsart,
              s.farbe,
              s.baujahr,
              p.prozess_id,
              p.prozess_typ,
              p.status,
              p.bearbeiter,
              p.prioritaet,
              p.standzeit_tage,
              p.tage_bis_sla_deadline,
              p.created_at,
              p.updated_at
            FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` p
            LEFT JOIN `ra-autohaus-tracker.autohaus.fahrzeuge_stamm` s
              ON p.fin = s.fin
            WHERE {where_clause}
            ORDER BY p.updated_at DESC
            LIMIT {limit}
            """
            
            results = self.client.query(query).result()
            
            fahrzeuge = []
            for row in results:
                fahrzeuge.append(self._convert_row_to_dict(row))
                
            return fahrzeuge
            
        except Exception as e:
            logger.error(f"Fahrzeuge mit Prozessen abrufen Fehler: {e}")
            return []
    
    async def get_dashboard_kpis(self) -> Dict[str, Any]:
        """Dashboard KPIs aus normalisierten Tabellen"""
        if not self.client:
            return self._get_mock_dashboard_kpis()
            
        try:
            query = """
            WITH kpi_daten AS (
              SELECT 
                COUNT(DISTINCT p.fin) as aktive_fahrzeuge,
                COUNTIF(DATE(p.created_at) = CURRENT_DATE()) as heute_gestartet,
                COUNTIF(p.tage_bis_sla_deadline < 0) as sla_verletzungen,
                AVG(p.standzeit_tage) as avg_standzeit,
                COUNT(DISTINCT s.marke) as anzahl_marken,
                COUNT(DISTINCT p.bearbeiter) as anzahl_bearbeiter
              FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` p
              LEFT JOIN `ra-autohaus-tracker.autohaus.fahrzeuge_stamm` s
                ON p.fin = s.fin
              WHERE p.status NOT IN ('verkauft', 'storniert', 'abgeschlossen')
                AND p.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            )
            SELECT * FROM kpi_daten
            """
            
            results = self.client.query(query).result()
            row = next(iter(results))
            
            return {
                "aktive_fahrzeuge": row.aktive_fahrzeuge or 0,
                "heute_gestartet": row.heute_gestartet or 0,
                "sla_verletzungen": row.sla_verletzungen or 0,
                "avg_standzeit": round(row.avg_standzeit or 0, 1),
                "anzahl_marken": row.anzahl_marken or 0,
                "anzahl_bearbeiter": row.anzahl_bearbeiter or 0,
                "timestamp": datetime.now().isoformat(),
                "status": "live_data"
            }
            
        except Exception as e:
            logger.error(f"Dashboard KPIs Fehler: {e}")
            return self._get_mock_dashboard_kpis()
    
    async def get_warteschlangen_status(self) -> Dict[str, Any]:
        """Warteschlangen-Status für alle Prozesstypen"""
        if not self.client:
            return self._get_mock_warteschlangen()
            
        try:
            query = """
            SELECT 
              prozess_typ,
              status,
              COUNT(*) as anzahl,
              AVG(standzeit_tage) as avg_standzeit,
              AVG(tage_bis_sla_deadline) as avg_sla_verbleibend
            FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE status IN ('warteschlange', 'geplant', 'in_bearbeitung')
              AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
            GROUP BY prozess_typ, status
            ORDER BY prozess_typ, anzahl DESC
            """
            
            results = self.client.query(query).result()
            
            warteschlangen = {}
            for row in results:
                prozess = row.prozess_typ
                if prozess not in warteschlangen:
                    warteschlangen[prozess] = {}
                    
                warteschlangen[prozess][row.status] = {
                    "anzahl": row.anzahl,
                    "avg_standzeit": round(row.avg_standzeit or 0, 1),
                    "avg_sla_verbleibend": round(row.avg_sla_verbleibend or 0, 1)
                }
            
            return {
                "warteschlangen": warteschlangen,
                "timestamp": datetime.now().isoformat(),
                "status": "live_data"
            }
            
        except Exception as e:
            logger.error(f"Warteschlangen-Status Fehler: {e}")
            return self._get_mock_warteschlangen()
    
    # ========================================
    # UTILITY Methoden
    # ========================================
    
    def _prepare_stamm_data(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fahrzeug-Stammdaten für BigQuery vorbereiten"""
        prepared = {}
        
        for key, value in vehicle_data.items():
            if value is not None:
                if isinstance(value, (datetime, date)):
                    prepared[key] = value.isoformat()
                else:
                    prepared[key] = value
        
        # Default-Werte setzen falls nicht vorhanden
        if "ersterfassung_datum" not in prepared:
            prepared["ersterfassung_datum"] = datetime.now().isoformat()
        if "aktiv" not in prepared:
            prepared["aktiv"] = True
            
        return prepared
    
    def _prepare_prozess_data(self, process_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prozess-Daten für BigQuery vorbereiten"""
        prepared = {}
        
        for key, value in process_data.items():
            if value is not None:
                if isinstance(value, (datetime, date)):
                    prepared[key] = value.isoformat()
                else:
                    prepared[key] = value
        
        # Default-Werte setzen falls nicht vorhanden
        if "erstellt_am" not in prepared:
            prepared["erstellt_am"] = datetime.now().isoformat()
        if "aktualisiert_am" not in prepared:
            prepared["aktualisiert_am"] = datetime.now().isoformat()
            
        return prepared
    
    def _convert_row_to_dict(self, row) -> Dict[str, Any]:
        """BigQuery Row zu Dictionary konvertieren"""
        result = {}
        for key, value in dict(row).items():
            if hasattr(value, 'isoformat'):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    
    def _create_query_parameter(self, key: str, value: Any) -> bigquery.ScalarQueryParameter:
        """Query Parameter basierend auf Datentyp erstellen"""
        if isinstance(value, str):
            return bigquery.ScalarQueryParameter(key, "STRING", value)
        elif isinstance(value, int):
            return bigquery.ScalarQueryParameter(key, "INTEGER", value)
        elif isinstance(value, float):
            return bigquery.ScalarQueryParameter(key, "NUMERIC", value)
        elif isinstance(value, bool):
            return bigquery.ScalarQueryParameter(key, "BOOLEAN", value)
        elif isinstance(value, (datetime, date)):
            return bigquery.ScalarQueryParameter(key, "DATETIME", value.isoformat())
        else:
            return bigquery.ScalarQueryParameter(key, "STRING", str(value))
    
    # ========================================
    # MOCK-Daten für Fallback
    # ========================================
    
    def _get_mock_fahrzeug_stamm(self, fin: str) -> Dict[str, Any]:
        """Mock Fahrzeug-Stammdaten"""
        return {
            "fin": fin,
            "marke": "Audi",
            "modell": "A4",
            "antriebsart": "Benzin",
            "farbe": "Schwarz",
            "baujahr": 2020,
            "kw_leistung": 140,
            "km_stand": 25000,
            "ek_netto": 18500.00,
            "status": "mock_data"
        }
    
    def _get_mock_fahrzeuge_mit_prozessen(self) -> List[Dict[str, Any]]:
        """Mock Fahrzeuge mit Prozessen"""
        return [
            {
                "fin": "WAUZZZGE1NB038655",
                "marke": "Audi",
                "modell": "A4",
                "prozess_typ": "Aufbereitung",
                "status": "in_bearbeitung",
                "bearbeiter": "Hans Müller",
                "prioritaet": 3,
                "standzeit_tage": 2,
                "tage_bis_sla_deadline": 1
            }
        ]
    
    def _get_mock_fahrzeug_prozesse(self, fin: str) -> List[Dict[str, Any]]:
        """Mock Prozesse für Fahrzeug"""
        return [
            {
                "prozess_id": f"PROC_{uuid.uuid4().hex[:8]}",
                "fin": fin,
                "prozess_typ": "Aufbereitung",
                "status": "in_bearbeitung",
                "bearbeiter": "Hans Müller",
                "prioritaet": 5,
                "standzeit_tage": 2
            }
        ]
    
    def _get_mock_dashboard_kpis(self) -> Dict[str, Any]:
        """Mock Dashboard KPIs"""
        return {
            "aktive_fahrzeuge": 42,
            "heute_gestartet": 3,
            "sla_verletzungen": 2,
            "avg_standzeit": 15.5,
            "anzahl_marken": 8,
            "anzahl_bearbeiter": 6,
            "timestamp": datetime.now().isoformat(),
            "status": "mock_data"
        }
    
    def _get_mock_warteschlangen(self) -> Dict[str, Any]:
        """Mock Warteschlangen-Status"""
        return {
            "warteschlangen": {
                "Aufbereitung": {
                    "warteschlange": {"anzahl": 5, "avg_standzeit": 2.3},
                    "in_bearbeitung": {"anzahl": 2, "avg_standzeit": 1.1}
                },
                "Foto": {
                    "warteschlange": {"anzahl": 3, "avg_standzeit": 0.8},
                    "in_bearbeitung": {"anzahl": 1, "avg_standzeit": 0.5}
                }
            },
            "timestamp": datetime.now().isoformat(),
            "status": "mock_data"
        }