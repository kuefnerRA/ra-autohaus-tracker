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
        if service_account:
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
        
        # 6. Beispieldaten einfügen
        print("\n📝 Füge Beispieldaten ein...")
        insert_sample_data(client, dataset_id)
        
        # 7. Verbindung testen
        print("\n🧪 Teste Verbindung...")
        test_connection(client, dataset_id)
        
        print("\n🎉 BigQuery Setup erfolgreich abgeschlossen!")
        print(f"   Dataset: {dataset_id}")
        print("   Tabellen: fahrzeuge_stamm, fahrzeug_prozesse")
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