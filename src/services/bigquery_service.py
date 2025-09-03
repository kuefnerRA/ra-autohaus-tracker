"""
BigQuery Service - Core Data Layer
Reinhardt Automobile GmbH - RA Autohaus Tracker

Zentraler Service für alle BigQuery-Operationen mit Type-Safety und Error-Handling.
"""

import logging
import os
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import json

try:
    from google.cloud import bigquery
    from google.cloud.bigquery import Client, Table
    from google.api_core.exceptions import GoogleAPIError, NotFound
    from google.auth import impersonated_credentials
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
        self.use_mock = os.getenv('USE_MOCK_BIGQUERY', 'false').lower() == 'true'
        
        # Automatisch Mock verwenden wenn BigQuery nicht verfügbar
        if not BIGQUERY_AVAILABLE:
            self.use_mock = True
        
        # Client-Initialisierung
        self.client: Optional[Client] = None
        self.dataset_ref: Optional[str] = f"{self.project_id}.{self.dataset_name}"
        
        # Mock-Daten für Fallback
        self._mock_fahrzeuge: List[Dict[str, Any]] = []
        self._mock_prozesse: List[Dict[str, Any]] = []
        
        # Logging
        self.logger = logger.bind(
            service="BigQueryService",
            project=self.project_id,
            dataset=self.dataset_name,
            service_account=self.service_account,
            mock_mode=self.use_mock
        )
        
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialisiert BigQuery Client mit Service Account Impersonation."""
        if self.use_mock:
            self.logger.info("🧪 BigQuery Mock-Modus aktiviert")
            self._init_mock_data()
            return
            
        if not BIGQUERY_AVAILABLE:
            self.logger.warning("⚠️ Google Cloud BigQuery SDK nicht installiert - verwende Mock-Modus")
            self.use_mock = True
            self._init_mock_data()
            return
            
        try:
            # Service Account Impersonation verwenden falls konfiguriert
            if self.service_account:
                # ADC laden
                source_credentials, _ = google.auth.default()
                
                # Service Account impersonieren
                target_credentials = impersonated_credentials.Credentials(
                    source_credentials=source_credentials,
                    target_principal=self.service_account,
                    target_scopes=['https://www.googleapis.com/auth/bigquery']
                )
                
                self.client = bigquery.Client(project=self.project_id, credentials=target_credentials)
                self.logger.info("✅ BigQuery Client mit Service Account Impersonation initialisiert",
                               service_account=self.service_account)
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
            self._init_mock_data()
    
    def _init_mock_data(self) -> None:
        """Initialisiert Mock-Daten für lokale Entwicklung."""
        self._mock_fahrzeuge = [
            {
                'fin': 'WVWZZZ1JZ8W123456',
                'marke': 'Volkswagen',
                'modell': 'Golf',
                'antriebsart': 'Benzin',
                'farbe': 'Schwarz',
                'baujahr': 2023,
                'ek_netto': Decimal('18500.00'),
                'aktiv': True,
                'datenquelle_fahrzeug': 'mock',
                'created_at': datetime.now()
            },
            {
                'fin': 'WBA12345678901234',
                'marke': 'BMW',
                'modell': '320d',
                'antriebsart': 'Diesel',
                'farbe': 'Weiß',
                'baujahr': 2022,
                'ek_netto': Decimal('28500.00'),
                'aktiv': True,
                'datenquelle_fahrzeug': 'mock',
                'created_at': datetime.now()
            },
            {
                'fin': 'WDD12345678901234',
                'marke': 'Mercedes-Benz',
                'modell': 'C-Klasse',
                'antriebsart': 'Hybrid',
                'farbe': 'Silber',
                'baujahr': 2024,
                'ek_netto': Decimal('35500.00'),
                'aktiv': True,
                'datenquelle_fahrzeug': 'mock',
                'created_at': datetime.now()
            }
        ]
        
        self._mock_prozesse = [
            {
                'prozess_id': 'AUF_123456_20250102_143000',
                'fin': 'WVWZZZ1JZ8W123456',
                'prozess_typ': 'Aufbereitung',
                'status': 'In Bearbeitung',
                'bearbeiter': 'Thomas Küfner',
                'prioritaet': 3,
                'sla_tage': 3,
                'datenquelle': 'mock',
                'aktualisiert_am': datetime.now(),
                'created_at': datetime.now()
            },
            {
                'prozess_id': 'FOT_901234_20250102_144500',
                'fin': 'WBA12345678901234',
                'prozess_typ': 'Foto',
                'status': 'Wartend',
                'bearbeiter': 'Maximilian Reinhardt',
                'prioritaet': 4,
                'sla_tage': 1,
                'datenquelle': 'mock',
                'aktualisiert_am': datetime.now(),
                'created_at': datetime.now()
            },
            {
                'prozess_id': 'VER_901234_20250102_145000',
                'fin': 'WDD12345678901234',
                'prozess_typ': 'Verkauf',
                'status': 'Aktiv',
                'bearbeiter': 'Thomas Küfner',
                'prioritaet': 2,
                'sla_tage': 30,
                'datenquelle': 'mock',
                'aktualisiert_am': datetime.now(),
                'created_at': datetime.now()
            }
        ]
        
        self.logger.info("🧪 Mock-Daten initialisiert", 
                       fahrzeuge=len(self._mock_fahrzeuge),
                       prozesse=len(self._mock_prozesse))
    
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
            
            if self.use_mock:
                return await self._create_fahrzeug_mock(fahrzeug_data)
            
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
    
    async def create_fahrzeug_prozess(self, prozess_data: Dict[str, Any]) -> bool:
        """
        Erstellt einen neuen Fahrzeugprozess.
        
        Args:
            prozess_data: Prozessdaten als Dictionary
            
        Returns:
            bool: True wenn erfolgreich
        """
        try:
            # Validierung
            required_fields = ['prozess_id', 'fin', 'prozess_typ', 'status']
            for field in required_fields:
                if field not in prozess_data:
                    raise ValueError(f"Feld '{field}' ist erforderlich")
            
            if self.use_mock:
                return await self._create_prozess_mock(prozess_data)
            
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
            if self.use_mock:
                return next((f for f in self._mock_fahrzeuge if f['fin'] == fin), None)
            
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
            if self.use_mock:
                return await self._get_fahrzeuge_mit_prozessen_mock(limit, prozess_typ, bearbeiter)
            
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
            'ek_netto': float(fahrzeug_data['ek_netto']) if fahrzeug_data.get('ek_netto') else None,
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
            'datenquelle': prozess_data.get('datenquelle', 'api'),
            'notizen': prozess_data.get('notizen'),
            'zusatz_daten': json.dumps(prozess_data.get('zusatz_daten', {})),
            'erstellt_am': now.isoformat(),
            'aktualisiert_am': now.isoformat(),
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
    
    # Mock-Implementierungen
    async def _create_fahrzeug_mock(self, fahrzeug_data: Dict[str, Any]) -> bool:
        """Mock-Implementation für Fahrzeug-Erstellung."""
        existing_index = next((i for i, f in enumerate(self._mock_fahrzeuge) 
                             if f['fin'] == fahrzeug_data['fin']), None)
        
        if existing_index is not None:
            # Update
            self._mock_fahrzeuge[existing_index].update(fahrzeug_data)
            self._mock_fahrzeuge[existing_index]['updated_at'] = datetime.now()
            self.logger.info("🧪 Mock: Fahrzeug-Stammdaten aktualisiert", fin=fahrzeug_data['fin'])
        else:
            # Insert
            fahrzeug_data['created_at'] = datetime.now()
            fahrzeug_data['aktiv'] = True
            self._mock_fahrzeuge.append(fahrzeug_data)
            self.logger.info("🧪 Mock: Fahrzeug-Stammdaten erstellt", fin=fahrzeug_data['fin'])
        
        return True
    
    async def _create_prozess_mock(self, prozess_data: Dict[str, Any]) -> bool:
        """Mock-Implementation für Prozess-Erstellung."""
        prozess_data['created_at'] = datetime.now()
        prozess_data['aktualisiert_am'] = datetime.now()
        self._mock_prozesse.append(prozess_data)
        self.logger.info("🧪 Mock: Fahrzeugprozess erstellt", 
                       prozess_id=prozess_data['prozess_id'])
        return True
    
    async def _get_fahrzeuge_mit_prozessen_mock(
        self, 
        limit: int,
        prozess_typ: Optional[str] = None,
        bearbeiter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Mock-Implementation für JOIN-Query."""
        result = []
        
        for fahrzeug in self._mock_fahrzeuge:
            # Aktuellsten Prozess für dieses Fahrzeug suchen
            fahrzeug_prozesse = [p for p in self._mock_prozesse if p['fin'] == fahrzeug['fin']]
            
            # Kombinierte Daten erstellen
            combined = fahrzeug.copy()
            
            if fahrzeug_prozesse:
                # Neuesten Prozess nehmen
                aktueller_prozess = max(fahrzeug_prozesse, key=lambda x: x['created_at'])
                
                # Filter anwenden
                if prozess_typ and aktueller_prozess.get('prozess_typ') != prozess_typ:
                    continue
                if bearbeiter and aktueller_prozess.get('bearbeiter') != bearbeiter:
                    continue
                
                # Prozessdaten hinzufügen
                combined.update(aktueller_prozess)
            else:
                # Fahrzeug ohne Prozess
                if prozess_typ or bearbeiter:
                    continue  # Filter ausschließen wenn kein Prozess
            
            result.append(combined)
            
            if len(result) >= limit:
                break
        
        return result
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Gesundheitscheck für BigQuery-Verbindung.
        
        Returns:
            Dict: Status-Informationen
        """
        if self.use_mock:
            return {
                'status': 'healthy',
                'mode': 'mock',
                'mock_fahrzeuge': len(self._mock_fahrzeuge),
                'mock_prozesse': len(self._mock_prozesse),
                'bigquery_sdk': BIGQUERY_AVAILABLE
            }
        
        try:
            # Einfache Query zum Test
            if not self.client:
                raise RuntimeError("BigQuery Client nicht verfügbar")
            query = f"SELECT COUNT(*) as count FROM `{self.dataset_ref}.fahrzeuge_stamm` LIMIT 1"
            query_job = self.client.query(query)
            result = list(query_job.result())
            
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
