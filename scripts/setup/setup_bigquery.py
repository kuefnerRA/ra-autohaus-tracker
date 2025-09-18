#!/usr/bin/env python3
"""
BigQuery Setup Script für RA Autohaus Tracker
Reinhardt Automobile GmbH

Dieses Script:
1. Erstellt das BigQuery Dataset
2. Erstellt alle Tabellen
3. Fügt Beispieldaten ein
4. Testet die Verbindung
"""

import os
import sys
from google.cloud import bigquery
from google.cloud.exceptions import Conflict, NotFound
import json

def setup_bigquery():
    """Komplettes BigQuery Setup."""
    
    print("🚀 BigQuery Setup für RA Autohaus Tracker")
    print("=" * 50)
    
    # 1. Konfiguration prüfen
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    dataset_name = os.getenv('BIGQUERY_DATASET', 'autohaus')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT nicht gesetzt!")
        print("   Setze in .env: GOOGLE_CLOUD_PROJECT=deine-projekt-id")
        return False
    
    # ADC (Application Default Credentials) prüfen
    adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    if credentials_path and os.path.exists(credentials_path):
        auth_method = f"JSON Key: {credentials_path}"
    elif os.path.exists(adc_path):
        auth_method = f"ADC: {adc_path}"
    else:
        print("❌ Keine Google Cloud Credentials gefunden!")
        print("   Führe aus: gcloud auth application-default login")
        return False

    print(f"✅ Projekt: {project_id}")
    print(f"✅ Dataset: {dataset_name}")
    print(f"✅ Credentials: {auth_method}")
    
    try:
        # 2. BigQuery Client mit Service Account Impersonation initialisieren
        print("\n🔗 Verbinde zu BigQuery mit Service Account Impersonation...")

        service_account = os.getenv('GOOGLE_SERVICE_ACCOUNT')
        if service_account and False: #TODO temporär deaktiviert, muss wieder aktiviert werden
            from google.auth import impersonated_credentials
            import google.auth
            
            # ADC laden
            source_credentials, _ = google.auth.default()
            
            # Service Account impersonieren
            target_credentials = impersonated_credentials.Credentials(
                source_credentials=source_credentials,
                target_principal=service_account,
                target_scopes=['https://www.googleapis.com/auth/bigquery']
            )
            
            client = bigquery.Client(project=project_id, credentials=target_credentials)
            print(f"✅ Impersonating Service Account: {service_account}")
        else:
            client = bigquery.Client(project=project_id)
            print("✅ Using Application Default Credentials")
                
        # 3. Dataset erstellen
        print(f"\n📊 Erstelle Dataset '{dataset_name}'...")
        dataset_id = f"{project_id}.{dataset_name}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "europe-west3"
        dataset.description = "Fahrzeugprozess-Tracking für Reinhardt Automobile GmbH"
        
        try:
            dataset = client.create_dataset(dataset, timeout=30)
            print(f"✅ Dataset '{dataset_name}' erfolgreich erstellt")
        except Conflict:
            print(f"ℹ️ Dataset '{dataset_name}' existiert bereits")
            dataset = client.get_dataset(dataset_id)
        
        # 4. Tabelle: fahrzeuge_stamm
        print("\n🚗 Erstelle Tabelle 'fahrzeuge_stamm'...")
        create_fahrzeuge_stamm_table(client, dataset_id)
        
        # 5. Tabelle: fahrzeug_prozesse
        print("\n⚙️ Erstelle Tabelle 'fahrzeug_prozesse'...")
        create_fahrzeug_prozesse_table(client, dataset_id)

        # 6. NEU: Tabelle: fahrzeug_aenderungen
        print("\n📝 Erstelle Tabelle 'fahrzeug_aenderungen' für Change-Tracking...")
        create_fahrzeug_aenderungen_table(client, dataset_id)

        # 7. NEU: Tabelle: cleanup_queue
        print("\n🧹 Erstelle Tabelle 'cleanup_queue' für verzögerte Bereinigungen...")
        create_cleanup_queue_table(client, dataset_id)
        
        # 8. Monitoring Views erstellen (verschiebt sich von 7 auf 8)
        print("\n📊 Erstelle Monitoring Views...")
        create_monitoring_views(client, dataset_id)
        
        # 9. Beispieldaten einfügen (verschiebt sich von 8 auf 9)
        print("\n📝 Füge Beispieldaten ein...")
        insert_sample_data(client, dataset_id)
        
        # 10. Verbindung testen
        print("\n🧪 Teste Verbindung...")
        test_connection(client, dataset_id)
        
        print("\n🎉 BigQuery Setup erfolgreich abgeschlossen!")
        print(f"   Dataset: {dataset_id}")
        print("   Tabellen:")
        print("   - fahrzeuge_stamm (Fahrzeugstammdaten)")
        print("   - fahrzeug_prozesse (Prozessverlauf)")
        print("   - fahrzeug_aenderungen (Änderungshistorie)")
        print("   - cleanup_queue (Verzögerte Bereinigungen)")  
        print("   Views:")
        print("   - v_prozess_pipeline (Prozess-Pipeline)")
        print("   - v_prozesslaufzeiten (Laufzeiten-Analyse)")
        print("   - v_prozess_gesamtlaufzeiten (Gesamtlaufzeiten)")
        print("   - v_sla_monitoring (SLA-Überwachung)")        
        print("   Beispieldaten: 3 Fahrzeuge mit Prozessen")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Fehler beim BigQuery Setup: {e}")
        return False

