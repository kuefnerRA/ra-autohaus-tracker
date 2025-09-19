#!/usr/bin/env python3
"""
Erstellt nur die Views (ohne Tabellen)
RA Autohaus Tracker - Reinhardt Automobile GmbH

Nutzt die View-Definitionen aus bigquery_views.py
"""

import os
import sys
from dotenv import load_dotenv
from google.cloud import bigquery

# Import der View-Definitionen
from bigquery_views import create_all_views

def main():
    """Hauptfunktion zum Erstellen der Views."""
    
    print("📊 Create Views für RA Autohaus Tracker")
    print("=" * 50)
    
    # Environment laden
    load_dotenv()
    
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    dataset_name = os.getenv('BIGQUERY_DATASET', 'autohaus')
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT nicht gesetzt!")
        print("   Setze in .env: GOOGLE_CLOUD_PROJECT=deine-projekt-id")
        return False
    
    dataset_id = f"{project_id}.{dataset_name}"
    
    print(f"✅ Projekt: {project_id}")
    print(f"✅ Dataset: {dataset_name}")
    
    try:
        # BigQuery Client initialisieren
        print("\n🔗 Verbinde zu BigQuery...")
        client = bigquery.Client(project=project_id)
        print("✅ BigQuery Client initialisiert")
        
        # Alle Views erstellen
        create_all_views(client, dataset_id)
        
        print("\n🎉 Views erfolgreich erstellt/aktualisiert!")
        print("\nDu kannst die Views jetzt in:")
        print("  • BigQuery Console überprüfen")
        print("  • Looker Studio als Datenquelle verwenden")
        print("  • SQL-Abfragen nutzen")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Views-Setup für RA Autohaus Tracker")
    print("Dieses Skript erstellt/aktualisiert NUR die Views.")
    print("Voraussetzung: Tabellen müssen bereits existieren!")
    print()
    
    if input("Views erstellen/aktualisieren? (y/N): ").lower() != 'y':
        print("Abgebrochen.")
        sys.exit(0)
    
    success = main()
    
    if success:
        print("\n✅ Erfolgreich abgeschlossen!")
    else:
        print("\n❌ Setup fehlgeschlagen!")
        print("Prüfe die Fehlermeldungen oben.")
        sys.exit(1)