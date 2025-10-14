"""
BigQuery Service - Core Data Layer
Reinhardt Automobile GmbH - RA Autohaus Tracker

Zentraler Service für alle BigQuery-Operationen mit Type-Safety und Error-Handling.
"""

import os
from datetime import datetime, date
from typing import Dict, List, Optional, Any, cast
from decimal import Decimal
import json


try:
    from google.cloud import bigquery
    from google.cloud.bigquery import Client
    from google.api_core.exceptions import GoogleAPIError, NotFound
    from google.auth import impersonated_credentials
    from google.auth.credentials import Credentials

    import google.auth
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False
    # Fallback für lokale Entwicklung ohne Google Cloud SDK

import structlog

# Strukturiertes Logging
logger = structlog.get_logger(__name__)

class BigQueryService:
    """
    Zentraler Service für BigQuery-Operationen.
    
    Verantwortlichkeiten:
    - Verbindungsmanagement zu BigQuery
    - CRUD-Operationen für fahrzeuge_stamm und fahrzeug_prozesse
    - Schema-Validierung und Type-Safety
    - Service Account Impersonation
    - Fallback zu Mock-Modus bei Problemen
    """
    
    def __init__(self, project_id: Optional[str] = None, dataset_name: Optional[str] = None):
        """
        Initialisiert BigQuery Service.
        
        Args:
            project_id: Google Cloud Project ID (default: aus ENV)
            dataset_name: BigQuery Dataset Name (default: aus ENV)
        """
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT', 'ra-autohaus-tracker')
        self.dataset_name = dataset_name or os.getenv('BIGQUERY_DATASET', 'autohaus')
        self.service_account = os.getenv('GOOGLE_SERVICE_ACCOUNT')
        
        # Client-Initialisierung
        self.client: Optional[Client] = None
        self.dataset_ref: str = f"{self.project_id}.{self.dataset_name}"
        
        # Logging
        self.logger = logger.bind(
            service="BigQueryService",
            project=self.project_id,
            dataset=self.dataset_name,
            service_account=self.service_account
        )
        
        self._init_client()
    
    def _serialize_dates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Konvertiert date/datetime Objekte zu Strings"""
        from datetime import date, datetime
        
        result = {}
        for key, value in data.items():
            if isinstance(value, (date, datetime)):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    
    def _init_client(self) -> None:
        """Initialisiert BigQuery Client mit Service Account Impersonation."""
        if not BIGQUERY_AVAILABLE:
            raise RuntimeError("Google Cloud BigQuery SDK nicht installiert. Bitte installieren Sie: pip install google-cloud-bigquery")
            
        try:
            # ADC laden
            source_credentials, project = google.auth.default()
            
            # Service Account Impersonation nur wenn nötig
            if self.service_account:
                source_account = getattr(source_credentials, 'service_account_email', None)
                
                self.logger.info("🔍 Credentials Analyse",
                    source_type=type(source_credentials).__name__,
                    source_account=source_account,
                    target_account=self.service_account,
                    needs_impersonation=(source_account != self.service_account)
                )
                
                # Nur impersonieren wenn source != target
                if source_account and source_account == self.service_account:
                    # Bereits der richtige Service Account - keine Impersonation nötig!
                    self.logger.info("✅ Verwende bereits impersonierte Credentials",
                        service_account=self.service_account)
                    self.client = bigquery.Client(project=self.project_id, credentials=cast(Credentials, source_credentials))
                else:
                    # Echte Impersonation nötig
                    self.logger.info("🔄 Impersonation erforderlich",
                        from_account=source_account or "user account",
                        to_account=self.service_account)
                    
                    from google.auth.transport import requests
                    
                    target_credentials = impersonated_credentials.Credentials(
                        source_credentials=source_credentials,
                        target_principal=self.service_account,
                        target_scopes=['https://www.googleapis.com/auth/bigquery'],
                        lifetime=3600
                    )
                    
                    request = requests.Request()
                    target_credentials.refresh(request)
                    
                    self.client = bigquery.Client(project=self.project_id, credentials=target_credentials)
                    self.logger.info("✅ BigQuery Client mit Impersonation initialisiert")
            else:
                # Standard ADC verwenden
                self.client = bigquery.Client(project=self.project_id)
                self.logger.info("✅ BigQuery Client mit ADC initialisiert")
            
            # Verbindung testen
            if not self.client or not self.dataset_ref:
                raise RuntimeError("BigQuery Client nicht initialisiert")
            dataset = self.client.get_dataset(self.dataset_ref)
            self.logger.info("✅ BigQuery Dataset-Verbindung erfolgreich", 
                        dataset=dataset.dataset_id)
            
        except Exception as e:
            self.logger.error("❌ BigQuery Client Initialisierung fehlgeschlagen", error=str(e))
            self.logger.warning("🔄 Fallback zu Mock-Modus")
            self.use_mock = True


 
    
    async def create_fahrzeug_stamm(self, fahrzeug_data: Dict[str, Any]) -> bool:
        """
        Erstellt oder aktualisiert Fahrzeugstammdaten.
        
        Args:
            fahrzeug_data: Fahrzeugdaten als Dictionary
            
        Returns:
            bool: True wenn erfolgreich
            
        Raises:
            ValueError: Bei ungültigen Daten
            GoogleAPIError: Bei BigQuery-Fehlern
        """
        try:
            # Validierung
            if 'fin' not in fahrzeug_data:
                raise ValueError("FIN ist erforderlich")
            
            fin = fahrzeug_data['fin']
            
            fahrzeug_data = self._serialize_dates(fahrzeug_data)
            
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
            
            # BigQuery INSERT
            table_id = f"{self.dataset_ref}.fahrzeuge_stamm"
            
            # Prüfen ob Fahrzeug existiert
            existing = await self.get_fahrzeug_by_fin(fin)
            
            if existing:
                # UPDATE - für MVP erstmal Skip
                self.logger.info("ℹ️ Fahrzeug bereits vorhanden - Update in zukünftiger Version", fin=fin)
                return True
            else:
                # INSERT
                if not self.client:
                    raise RuntimeError("BigQuery Client nicht verfügbar")
                rows_to_insert = [self._prepare_fahrzeug_row(fahrzeug_data)]
                table = self.client.get_table(table_id)
                errors = self.client.insert_rows_json(table, rows_to_insert)
                
                if errors:
                    raise GoogleAPIError(f"Insert-Fehler: {errors}")
                
                self.logger.info("✅ Fahrzeug-Stammdaten erstellt", fin=fin)
            
            return True
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Erstellen von Fahrzeug-Stammdaten", 
                            error=str(e), fin=fahrzeug_data.get('fin'))
            raise
    
    async def update_fahrzeug_stamm(
        self, 
        fin: str, 
        update_data: Dict[str, Any],
        log_changes: bool = True
    ) -> Dict[str, Any]:
        """
        Aktualisiert Fahrzeugstammdaten mit Change-Tracking.
        
        Args:
            fin: Fahrzeugidentifizierungsnummer
            update_data: Zu aktualisierende Felder
            log_changes: Ob Änderungen geloggt werden sollen
            
        Returns:
            Dict mit update_result und change_log
        """
        try:
            # Aktuelles Fahrzeug abrufen für Vergleich
            current_vehicle = await self.get_fahrzeug_by_fin(fin)
            
            if not current_vehicle:
                raise ValueError(f"Fahrzeug mit FIN {fin} nicht gefunden")
            
            # Change-Log erstellen
            change_log = []
            fields_updated = []
            
            # Timestamps
            now = datetime.utcnow()
            update_data['updated_at'] = now.isoformat()
            
            # Serialisiere Dates
            update_data = self._serialize_dates(update_data)
            
            # BigQuery UPDATE via DML
            set_clauses = []
            parameters = []
            
            for field, new_value in update_data.items():
                if field in ['fin', 'created_at']:  # FIN und created_at nie ändern
                    continue
                    
                old_value = current_vehicle.get(field)
                
                # Nur wenn Wert sich ändert und nicht None ist
                if old_value != new_value and new_value is not None:
                    set_clauses.append(f"{field} = @{field}")
                    
                    # Parameter-Typ bestimmen
                    if isinstance(new_value, bool):
                        param_type = "BOOL"
                    elif isinstance(new_value, Decimal):
                        param_type = "NUMERIC"
                        new_value = str(new_value)  # BigQuery erwartet NUMERIC als String
                    elif isinstance(new_value, float):
                        # Prüfe ob es ein Geldfeld ist
                        if field in ['ek_netto', 'vk_netto', 'ek_brutto', 'vk_brutto']:
                            param_type = "NUMERIC"
                            new_value = str(new_value)
                        else:
                            param_type = "FLOAT64"
                    elif isinstance(new_value, int):
                        param_type = "INT64"
                    elif isinstance(new_value, (datetime, date)):
                        param_type = "TIMESTAMP" if isinstance(new_value, datetime) else "DATE"
                        new_value = new_value.isoformat()
                    else:
                        param_type = "STRING"
                        new_value = str(new_value) if new_value is not None else None
                    
                    parameters.append(
                        bigquery.ScalarQueryParameter(field, param_type, new_value)
                    )
                    
                    # Für Change-Log
                    change_log.append({
                        'field': field,
                        'old_value': old_value,
                        'new_value': new_value,
                        'timestamp': now.isoformat()
                    })
                    fields_updated.append(field)

            if not set_clauses:
                self.logger.info("ℹ️ Keine Änderungen für Fahrzeug", fin=fin)
                return {
                    'success': True,
                    'fin': fin,
                    'changes_made': False,
                    'fields_updated': [],
                    'change_log': []
                }

            # FIN-Parameter EINMAL hinzufügen (AUSSERHALB der Schleife!)
            parameters.append(
                bigquery.ScalarQueryParameter("fin", "STRING", fin)
            )

            # MERGE Query ausführen
            query = f"""
            MERGE `{self.dataset_ref}.fahrzeuge_stamm` T
            USING (SELECT @fin AS fin) S
            ON T.fin = S.fin
            WHEN MATCHED THEN
            UPDATE SET {', '.join(set_clauses)}
            """
            
            job_config = bigquery.QueryJobConfig(query_parameters=parameters)
            
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
                
            query_job = self.client.query(query, job_config=job_config)
            query_job.result()  # Warte auf Abschluss
            
            # Optional: Change-Log in separate Tabelle speichern
            if log_changes and change_log:
                await self._log_vehicle_changes(fin, change_log)
            
            self.logger.info("✅ Fahrzeug-Stammdaten aktualisiert", 
                            fin=fin,
                            fields_updated=fields_updated,
                            changes_count=len(change_log))
            
            return {
                'success': True,
                'fin': fin,
                'changes_made': len(change_log) > 0,
                'fields_updated': fields_updated,
                'change_log': change_log
            }
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Update der Fahrzeug-Stammdaten", 
                            error=str(e), fin=fin)
            raise

    async def _log_vehicle_changes(self, fin: str, changes: List[Dict[str, Any]]) -> None:
        """
        Speichert Änderungshistorie in separater Tabelle (optional).
        
        Tabelle 'fahrzeug_aenderungen' sollte folgende Struktur haben:
        - change_id: STRING
        - fin: STRING  
        - field_name: STRING
        - old_value: STRING
        - new_value: STRING
        - changed_at: TIMESTAMP
        - changed_by: STRING
        """
        try:
            if self.use_mock:
                # In Mock-Modus nur loggen
                self.logger.info("🧪 Mock: Änderungen würden geloggt", 
                            fin=fin, changes_count=len(changes))
                return
            
            # Prüfe ob Änderungs-Tabelle existiert
            table_id = f"{self.dataset_ref}.fahrzeug_aenderungen"
            
            rows_to_insert = []
            for change in changes:
                rows_to_insert.append({
                    'change_id': f"{fin}_{change['field']}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    'fin': fin,
                    'field_name': change['field'],
                    'old_value': str(change['old_value']) if change['old_value'] is not None else None,
                    'new_value': str(change['new_value']) if change['new_value'] is not None else None,
                    'changed_at': change['timestamp'],
                    'changed_by': 'email_import',  # Könnte aus Context kommen
                    'created_at': datetime.utcnow().isoformat()
                })
            
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
                
            # Versuche in Änderungs-Tabelle zu schreiben
            try:
                table = self.client.get_table(table_id)
                errors = self.client.insert_rows_json(table, rows_to_insert)
                
                if errors:
                    self.logger.warning("⚠️ Fehler beim Logging der Änderungen", errors=errors)
                else:
                    self.logger.info("📝 Änderungshistorie gespeichert", 
                                fin=fin, entries=len(rows_to_insert))
            except NotFound:
                # Tabelle existiert nicht - nur loggen
                self.logger.debug("Änderungs-Tabelle existiert nicht, Logging übersprungen")
                
        except Exception as e:
            # Fehler beim Logging sollten Update nicht verhindern
            self.logger.warning("⚠️ Änderungs-Logging fehlgeschlagen", error=str(e))

    async def create_fahrzeug_prozess(self, prozess_data: Dict[str, Any]) -> bool:
        """
        Erstellt einen neuen Fahrzeugprozess.
        """
        try:
            # Validierung
            required_fields = ['prozess_id', 'fin', 'prozess_typ', 'status']
            for field in required_fields:
                if field not in prozess_data:
                    raise ValueError(f"Feld '{field}' ist erforderlich")
            
            # Serialisiere Dates/DateTime BEVOR prepare_row
            prozess_data = self._serialize_dates(prozess_data)
            
            
            # BigQuery INSERT
            table_id = f"{self.dataset_ref}.fahrzeug_prozesse"
            rows_to_insert = [self._prepare_prozess_row(prozess_data)]
            
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
            table = self.client.get_table(table_id)
            errors = self.client.insert_rows_json(table, rows_to_insert)
            
            if errors:
                raise GoogleAPIError(f"Insert-Fehler: {errors}")
            
            self.logger.info("✅ Fahrzeugprozess erstellt", 
                        prozess_id=prozess_data['prozess_id'],
                        fin=prozess_data['fin'])
            
            return True
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Erstellen des Fahrzeugprozesses", 
                            error=str(e), 
                            prozess_id=prozess_data.get('prozess_id'))
            raise

    async def get_fahrzeug_by_fin(self, fin: str) -> Optional[Dict[str, Any]]:
        """
        Holt Fahrzeugdaten anhand der FIN.
        
        Args:
            fin: Fahrzeugidentifizierungsnummer
            
        Returns:
            Optional[Dict]: Fahrzeugdaten oder None
        """
        try:

            
            query = f"""
            SELECT *
            FROM `{self.dataset_ref}.fahrzeuge_stamm`
            WHERE fin = @fin AND aktiv = TRUE
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("fin", "STRING", fin)
                ]
            )
            
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                return dict(row)
            
            return None
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Abrufen der Fahrzeugdaten", 
                            error=str(e), fin=fin)
            return None
    
    async def get_fahrzeuge_mit_prozessen(
        self, 
        limit: int = 100,
        prozess_typ: Optional[str] = None,
        bearbeiter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Holt Fahrzeuge mit aktuellen Prozessen.
        
        Args:
            limit: Maximale Anzahl Ergebnisse
            prozess_typ: Filter nach Prozesstyp
            bearbeiter: Filter nach Bearbeiter
            
        Returns:
            List[Dict]: Fahrzeuge mit Prozessdaten
        """
        try:
             
            # Base Query mit JOIN
            query = f"""
            SELECT 
                f.*,
                p.prozess_id,
                p.prozess_typ,
                p.status,
                p.bearbeiter,
                p.prioritaet,
                p.sla_deadline_datum,
                p.tage_bis_sla_deadline,
                p.standzeit_tage,
                p.aktualisiert_am as prozess_aktualisiert_am
            FROM `{self.dataset_ref}.fahrzeuge_stamm` f
            LEFT JOIN (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY fin ORDER BY aktualisiert_am DESC) as rn
                FROM `{self.dataset_ref}.fahrzeug_prozesse`
            ) p ON f.fin = p.fin AND p.rn = 1
            WHERE f.aktiv = TRUE
            """
            
            # Filter hinzufügen
            query_params = []
            if prozess_typ:
                query += " AND p.prozess_typ = @prozess_typ"
                query_params.append(bigquery.ScalarQueryParameter("prozess_typ", "STRING", prozess_typ))
            
            if bearbeiter:
                query += " AND p.bearbeiter = @bearbeiter"
                query_params.append(bigquery.ScalarQueryParameter("bearbeiter", "STRING", bearbeiter))
            
            query += f" LIMIT {limit}"
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            fahrzeuge = []
            for row in results:
                fahrzeuge.append(dict(row))
            
            self.logger.info("📊 Fahrzeuge mit Prozessen abgerufen", 
                           count=len(fahrzeuge), 
                           prozess_typ=prozess_typ,
                           bearbeiter=bearbeiter)
            
            return fahrzeuge
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Abrufen der Fahrzeuge mit Prozessen", error=str(e))
            return []
    
    async def get_prozesse_by_fin(
        self, 
        fin: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Holt alle Prozesse eines Fahrzeugs.
        """
        try:
              
            query = f"""
            SELECT *
            FROM `{self.dataset_ref}.fahrzeug_prozesse`
            WHERE fin = @fin
            ORDER BY aktualisiert_am DESC
            LIMIT {limit}
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("fin", "STRING", fin)
                ]
            )
            
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
            
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            prozesse = []
            for row in results:
                prozess = dict(row)
                
                # Datentyp-Korrekturen
                if 'prioritaet' in prozess and prozess['prioritaet'] is not None:
                    prozess['prioritaet'] = str(prozess['prioritaet'])
                
                if 'zusatz_daten' in prozess and isinstance(prozess['zusatz_daten'], str):
                    import json
                    try:
                        prozess['zusatz_daten'] = json.loads(prozess['zusatz_daten'])
                    except (json.JSONDecodeError, TypeError):
                        prozess['zusatz_daten'] = None
                
                prozesse.append(prozess)
            
            return prozesse
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Abrufen der Prozesse", 
                            error=str(e))
            return []

    async def get_prozess_by_id(
        self, 
        prozess_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Holt einen spezifischen Prozess.
        """
        try:
            
            query = f"""
            SELECT *
            FROM `{self.dataset_ref}.fahrzeug_prozesse`
            WHERE prozess_id = @prozess_id
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("prozess_id", "STRING", prozess_id)
                ]
            )
            
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
            
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                return dict(row)
            
            return None
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Abrufen des Prozesses", 
                            error=str(e))
            return None

    # ===============================
    # Dashboard-spezifische Queries
    # ===============================

    async def get_dashboard_prozess_stats(self, days_back: int = 90) -> List[Dict[str, Any]]:
        """Holt Prozess-Statistiken für Dashboard KPIs"""
        query = f"""
        SELECT 
            COUNT(DISTINCT fin) as fahrzeuge_gesamt,
            COUNT(DISTINCT CASE WHEN status != 'abgeschlossen' THEN fin END) as fahrzeuge_aktiv,
            COUNT(DISTINCT CASE WHEN prozess_typ = 'Aufbereitung' AND status != 'abgeschlossen' THEN fin END) as in_aufbereitung,
            COUNT(DISTINCT CASE WHEN prozess_typ = 'Werkstatt' AND status != 'abgeschlossen' THEN fin END) as in_werkstatt,
            COUNT(DISTINCT CASE WHEN prozess_typ = 'Foto' AND status != 'abgeschlossen' THEN fin END) as in_foto,
            COUNT(DISTINCT CASE WHEN prozess_typ = 'Verkauf' AND status = 'verfügbar' THEN fin END) as verkaufsbereit
        FROM `{self.dataset_ref}.fahrzeug_prozesse`
        WHERE DATE(erstellt_am) >= DATE_SUB(CURRENT_DATE(), INTERVAL {days_back} DAY)
        """
        return await self.execute_query(query)

    async def get_dashboard_sla_stats(self) -> List[Dict[str, Any]]:
        """Holt SLA-Statistiken für Dashboard"""
        query = f"""
        SELECT
            COUNT(CASE WHEN tage_bis_sla_deadline < 0 THEN 1 END) as sla_ueberfaellig,
            COUNT(CASE WHEN tage_bis_sla_deadline BETWEEN 0 AND 1 THEN 1 END) as sla_kritisch,
            COUNT(CASE WHEN tage_bis_sla_deadline BETWEEN 2 AND 3 THEN 1 END) as sla_warnung,
            AVG(dauer_minuten) / 60 as avg_prozessdauer_stunden
        FROM `{self.dataset_ref}.fahrzeug_prozesse`
        WHERE status != 'abgeschlossen' 
        AND ende_timestamp IS NULL
        """
        return await self.execute_query(query)

    async def get_dashboard_durchlaufzeiten(self) -> List[Dict[str, Any]]:
        """Holt Durchlaufzeiten-Statistiken"""
        query = f"""
        SELECT 
            prozess_typ,
            AVG(DATETIME_DIFF(ende_timestamp, start_timestamp, HOUR)) as avg_dauer_stunden,
            MIN(DATETIME_DIFF(ende_timestamp, start_timestamp, HOUR)) as min_dauer_stunden,
            MAX(DATETIME_DIFF(ende_timestamp, start_timestamp, HOUR)) as max_dauer_stunden
        FROM `{self.dataset_ref}.fahrzeug_prozesse`
        WHERE ende_timestamp IS NOT NULL
        AND start_timestamp IS NOT NULL
        GROUP BY prozess_typ
        """
        return await self.execute_query(query)

    async def get_warteschlangen_detail(self) -> List[Dict[str, Any]]:
        """Holt detaillierte Warteschlangen-Informationen"""
        query = f"""
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
        FROM `{self.dataset_ref}.fahrzeug_prozesse` p
        LEFT JOIN `{self.dataset_ref}.fahrzeuge_stamm` f ON p.fin = f.fin
        WHERE p.status IN ('wartend', 'in_bearbeitung', 'pausiert')
        AND p.ende_timestamp IS NULL
        ORDER BY p.prioritaet ASC, p.start_timestamp ASC
        """
        return await self.execute_query(query)

    async def get_sla_critical_vehicles(self) -> List[Dict[str, Any]]:
        """Holt SLA-kritische Fahrzeuge"""
        query = f"""
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
        FROM `{self.dataset_ref}.fahrzeug_prozesse` p
        LEFT JOIN `{self.dataset_ref}.fahrzeuge_stamm` f ON p.fin = f.fin
        WHERE p.ende_timestamp IS NULL
        ORDER BY p.tage_bis_sla_deadline ASC
        """
        return await self.execute_query(query)

    async def get_bearbeiter_workload_stats(self) -> List[Dict[str, Any]]:
        """Holt Bearbeiter-Workload Statistiken"""
        query = f"""
        SELECT 
            bearbeiter,
            COUNT(DISTINCT fin) as fahrzeuge_anzahl,
            COUNT(DISTINCT prozess_id) as prozesse_anzahl,
            AVG(DATETIME_DIFF(CURRENT_DATETIME(), start_timestamp, HOUR)) as avg_alter_stunden,
            MIN(tage_bis_sla_deadline) as kritischster_sla,
            STRING_AGG(DISTINCT prozess_typ) as prozess_typen
        FROM `{self.dataset_ref}.fahrzeug_prozesse`
        WHERE ende_timestamp IS NULL
        AND bearbeiter IS NOT NULL
        GROUP BY bearbeiter
        ORDER BY fahrzeuge_anzahl DESC
        """
        return await self.execute_query(query)

    # Helper Methods
    def _prepare_fahrzeug_row(self, fahrzeug_data: Dict[str, Any]) -> Dict[str, Any]:
        """Bereitet Fahrzeugdaten für BigQuery vor."""
        now = datetime.utcnow()
        
        return {
            'fin': fahrzeug_data['fin'],
            'marke': fahrzeug_data.get('marke'),
            'modell': fahrzeug_data.get('modell'),
            'antriebsart': fahrzeug_data.get('antriebsart'),
            'farbe': fahrzeug_data.get('farbe'),
            'baujahr': fahrzeug_data.get('baujahr'),
            'datum_erstzulassung': fahrzeug_data.get('datum_erstzulassung'),
            'kw_leistung': fahrzeug_data.get('kw_leistung'),
            'km_stand': fahrzeug_data.get('km_stand'),
            'anzahl_fahrzeugschluessel': fahrzeug_data.get('anzahl_fahrzeugschluessel'),
            'bereifungsart': fahrzeug_data.get('bereifungsart'),
            'anzahl_vorhalter': fahrzeug_data.get('anzahl_vorhalter'),
            'ek_netto': str(fahrzeug_data['ek_netto']) if fahrzeug_data.get('ek_netto') else None,
            'besteuerungsart': fahrzeug_data.get('besteuerungsart'),
            'ersterfassung_datum': now.isoformat(),
            'aktiv': True,
            'erstellt_aus_email': fahrzeug_data.get('erstellt_aus_email', False),
            'datenquelle_fahrzeug': fahrzeug_data.get('datenquelle_fahrzeug', 'api'),
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
    
    def _prepare_prozess_row(self, prozess_data: Dict[str, Any]) -> Dict[str, Any]:
        """Bereitet Prozessdaten für BigQuery vor."""
        now = datetime.utcnow()
        
        return {
            'prozess_id': prozess_data['prozess_id'],
            'fin': prozess_data['fin'],
            'prozess_typ': prozess_data['prozess_typ'],
            'status': prozess_data['status'],
            'bearbeiter': prozess_data.get('bearbeiter'),
            'prioritaet': prozess_data.get('prioritaet', 5),
            'anlieferung_datum': prozess_data.get('anlieferung_datum'),
            'start_timestamp': prozess_data.get('start_timestamp'),
            'ende_timestamp': prozess_data.get('ende_timestamp'),
            'dauer_minuten': prozess_data.get('dauer_minuten'),
            'standzeit_tage': prozess_data.get('standzeit_tage'),
            'sla_tage': prozess_data.get('sla_tage'),
            'sla_deadline_datum': prozess_data.get('sla_deadline_datum'),
            'tage_bis_sla_deadline': prozess_data.get('tage_bis_sla_deadline'),
            'individuelle_deadline': prozess_data.get('individuelle_deadline'),
            'individuelle_deadline_gesetzt': prozess_data.get('individuelle_deadline_gesetzt'),
            'datenquelle': prozess_data.get('datenquelle', 'api'),
            'notizen': prozess_data.get('notizen'),
            'zusatz_daten': json.dumps(prozess_data.get('zusatz_daten', {})),
            'erstellt_am': now.isoformat(),
            'aktualisiert_am': now.isoformat(),
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
    
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Gesundheitscheck für BigQuery-Verbindung.
        
        Returns:
            Dict: Status-Informationen
        """
        if not BIGQUERY_AVAILABLE or not self.client:
            return {
                'status': 'unhealthy',
                'mode': 'unavailable',
                'error': 'BigQuery nicht verfügbar'
    }
        
        try:
            # Einfache Query zum Test
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
            query = f"SELECT COUNT(*) as count FROM `{self.dataset_ref}.fahrzeuge_stamm` LIMIT 1"
            query_job = self.client.query(query)
            list(query_job.result())
            
            return {
                'status': 'healthy',
                'mode': 'bigquery',
                'project_id': self.project_id,
                'dataset': self.dataset_name,
                'connection': 'ok',
                'service_account': self.service_account
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'mode': 'bigquery',
                'error': str(e)
            }

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Führt eine BigQuery-Abfrage aus"""
        try:
            logger.info(f"📊 Executing query: {query[:100]}...")
            
            # Prüfe ob Client verfügbar
            if not self.client:
                logger.warning("⚠️ BigQuery Client nicht verfügbar - Mock-Daten")
                return []
            
            # Echte BigQuery-Abfrage
            query_job = self.client.query(query)
            results = query_job.result()
            
            # In Liste von Dicts konvertieren
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Query-Fehler: {e}")
            return []
        
    async def insert_cleanup_queue(self, cleanup_entry: Dict[str, Any]) -> bool:
        """
        Fügt einen Eintrag in die cleanup_queue Tabelle ein.
        
        Args:
            cleanup_entry: Dict mit queue_id, fin, cleanup_type, prozess_id, etc.
        """
        try:
            import uuid
            cleanup_entry['queue_id'] = cleanup_entry.get('queue_id', str(uuid.uuid4()))
            
            # Sicherstellen dass alle Pflichtfelder vorhanden sind
            required_fields = ['queue_id', 'fin', 'cleanup_type', 'scheduled_for']
            for field in required_fields:
                if field not in cleanup_entry:
                    self.logger.error(f"❌ Pflichtfeld {field} fehlt in cleanup_entry")
                    return False
            
            # Default-Werte setzen
            cleanup_entry.setdefault('processed', False)
            cleanup_entry.setdefault('created_at', datetime.now().isoformat())
            
            if not self.client:
                self.logger.error("❌ BigQuery Client nicht verfügbar")
                return False
                
            table_ref = f"{self.dataset_ref}.cleanup_queue"
            table = self.client.get_table(table_ref)
            errors = self.client.insert_rows_json(table, [cleanup_entry])
            
            if errors:
                self.logger.error(f"❌ Fehler beim Einfügen in cleanup_queue: {errors}")
                return False
                
            self.logger.info(f"✅ Cleanup-Task geplant", 
                            fin=cleanup_entry['fin'],
                            prozess_id=cleanup_entry.get('prozess_id'),
                            cleanup_type=cleanup_entry['cleanup_type'])
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei insert_cleanup_queue: {e}")
            return False