def create_fahrzeuge_stamm_table(client: bigquery.Client, dataset_id: str):
    """Erstellt die fahrzeuge_stamm Tabelle."""
    
    table_id = f"{dataset_id}.fahrzeuge_stamm"
    
    schema = [
        bigquery.SchemaField("fin", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("marke", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("modell", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("antriebsart", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("farbe", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("baujahr", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("datum_erstzulassung", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("kw_leistung", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("km_stand", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("anzahl_fahrzeugschluessel", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("bereifungsart", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("anzahl_vorhalter", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("ek_netto", "NUMERIC", mode="NULLABLE"),
        bigquery.SchemaField("besteuerungsart", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ersterfassung_datum", "DATETIME", mode="NULLABLE"),
        bigquery.SchemaField("aktiv", "BOOLEAN", mode="NULLABLE"),
        bigquery.SchemaField("erstellt_aus_email", "BOOLEAN", mode="NULLABLE"),
        bigquery.SchemaField("datenquelle_fahrzeug", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="created_at"
    )
    table.clustering_fields = ["fin", "marke"]
    
    try:
        table = client.create_table(table)
        print(f"✅ Tabelle '{table.table_id}' erstellt")
    except Conflict:
        print(f"ℹ️ Tabelle '{table_id}' existiert bereits")

def create_fahrzeug_prozesse_table(client: bigquery.Client, dataset_id: str):
    """Erstellt die fahrzeug_prozesse Tabelle."""
    
    table_id = f"{dataset_id}.fahrzeug_prozesse"
    
    schema = [
        bigquery.SchemaField("prozess_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("fin", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("prozess_typ", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("bearbeiter", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("prioritaet", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("anlieferung_datum", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("start_timestamp", "DATETIME", mode="NULLABLE"),
        bigquery.SchemaField("ende_timestamp", "DATETIME", mode="NULLABLE"),
        bigquery.SchemaField("dauer_minuten", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("standzeit_tage", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("sla_tage", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("sla_deadline_datum", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("tage_bis_sla_deadline", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("datenquelle", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("notizen", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("zusatz_daten", "STRING", mode="NULLABLE"),  # JSON als String
        bigquery.SchemaField("erstellt_am", "DATETIME", mode="NULLABLE"),
        bigquery.SchemaField("aktualisiert_am", "DATETIME", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="created_at"
    )
    table.clustering_fields = ["fin", "prozess_typ", "bearbeiter"]
    
    try:
        table = client.create_table(table)
        print(f"✅ Tabelle '{table.table_id}' erstellt")
    except Conflict:
        print(f"ℹ️ Tabelle '{table_id}' existiert bereits")

def create_fahrzeug_aenderungen_table(client: bigquery.Client, dataset_id: str):
    """Erstellt die fahrzeug_aenderungen Tabelle für Change-Tracking."""
    
    table_id = f"{dataset_id}.fahrzeug_aenderungen"
    
    schema = [
        bigquery.SchemaField("change_id", "STRING", mode="REQUIRED", 
                           description="Eindeutige ID der Änderung (FIN_FIELD_TIMESTAMP)"),
        bigquery.SchemaField("fin", "STRING", mode="REQUIRED",
                           description="Fahrzeugidentifizierungsnummer"),
        bigquery.SchemaField("field_name", "STRING", mode="REQUIRED",
                           description="Name des geänderten Feldes"),
        bigquery.SchemaField("old_value", "STRING", mode="NULLABLE",
                           description="Alter Wert (als String)"),
        bigquery.SchemaField("new_value", "STRING", mode="NULLABLE",
                           description="Neuer Wert (als String)"),
        bigquery.SchemaField("changed_at", "TIMESTAMP", mode="REQUIRED",
                           description="Zeitpunkt der Änderung"),
        bigquery.SchemaField("changed_by", "STRING", mode="NULLABLE",
                           description="Quelle/Benutzer der Änderung (z.B. email_import, api, manual)"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE",
                           description="Zeitpunkt der Protokollierung"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    
    # Partitionierung nach changed_at für effiziente Abfragen
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="changed_at"
    )
    
    # Clustering für optimierte Abfragen nach FIN und Feldname
    table.clustering_fields = ["fin", "field_name", "changed_by"]
    
    # Beschreibung
    table.description = "Audit-Log für Änderungen an Fahrzeugstammdaten"
    
    try:
        table = client.create_table(table)
        print(f"✅ Tabelle '{table.table_id}' für Change-Tracking erstellt")
    except Conflict:
        print(f"ℹ️ Tabelle '{table_id}' existiert bereits")

def create_cleanup_queue_table(client: bigquery.Client, dataset_id: str):
    """Erstellt die cleanup_queue Tabelle für verzögerte Bereinigungen."""
    
    table_id = f"{dataset_id}.cleanup_queue"
    
    schema = [
        bigquery.SchemaField("queue_id", "STRING", mode="REQUIRED", 
                           description="Eindeutige ID des Cleanup-Tasks"),
        bigquery.SchemaField("fin", "STRING", mode="REQUIRED",
                           description="Fahrzeugidentifizierungsnummer"),
        bigquery.SchemaField("cleanup_type", "STRING", mode="REQUIRED",
                           description="Art der Bereinigung (VERKAUFSABSCHLUSS, PROZESS_TIMEOUT, etc.)"),
        bigquery.SchemaField("scheduled_for", "DATETIME", mode="REQUIRED",
                           description="Geplanter Zeitpunkt für die Bereinigung"),
        bigquery.SchemaField("processed", "BOOLEAN", mode="NULLABLE", default_value_expression="FALSE",
                           description="Wurde der Task verarbeitet"),
        bigquery.SchemaField("processed_at", "DATETIME", mode="NULLABLE",
                           description="Zeitpunkt der Verarbeitung"),
        bigquery.SchemaField("error_message", "STRING", mode="NULLABLE",
                           description="Fehlermeldung falls aufgetreten"),
        bigquery.SchemaField("retry_count", "INTEGER", mode="NULLABLE", default_value_expression="0",
                           description="Anzahl der Wiederholungsversuche"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE", default_value_expression="CURRENT_TIMESTAMP()",
                           description="Erstellungszeitpunkt"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    
    # Partitionierung nach scheduled_for für effiziente Abfragen
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="scheduled_for"
    )
    
    # Clustering für optimierte Abfragen
    table.clustering_fields = ["fin", "cleanup_type", "processed"]
    
    # Beschreibung
    table.description = "Queue für verzögerte Bereinigungsaufgaben (z.B. nach Verkauf)"
    
    try:
        table = client.create_table(table)
        print(f"✅ Tabelle '{table.table_id}' für Cleanup-Queue erstellt")
    except Conflict:
        print(f"ℹ️ Tabelle '{table_id}' existiert bereits")

def create_monitoring_views(client: bigquery.Client, dataset_id: str):
    """Erstellt Views für Business Monitoring."""
    
    print("\n📊 Erstelle Monitoring Views...")
    
    # View 1: Aktuelle Fahrzeuge mit letztem Prozess
    view_id = f"{dataset_id}.v_fahrzeuge_aktuell"
    view_query = f"""
    WITH letzte_prozesse AS (
      SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY fin ORDER BY start_timestamp DESC) as rn
      FROM `{dataset_id}.fahrzeug_prozesse`
      WHERE ende_timestamp IS NULL  -- Nur offene Prozesse
    )
    SELECT 
      fs.fin,
      fs.marke,
      fs.modell,
      fs.baujahr,
      fs.farbe,
      fs.km_stand,
      fs.ek_netto,
      fp.prozess_typ,
      fp.status,
      fp.bearbeiter,
      fp.prioritaet,
      fp.start_timestamp,
      fp.sla_deadline_datum,
      DATETIME_DIFF(CURRENT_DATETIME(), fp.start_timestamp, DAY) as tage_im_prozess,
      DATE_DIFF(fp.sla_deadline_datum, CURRENT_DATE(), DAY) as tage_bis_deadline
    FROM `{dataset_id}.fahrzeuge_stamm` fs
    LEFT JOIN letzte_prozesse fp 
      ON fs.fin = fp.fin 
      AND fp.rn = 1  -- Nur der neueste Prozess
    WHERE fs.aktiv = TRUE
    """
    
    try:
        view = bigquery.Table(view_id)
        view.view_query = view_query
        client.create_table(view)
        print(f"✅ View 'v_fahrzeuge_aktuell' erstellt")
    except Conflict:
        view = client.get_table(view_id)
        view.view_query = view_query
        client.update_table(view, ["view_query"])
        print(f"✅ View 'v_fahrzeuge_aktuell' aktualisiert")
    
    # View 2: Prozess-Pipeline (mit nur aktuellem Prozess pro Fahrzeug)
    view_id = f"{dataset_id}.v_prozess_pipeline"
    view_query = f"""
    WITH letzte_prozesse AS (
      SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY fin ORDER BY start_timestamp DESC) as rn
      FROM `{dataset_id}.fahrzeug_prozesse`
      WHERE ende_timestamp IS NULL
    )
    SELECT 
      prozess_typ,
      CASE 
        WHEN UPPER(status) IN ('WARTESCHLANGE', 'GESTARTET', 'ANGELEGT', 'WARTEND', 'NEU') 
          THEN 'WARTESCHLANGE'
        WHEN UPPER(status) IN ('AKTIV', 'IN BEARBEITUNG', 'LAUFEND', 'IN ARBEIT')
          THEN 'AKTIV'
        WHEN UPPER(status) IN ('BEENDET', 'ABGESCHLOSSEN', 'FERTIG', 'ERLEDIGT')
          THEN 'BEENDET'
        ELSE UPPER(status)
      END as status_normalisiert,
      COUNT(DISTINCT fin) as anzahl_fahrzeuge,
      COUNT(DISTINCT CASE WHEN bearbeiter IS NOT NULL THEN fin END) as mit_bearbeiter,
      COUNT(DISTINCT CASE WHEN bearbeiter IS NULL THEN fin END) as ohne_bearbeiter,
      AVG(DATE_DIFF(CURRENT_DATE(), DATE(start_timestamp), DAY)) as avg_tage_im_prozess,
      COUNT(CASE WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) < 0 THEN 1 END) as sla_verletzt,
      COUNT(CASE WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) BETWEEN 0 AND 1 THEN 1 END) as sla_kritisch
    FROM letzte_prozesse
    WHERE rn = 1  -- Nur der neueste Prozess pro Fahrzeug
    GROUP BY prozess_typ, status_normalisiert
    ORDER BY prozess_typ, status_normalisiert
    """
    
    try:
        view = bigquery.Table(view_id)
        view.view_query = view_query
        client.create_table(view)
        print(f"✅ View 'v_prozess_pipeline' erstellt")
    except Conflict:
        view = client.get_table(view_id)
        view.view_query = view_query
        client.update_table(view, ["view_query"])
        print(f"✅ View 'v_prozess_pipeline' aktualisiert")
    
    # View 3: Prozesslaufzeiten (für abgeschlossene Prozesse)
    view_id = f"{dataset_id}.v_prozesslaufzeiten"
    view_query = f"""
    SELECT 
      prozess_typ,
      CASE 
        WHEN UPPER(status) IN ('WARTESCHLANGE', 'GESTARTET', 'ANGELEGT', 'WARTEND') 
          THEN 'WARTESCHLANGE'
        WHEN UPPER(status) IN ('AKTIV', 'IN BEARBEITUNG', 'LAUFEND')
          THEN 'AKTIV'
        WHEN UPPER(status) IN ('BEENDET', 'ABGESCHLOSSEN', 'FERTIG', 'ERLEDIGT')
          THEN 'BEENDET'
        ELSE UPPER(status)
      END as status_normalisiert,
      
      -- Zeitraum-Kategorisierung
      CASE 
        WHEN DATE(start_timestamp) = CURRENT_DATE() THEN 'Heute'
        WHEN DATE(start_timestamp) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) THEN 'Gestern'
        WHEN DATE_TRUNC(start_timestamp, WEEK) = DATE_TRUNC(CURRENT_DATE(), WEEK) THEN 'Diese Woche'
        WHEN DATE_TRUNC(start_timestamp, WEEK) = DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 WEEK), WEEK) THEN 'Letzte Woche'
        WHEN DATE_TRUNC(start_timestamp, MONTH) = DATE_TRUNC(CURRENT_DATE(), MONTH) THEN 'Dieser Monat'
        ELSE 'Älter'
      END as zeitraum,
      
      -- Laufzeit-Metriken (nur für abgeschlossene Prozesse)
      AVG(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)) as avg_laufzeit_minuten,
      MIN(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)) as min_laufzeit_minuten,
      MAX(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)) as max_laufzeit_minuten,
      APPROX_QUANTILES(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE), 100)[OFFSET(50)] as median_laufzeit_minuten,
      COUNT(*) as anzahl_messungen
      
    FROM `{dataset_id}.fahrzeug_prozesse`
    WHERE ende_timestamp IS NOT NULL
      AND start_timestamp IS NOT NULL
      AND status IN ('BEENDET', 'Abgeschlossen', 'Fertig', 'Erledigt')
    GROUP BY prozess_typ, status_normalisiert, zeitraum
    """
    
    try:
        view = bigquery.Table(view_id)
        view.view_query = view_query
        client.create_table(view)
        print(f"✅ View 'v_prozesslaufzeiten' erstellt")
    except Conflict:
        view = client.get_table(view_id)
        view.view_query = view_query
        client.update_table(view, ["view_query"])
        print(f"✅ View 'v_prozesslaufzeiten' aktualisiert")
    
    # View 4: Prozess-Gesamtlaufzeiten
    view_id = f"{dataset_id}.v_prozess_gesamtlaufzeiten"
    view_query = f"""
    WITH prozess_laufzeiten AS (
      SELECT 
        fin,
        prozess_typ,
        SUM(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)) as gesamt_laufzeit_minuten,
        MIN(start_timestamp) as prozess_start,
        MAX(ende_timestamp) as prozess_ende,
        COUNT(*) as anzahl_teilprozesse
      FROM `{dataset_id}.fahrzeug_prozesse`
      WHERE ende_timestamp IS NOT NULL
        AND status IN ('BEENDET', 'Abgeschlossen', 'Fertig', 'Erledigt')
      GROUP BY fin, prozess_typ
    )
    SELECT 
      prozess_typ,
      DATE_TRUNC(prozess_start, WEEK) as woche,
      AVG(gesamt_laufzeit_minuten) as avg_gesamtlaufzeit_minuten,
      AVG(gesamt_laufzeit_minuten/60.0) as avg_gesamtlaufzeit_stunden,
      APPROX_QUANTILES(gesamt_laufzeit_minuten, 100)[OFFSET(50)] as median_laufzeit_minuten,
      COUNT(*) as anzahl_prozesse
    FROM prozess_laufzeiten
    GROUP BY prozess_typ, woche
    ORDER BY prozess_typ, woche DESC
    """
    
    try:
        view = bigquery.Table(view_id)
        view.view_query = view_query
        client.create_table(view)
        print(f"✅ View 'v_prozess_gesamtlaufzeiten' erstellt")
    except Conflict:
        view = client.get_table(view_id)
        view.view_query = view_query
        client.update_table(view, ["view_query"])
        print(f"✅ View 'v_prozess_gesamtlaufzeiten' aktualisiert")
    
    # View 5: SLA-Monitoring (nur aktuelle Prozesse)
    view_id = f"{dataset_id}.v_sla_monitoring"
    view_query = f"""
    WITH letzte_prozesse AS (
      SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY fin ORDER BY start_timestamp DESC) as rn
      FROM `{dataset_id}.fahrzeug_prozesse`
      WHERE ende_timestamp IS NULL
    ),
    prozess_metriken AS (
      SELECT 
        fin,
        prozess_typ,
        status,
        bearbeiter,
        start_timestamp,
        sla_deadline_datum,
        DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) as tage_bis_deadline,
        CASE 
          WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) < 0 THEN 'VERLETZT'
          WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) <= 1 THEN 'KRITISCH'
          WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) <= 3 THEN 'WARNUNG'
          ELSE 'OK'
        END as sla_status
      FROM letzte_prozesse
      WHERE rn = 1
    )
    SELECT 
      pm.*,
      fs.marke,
      fs.modell,
      fs.ek_netto,
      DATETIME_DIFF(CURRENT_DATETIME(), pm.start_timestamp, DAY) as tage_im_prozess
    FROM prozess_metriken pm
    JOIN `{dataset_id}.fahrzeuge_stamm` fs ON pm.fin = fs.fin
    WHERE pm.sla_status IN ('VERLETZT', 'KRITISCH', 'WARNUNG')
    ORDER BY pm.tage_bis_deadline ASC
    """
    
    try:
        view = bigquery.Table(view_id)
        view.view_query = view_query
        client.create_table(view)
        print(f"✅ View 'v_sla_monitoring' erstellt")
    except Conflict:
        view = client.get_table(view_id)
        view.view_query = view_query
        client.update_table(view, ["view_query"])
        print(f"✅ View 'v_sla_monitoring' aktualisiert")

    print("✅ Alle Monitoring Views erfolgreich erstellt/aktualisiert")

def insert_test_cleanup_task(client: bigquery.Client, dataset_id: str):
    """Fügt einen Test-Cleanup-Task ein."""
    
    from datetime import datetime, timedelta
    import uuid
    
    test_task = {
        'queue_id': str(uuid.uuid4()),
        'fin': 'TEST_CLEANUP_FIN_12345',
        'cleanup_type': 'VERKAUFSABSCHLUSS',
        'scheduled_for': (datetime.now() + timedelta(hours=2)).isoformat(),
        'processed': False,
        'retry_count': 0,
        'created_at': datetime.now().isoformat()
    }
    
    cleanup_table = client.get_table(f"{dataset_id}.cleanup_queue")
    errors = client.insert_rows_json(cleanup_table, [test_task])
    
    if errors:
        print(f"⚠️ Fehler beim Einfügen des Test-Cleanup-Tasks: {errors}")
    else:
        print(f"✅ Test-Cleanup-Task eingefügt (läuft in 2 Stunden)")
        print(f"   FIN: {test_task['fin']}")
        print(f"   Geplant für: {test_task['scheduled_for']}")

def insert_sample_data(client: bigquery.Client, dataset_id: str):
    """Fügt Beispieldaten ein."""
    
    from datetime import datetime
    
    # Fahrzeugstammdaten
    fahrzeuge = [
        {
            'fin': 'WVWZZZ1JZ8W123456',
            'marke': 'Volkswagen',
            'modell': 'Golf',
            'antriebsart': 'Benzin',
            'farbe': 'Schwarz',
            'baujahr': 2023,
            'ek_netto': 18500.00,
            'aktiv': True,
            'datenquelle_fahrzeug': 'setup_script',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        },
        {
            'fin': 'WBA12345678901234',
            'marke': 'BMW',
            'modell': '320d',
            'antriebsart': 'Diesel',
            'farbe': 'Weiß',
            'baujahr': 2022,
            'ek_netto': 28500.00,
            'aktiv': True,
            'datenquelle_fahrzeug': 'setup_script',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        },
        {
            'fin': 'WDD12345678901234',
            'marke': 'Mercedes-Benz',
            'modell': 'C-Klasse',
            'antriebsart': 'Hybrid',
            'farbe': 'Silber',
            'baujahr': 2024,
            'ek_netto': 35500.00,
            'aktiv': True,
            'datenquelle_fahrzeug': 'setup_script',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    ]
    
    # Fahrzeugprozesse
    prozesse = [
        {
            'prozess_id': 'AUF_123456_20250102_143000',
            'fin': 'WVWZZZ1JZ8W123456',
            'prozess_typ': 'Aufbereitung',
            'status': 'In Bearbeitung',
            'bearbeiter': 'Thomas Küfner',
            'prioritaet': 3,
            'sla_tage': 3,
            'datenquelle': 'setup_script',
            'erstellt_am': datetime.now().isoformat(),
            'aktualisiert_am': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        },
        {
            'prozess_id': 'FOT_901234_20250102_144500',
            'fin': 'WBA12345678901234',
            'prozess_typ': 'Foto',
            'status': 'Wartend',
            'bearbeiter': 'Maximilian Reinhardt',
            'prioritaet': 4,
            'sla_tage': 1,
            'datenquelle': 'setup_script',
            'erstellt_am': datetime.now().isoformat(),
            'aktualisiert_am': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        },
        {
            'prozess_id': 'VER_901234_20250102_145000',
            'fin': 'WDD12345678901234',
            'prozess_typ': 'Verkauf',
            'status': 'Aktiv',
            'bearbeiter': 'Thomas Küfner',
            'prioritaet': 2,
            'sla_tage': 30,
            'datenquelle': 'setup_script',
            'erstellt_am': datetime.now().isoformat(),
            'aktualisiert_am': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    ]
    
    # Fahrzeuge einfügen
    fahrzeuge_table = client.get_table(f"{dataset_id}.fahrzeuge_stamm")
    errors = client.insert_rows_json(fahrzeuge_table, fahrzeuge)
    if errors:
        print(f"⚠️ Fehler beim Einfügen von Fahrzeugen: {errors}")
    else:
        print(f"✅ {len(fahrzeuge)} Fahrzeuge eingefügt")
    
    # Prozesse einfügen
    prozesse_table = client.get_table(f"{dataset_id}.fahrzeug_prozesse")
    errors = client.insert_rows_json(prozesse_table, prozesse)
    if errors:
        print(f"⚠️ Fehler beim Einfügen von Prozessen: {errors}")
    else:
        print(f"✅ {len(prozesse)} Prozesse eingefügt")

def test_connection(client: bigquery.Client, dataset_id: str):
    """Testet die BigQuery-Verbindung."""
    
    try:
        # Test-Query ausführen
        query = f"""
        SELECT 
            COUNT(*) as fahrzeug_count
        FROM `{dataset_id}.fahrzeuge_stamm`
        WHERE aktiv = TRUE
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        for row in results:
            print(f"✅ Verbindungstest erfolgreich: {row.fahrzeug_count} aktive Fahrzeuge gefunden")
            
    except Exception as e:
        print(f"❌ Verbindungstest fehlgeschlagen: {e}")

if __name__ == "__main__":
    # Environment laden
    from dotenv import load_dotenv
    load_dotenv()
    
    print("BigQuery Setup Script")
    print("Stelle sicher, dass folgende ENV-Variablen gesetzt sind:")
    print("- GOOGLE_CLOUD_PROJECT")
    print("- GOOGLE_APPLICATION_CREDENTIALS") 
    print("- BIGQUERY_DATASET (optional, default: autohaus)")
    print()
    
    if input("Fortfahren? (y/N): ").lower() != 'y':
        print("Setup abgebrochen.")
        sys.exit(0)
    
    success = setup_bigquery()
    
    if success:
        print("\n🎉 Setup abgeschlossen!")
        print("Du kannst jetzt die RA Autohaus Tracker App starten.")
    else:
        print("\n❌ Setup fehlgeschlagen!")
        print("Prüfe die Fehlermeldungen oben.")