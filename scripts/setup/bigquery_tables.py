#!/usr/bin/env python3
"""
BigQuery Tabellen-Definitionen für RA Autohaus Tracker
Reinhardt Automobile GmbH

Zentrale Sammlung aller Tabellen-Definitionen.
Wird von setup_bigquery.py verwendet.
"""

from google.cloud import bigquery
from google.cloud.exceptions import Conflict
from datetime import datetime


def create_fahrzeuge_stamm_table(client: bigquery.Client, dataset_id: str):
    """Erstellt die fahrzeuge_stamm Tabelle."""
    
    table_id = f"{dataset_id}.fahrzeuge_stamm"
    
    schema = [
        bigquery.SchemaField("fin", "STRING", mode="REQUIRED", 
                           description="Fahrzeugidentifizierungsnummer (17-stellig)"),
        bigquery.SchemaField("marke", "STRING", mode="NULLABLE",
                           description="Fahrzeugmarke"),
        bigquery.SchemaField("modell", "STRING", mode="NULLABLE",
                           description="Fahrzeugmodell"),
        bigquery.SchemaField("antriebsart", "STRING", mode="NULLABLE",
                           description="Antriebsart (Benzin, Diesel, Hybrid, Elektro)"),
        bigquery.SchemaField("farbe", "STRING", mode="NULLABLE",
                           description="Fahrzeugfarbe"),
        bigquery.SchemaField("baujahr", "INTEGER", mode="NULLABLE",
                           description="Baujahr des Fahrzeugs"),
        bigquery.SchemaField("datum_erstzulassung", "DATE", mode="NULLABLE",
                           description="Datum der Erstzulassung"),
        bigquery.SchemaField("kw_leistung", "INTEGER", mode="NULLABLE",
                           description="Motorleistung in KW"),
        bigquery.SchemaField("km_stand", "INTEGER", mode="NULLABLE",
                           description="Kilometerstand"),
        bigquery.SchemaField("anzahl_fahrzeugschluessel", "INTEGER", mode="NULLABLE",
                           description="Anzahl vorhandener Fahrzeugschlüssel"),
        bigquery.SchemaField("bereifungsart", "STRING", mode="NULLABLE",
                           description="Art der Bereifung (Sommer, Winter, Allwetter)"),
        bigquery.SchemaField("anzahl_vorhalter", "INTEGER", mode="NULLABLE",
                           description="Anzahl der Vorbesitzer"),
        bigquery.SchemaField("ek_netto", "NUMERIC", mode="NULLABLE",
                           description="Einkaufspreis netto in EUR"),
        bigquery.SchemaField("besteuerungsart", "STRING", mode="NULLABLE",
                           description="Besteuerungsart (Differenzbesteuert, Regelbesteuert)"),
        bigquery.SchemaField("ersterfassung_datum", "DATETIME", mode="NULLABLE",
                           description="Zeitpunkt der Ersterfassung im System"),
        bigquery.SchemaField("aktiv", "BOOLEAN", mode="NULLABLE",
                           description="Ist das Fahrzeug aktiv im Bestand"),
        bigquery.SchemaField("erstellt_aus_email", "BOOLEAN", mode="NULLABLE",
                           description="Wurde aus Email-Import erstellt"),
        bigquery.SchemaField("datenquelle_fahrzeug", "STRING", mode="NULLABLE",
                           description="Quelle der Fahrzeugdaten (api, email, manual, setup)"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE",
                           description="Erstellungszeitpunkt"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE",
                           description="Letzter Aktualisierungszeitpunkt"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="created_at",
        expiration_ms=None  # Keine automatische Löschung
    )
    table.clustering_fields = ["fin", "marke"]
    table.description = "Stammdaten aller Fahrzeuge im Bestand"
    
    try:
        table = client.create_table(table)
        print(f"✅ Tabelle '{table.table_id}' erstellt")
    except Conflict:
        print(f"ℹ️ Tabelle '{table_id}' existiert bereits")


def create_fahrzeug_prozesse_table(client: bigquery.Client, dataset_id: str):
    """Erstellt die fahrzeug_prozesse Tabelle."""
    
    table_id = f"{dataset_id}.fahrzeug_prozesse"
    
    schema = [
        bigquery.SchemaField("prozess_id", "STRING", mode="REQUIRED",
                           description="Eindeutige Prozess-ID (TYP_FIN_TIMESTAMP)"),
        bigquery.SchemaField("fin", "STRING", mode="REQUIRED",
                           description="Fahrzeugidentifizierungsnummer"),
        bigquery.SchemaField("prozess_typ", "STRING", mode="REQUIRED",
                           description="Art des Prozesses (Einkauf, Aufbereitung, Foto, Werkstatt, Verkauf)"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED",
                           description="Aktueller Status des Prozesses"),
        bigquery.SchemaField("bearbeiter", "STRING", mode="NULLABLE",
                           description="Zugewiesener Bearbeiter"),
        bigquery.SchemaField("prioritaet", "INTEGER", mode="NULLABLE",
                           description="Priorität (1=sehr hoch, 5=sehr niedrig)"),
        bigquery.SchemaField("anlieferung_datum", "DATE", mode="NULLABLE",
                           description="Datum der Fahrzeuganlieferung"),
        bigquery.SchemaField("start_timestamp", "DATETIME", mode="NULLABLE",
                           description="Startzeitpunkt des Prozesses"),
        bigquery.SchemaField("ende_timestamp", "DATETIME", mode="NULLABLE",
                           description="Endzeitpunkt des Prozesses"),
        bigquery.SchemaField("dauer_minuten", "INTEGER", mode="NULLABLE",
                           description="Prozessdauer in Minuten"),
        bigquery.SchemaField("standzeit_tage", "INTEGER", mode="NULLABLE",
                           description="Standzeit in Tagen"),
        bigquery.SchemaField("sla_tage", "INTEGER", mode="NULLABLE",
                           description="SLA-Vorgabe in Tagen"),
        bigquery.SchemaField("sla_deadline_datum", "DATE", mode="NULLABLE",
                           description="SLA-Deadline"),
        bigquery.SchemaField("tage_bis_sla_deadline", "INTEGER", mode="NULLABLE",
                           description="Verbleibende Tage bis SLA-Deadline"),
        bigquery.SchemaField("individuelle_deadline", "DATETIME", mode="NULLABLE",
                           description="Individuelle Deadline (überschreibt Standard-SLA)"),
        bigquery.SchemaField("individuelle_deadline_gesetzt", "BOOLEAN", mode="NULLABLE",
                           description="Wurde eine individuelle Deadline gesetzt"),
        bigquery.SchemaField("datenquelle", "STRING", mode="NULLABLE",
                           description="Quelle der Prozessdaten (zapier, email, api, manual)"),
        bigquery.SchemaField("notizen", "STRING", mode="NULLABLE",
                           description="Notizen zum Prozess"),
        bigquery.SchemaField("zusatz_daten", "STRING", mode="NULLABLE",
                           description="Zusätzliche Daten als JSON-String"),
        bigquery.SchemaField("erstellt_am", "DATETIME", mode="NULLABLE",
                           description="Erstellungszeitpunkt des Prozesses"),
        bigquery.SchemaField("aktualisiert_am", "DATETIME", mode="NULLABLE",
                           description="Letzter Aktualisierungszeitpunkt"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE",
                           description="Datensatz-Erstellungszeitpunkt"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE",
                           description="Datensatz-Aktualisierungszeitpunkt"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="created_at",
        expiration_ms=None
    )
    table.clustering_fields = ["fin", "prozess_typ", "bearbeiter"]
    table.description = "Prozessverlauf und -status für alle Fahrzeuge"
    
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
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="changed_at",
        expiration_ms=7776000000  # 90 Tage Retention
    )
    table.clustering_fields = ["fin", "field_name", "changed_by"]
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
        bigquery.SchemaField("prozess_id", "STRING", mode="REQUIRED", 
                           description="Prozess ID die beendet werden soll"),                           
        bigquery.SchemaField("fin", "STRING", mode="REQUIRED",
                           description="Fahrzeugidentifizierungsnummer"),
        bigquery.SchemaField("cleanup_type", "STRING", mode="REQUIRED",
                           description="Art der Bereinigung (VERKAUFSABSCHLUSS, PROZESS_TIMEOUT, etc.)"),
        bigquery.SchemaField("scheduled_for", "DATETIME", mode="REQUIRED",
                           description="Geplanter Zeitpunkt für die Bereinigung"),
        bigquery.SchemaField("processed", "BOOLEAN", mode="NULLABLE",
                           description="Wurde der Task verarbeitet"),
        bigquery.SchemaField("processed_at", "DATETIME", mode="NULLABLE",
                           description="Zeitpunkt der Verarbeitung"),
        bigquery.SchemaField("error_message", "STRING", mode="NULLABLE",
                           description="Zeitpunkt der Verarbeitung"),
        bigquery.SchemaField("zusatz_daten", "STRING", mode="NULLABLE",                             
                           description="JSON mit zusätzlichen Daten"),
        bigquery.SchemaField("retry_count", "INTEGER", mode="NULLABLE",
                           description="Anzahl der Wiederholungsversuche"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE",
                           description="Erstellungszeitpunkt"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="scheduled_for",
        expiration_ms=2592000000  # 30 Tage Retention
    )
    table.clustering_fields = ["fin", "cleanup_type", "processed"]
    table.description = "Queue für verzögerte Bereinigungsaufgaben (z.B. nach Verkauf)"
    
    try:
        table = client.create_table(table)
        print(f"✅ Tabelle '{table.table_id}' für Cleanup-Queue erstellt")
    except Conflict:
        print(f"ℹ️ Tabelle '{table_id}' existiert bereits")


def create_all_tables(client: bigquery.Client, dataset_id: str):
    """Erstellt alle Tabellen."""
    
    print("\n📋 Erstelle Tabellen...")
    
    # 1. Fahrzeuge Stammdaten
    print("\n🚗 Erstelle Tabelle 'fahrzeuge_stamm'...")
    create_fahrzeuge_stamm_table(client, dataset_id)
    
    # 2. Fahrzeug Prozesse
    print("\n⚙️ Erstelle Tabelle 'fahrzeug_prozesse'...")
    create_fahrzeug_prozesse_table(client, dataset_id)
    
    # 3. Fahrzeug Änderungen (Audit-Log)
    print("\n📝 Erstelle Tabelle 'fahrzeug_aenderungen'...")
    create_fahrzeug_aenderungen_table(client, dataset_id)
    
    # 4. Cleanup Queue
    print("\n🧹 Erstelle Tabelle 'cleanup_queue'...")
    create_cleanup_queue_table(client, dataset_id)
    
    print("\n✅ Alle Tabellen erfolgreich erstellt/überprüft")


def insert_sample_data(client: bigquery.Client, dataset_id: str):
    """Fügt Beispieldaten ein, inkl. Werkstatt-Prozesse."""
    
    from datetime import datetime, timedelta
    
    print("\n📝 Füge Beispieldaten ein...")
    
    now = datetime.now()
    
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
            'km_stand': 15000,
            'aktiv': True,
            'datenquelle_fahrzeug': 'setup_script',
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        },
        {
            'fin': 'WBA12345678901234',
            'marke': 'BMW',
            'modell': '320d',
            'antriebsart': 'Diesel',
            'farbe': 'Weiß',
            'baujahr': 2022,
            'ek_netto': 28500.00,
            'km_stand': 32000,
            'aktiv': True,
            'datenquelle_fahrzeug': 'setup_script',
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        },
        {
            'fin': 'WDD12345678901234',
            'marke': 'Mercedes-Benz',
            'modell': 'C-Klasse',
            'antriebsart': 'Hybrid',
            'farbe': 'Silber',
            'baujahr': 2024,
            'ek_netto': 35500.00,
            'km_stand': 8000,
            'aktiv': True,
            'datenquelle_fahrzeug': 'setup_script',
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        },
        {
            'fin': 'WAUZZZ8V5KA123456',
            'marke': 'Audi',
            'modell': 'A4',
            'antriebsart': 'Benzin',
            'farbe': 'Grau',
            'baujahr': 2021,
            'ek_netto': 22000.00,
            'km_stand': 45000,
            'aktiv': True,
            'datenquelle_fahrzeug': 'setup_script',
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
    ]
    
    # Prozesse mit verschiedenen Status
    prozesse = [
        # Überfälliger Werkstatt-Prozess
        {
            'prozess_id': f'WER_123456_{now.strftime("%Y%m%d_%H%M%S")}',
            'fin': 'WVWZZZ1JZ8W123456',
            'prozess_typ': 'Werkstatt',
            'status': 'In Bearbeitung',
            'bearbeiter': 'Thomas Küfner',
            'prioritaet': 2,
            'start_timestamp': (now - timedelta(days=10)).isoformat(),
            'sla_tage': 7,
            'sla_deadline_datum': (now - timedelta(days=3)).date().isoformat(),
            'tage_bis_sla_deadline': -3,
            'standzeit_tage': 10,
            'notizen': 'Getriebeproblem - Ersatzteil bestellt',
            'datenquelle': 'setup_script',
            'erstellt_am': (now - timedelta(days=10)).isoformat(),
            'aktualisiert_am': now.isoformat(),
            'created_at': (now - timedelta(days=10)).isoformat(),
            'updated_at': now.isoformat()
        },
        # Kritischer Werkstatt-Prozess
        {
            'prozess_id': f'WER_901234_{now.strftime("%Y%m%d_%H%M%S")}',
            'fin': 'WBA12345678901234',
            'prozess_typ': 'Werkstatt',
            'status': 'Wartend auf Teile',
            'bearbeiter': 'Maximilian Reinhardt',
            'prioritaet': 1,
            'start_timestamp': (now - timedelta(days=6)).isoformat(),
            'sla_tage': 7,
            'sla_deadline_datum': (now + timedelta(days=1)).date().isoformat(),
            'tage_bis_sla_deadline': 1,
            'standzeit_tage': 6,
            'notizen': 'Bremsen komplett - warten auf Bremsscheiben',
            'datenquelle': 'setup_script',
            'erstellt_am': (now - timedelta(days=6)).isoformat(),
            'aktualisiert_am': now.isoformat(),
            'created_at': (now - timedelta(days=6)).isoformat(),
            'updated_at': now.isoformat()
        },
        # Aufbereitung-Prozess
        {
            'prozess_id': f'AUF_567890_{now.strftime("%Y%m%d_%H%M%S")}',
            'fin': 'WDD12345678901234',
            'prozess_typ': 'Aufbereitung',
            'status': 'In Bearbeitung',
            'bearbeiter': 'Thomas Küfner',
            'prioritaet': 3,
            'start_timestamp': (now - timedelta(days=2)).isoformat(),
            'sla_tage': 3,
            'sla_deadline_datum': (now + timedelta(days=1)).date().isoformat(),
            'tage_bis_sla_deadline': 1,
            'standzeit_tage': 2,
            'notizen': 'Innenreinigung und Politur',
            'datenquelle': 'setup_script',
            'erstellt_am': (now - timedelta(days=2)).isoformat(),
            'aktualisiert_am': now.isoformat(),
            'created_at': (now - timedelta(days=2)).isoformat(),
            'updated_at': now.isoformat()
        },
        # Foto-Prozess
        {
            'prozess_id': f'FOT_112233_{now.strftime("%Y%m%d_%H%M%S")}',
            'fin': 'WAUZZZ8V5KA123456',
            'prozess_typ': 'Foto',
            'status': 'Wartend',
            'bearbeiter': None,
            'prioritaet': 4,
            'start_timestamp': (now - timedelta(hours=6)).isoformat(),
            'sla_tage': 1,
            'sla_deadline_datum': (now + timedelta(hours=18)).date().isoformat(),
            'tage_bis_sla_deadline': 0,
            'standzeit_tage': 0,
            'notizen': 'Fahrzeug bereit für Fotografie',
            'datenquelle': 'setup_script',
            'erstellt_am': (now - timedelta(hours=6)).isoformat(),
            'aktualisiert_am': now.isoformat(),
            'created_at': (now - timedelta(hours=6)).isoformat(),
            'updated_at': now.isoformat()
        }
    ]
    
    try:
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
            print("   • 2 Werkstatt-Prozesse (1 überfällig, 1 kritisch)")
            print("   • 1 Aufbereitung-Prozess")
            print("   • 1 Foto-Prozess")
            
    except Exception as e:
        print(f"⚠️ Fehler beim Einfügen der Beispieldaten: {e}")


def test_connection(client: bigquery.Client, dataset_id: str):
    """Testet die BigQuery-Verbindung und zählt Datensätze."""
    
    print("\n🧪 Teste Verbindung und Daten...")
    
    try:
        # Test Fahrzeuge
        query = f"""
        SELECT 
            COUNT(*) as fahrzeug_count,
            COUNT(DISTINCT marke) as marken_count
        FROM `{dataset_id}.fahrzeuge_stamm`
        WHERE aktiv = TRUE
        """
        
        query_job = client.query(query)
        results = list(query_job.result())
        
        if results:
            row = results[0]
            print(f"✅ Fahrzeuge: {row.fahrzeug_count} aktive Fahrzeuge, {row.marken_count} Marken")
        
        # Test Prozesse
        query = f"""
        SELECT 
            prozess_typ,
            COUNT(*) as anzahl
        FROM `{dataset_id}.fahrzeug_prozesse`
        WHERE ende_timestamp IS NULL
        GROUP BY prozess_typ
        ORDER BY anzahl DESC
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        print("✅ Aktive Prozesse:")
        for row in results:
            print(f"   • {row.prozess_typ}: {row.anzahl}")
            
    except Exception as e:
        print(f"❌ Verbindungstest fehlgeschlagen: {e}")