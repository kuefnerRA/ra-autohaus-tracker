#!/usr/bin/env python3
"""
BigQuery Setup Script für RA Autohaus Tracker
Reinhardt Automobile GmbH

Hauptscript für das komplette Setup von BigQuery Dataset, Tabellen und Views.
Nutzt die modularisierten Definitionen aus bigquery_tables.py und bigquery_views.py.
"""

import os
import sys
from google.cloud import bigquery
from google.cloud.exceptions import Conflict, NotFound
from dotenv import load_dotenv

# Import der modularisierten Komponenten
from bigquery_tables import create_all_tables, insert_sample_data, test_connection
from bigquery_views import create_all_views


def setup_bigquery():
    """Komplettes BigQuery Setup - orchestriert alle Komponenten."""
    
    print("🚀 BigQuery Setup für RA Autohaus Tracker")
    print("=" * 50)
    
    # 1. Konfiguration prüfen
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    dataset_name = os.getenv('BIGQUERY_DATASET', 'autohaus')
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT nicht gesetzt!")
        print("   Setze in .env: GOOGLE_CLOUD_PROJECT=deine-projekt-id")
        return False
    
    # Credentials prüfen
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    
    if credentials_path and os.path.exists(credentials_path):
        auth_method = f"JSON Key: {credentials_path}"
    elif os.path.exists(adc_path):
        auth_method = f"ADC: {adc_path}"
    else:
        print("❌ Keine Google Cloud Credentials gefunden!")
        print("   Führe aus: gcloud auth application-default login")
        print("   Oder setze GOOGLE_APPLICATION_CREDENTIALS auf den Pfad zu deinem Service Account Key")
        return False

    print(f"✅ Projekt: {project_id}")
    print(f"✅ Dataset: {dataset_name}")
    print(f"✅ Credentials: {auth_method}")
    
    try:
        # 2. BigQuery Client initialisieren
        print("\n🔗 Verbinde zu BigQuery...")
        
        service_account = os.getenv('GOOGLE_SERVICE_ACCOUNT')
        
        # Optional: Service Account Impersonation
        if service_account and os.getenv('USE_IMPERSONATION', 'false').lower() == 'true':
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
            print(f"✅ Using impersonated Service Account: {service_account}")
        else:
            client = bigquery.Client(project=project_id)
            print("✅ Using Application Default Credentials")
                
        # 3. Dataset erstellen oder prüfen
        print(f"\n📊 Erstelle/prüfe Dataset '{dataset_name}'...")
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
        
        # 4. Tabellen erstellen
        create_all_tables(client, dataset_id)
        
        # 5. Views erstellen
        create_all_views(client, dataset_id)
        
        # 6. Optional: Beispieldaten einfügen
        if input("\n📝 Beispieldaten einfügen? (y/N): ").lower() == 'y':
            insert_sample_data(client, dataset_id)
        else:
            print("ℹ️ Beispieldaten übersprungen")
        
        # 7. Verbindung und Daten testen
        test_connection(client, dataset_id)
        
        # 8. Zusammenfassung
        print("\n" + "=" * 50)
        print("🎉 BigQuery Setup erfolgreich abgeschlossen!")
        print("=" * 50)
        
        print(f"\n📊 Dataset: {dataset_id}")
        
        print("\n📋 Tabellen:")
        print("   • fahrzeuge_stamm - Fahrzeugstammdaten")
        print("   • fahrzeug_prozesse - Prozessverlauf")
        print("   • fahrzeug_aenderungen - Änderungshistorie")
        print("   • cleanup_queue - Verzögerte Bereinigungen")
        
        print("\n👀 Views:")
        print("   Standard-Monitoring:")
        print("   • v_fahrzeuge_aktuell")
        print("   • v_prozess_pipeline")
        print("   • v_prozesslaufzeiten")
        print("   • v_prozess_gesamtlaufzeiten")
        print("   • v_sla_monitoring")
        print("   Werkstatt-Dashboard:")
        print("   • v_werkstatt_prozesse_aktiv")
        print("   • v_werkstatt_kpis")
        print("   • v_werkstatt_bearbeiter_auslastung")
        
        print("\n🚀 Nächste Schritte:")
        print("   1. Prüfe die Strukturen in der BigQuery Console")
        print("   2. Starte die API mit: python src/main.py")
        print("   3. Erstelle Dashboards in Looker Studio")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Fehler beim BigQuery Setup: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Haupteinstiegspunkt mit Benutzerinteraktion."""
    
    print("RA Autohaus Tracker - BigQuery Setup")
    print("=" * 50)
    print("Dieses Script erstellt:")
    print("  • 1 BigQuery Dataset")
    print("  • 4 Tabellen")
    print("  • 8 Views (inkl. Werkstatt-Dashboard)")
    print("  • Optional: Beispieldaten")
    print()
    print("Voraussetzungen:")
    print("  • Google Cloud Project")
    print("  • Application Default Credentials oder Service Account Key")
    print("  • Korrekte .env Konfiguration")
    print()
    
    if input("Setup starten? (y/N): ").lower() != 'y':
        print("Setup abgebrochen.")
        return False
    
    success = setup_bigquery()
    
    if success:
        print("\n✅ Setup erfolgreich abgeschlossen!")
        return True
    else:
        print("\n❌ Setup fehlgeschlagen!")
        print("Prüfe die Fehlermeldungen oben.")
        return False


if __name__ == "__main__":
    # Environment laden
    load_dotenv()
    
    # Logging Level setzen (optional)
    import logging
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup ausführen
    sys.exit(0 if main() else 1)