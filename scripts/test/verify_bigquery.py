#!/usr/bin/env python3
"""
BigQuery Daten-Verifikation für RA Autohaus Tracker
Prüft ob Fahrzeuge und Prozesse korrekt gespeichert wurden
"""

import os
from datetime import datetime, timedelta
from google.cloud import bigquery
from tabulate import tabulate
import sys

# Farben für Terminal-Output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_section(title):
    """Formatierte Sektion ausgeben"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def check_bigquery_connection():
    """BigQuery Verbindung testen"""
    try:
        client = bigquery.Client(project="ra-autohaus-tracker")
        datasets = list(client.list_datasets())
        print(f"{GREEN}✓ BigQuery Verbindung erfolgreich{RESET}")
        print(f"  Gefundene Datasets: {[d.dataset_id for d in datasets]}")
        return client
    except Exception as e:
        print(f"{RED}✗ BigQuery Verbindung fehlgeschlagen: {e}{RESET}")
        sys.exit(1)

def verify_fahrzeuge_stamm(client):
    """Fahrzeuge Stammdaten prüfen"""
    print_section("FAHRZEUGE STAMMDATEN")
    
    query = """
    SELECT 
        fin,
        marke,
        modell,
        km_stand,
        ek_netto,
        datenquelle_fahrzeug,
        DATE(created_at) as erstellt_am,
        TIME(created_at) as erstellt_um
    FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
    WHERE DATE(created_at) = CURRENT_DATE()
    ORDER BY created_at DESC
    LIMIT 10
    """
    
    try:
        results = client.query(query).to_dataframe()
        
        if len(results) > 0:
            print(f"{GREEN}✓ {len(results)} Fahrzeuge heute erstellt{RESET}\n")
            
            # Tabelle ausgeben
            print(tabulate(results, headers='keys', tablefmt='grid', showindex=False))
            
            # Statistiken
            print(f"\n📊 Statistiken:")
            print(f"  • Durchschnittlicher EK: €{results['ek_netto'].mean():,.2f}")
            print(f"  • Durchschnittlicher KM-Stand: {results['km_stand'].mean():,.0f} km")
            print(f"  • Marken: {', '.join(results['marke'].unique())}")
            print(f"  • Datenquellen: {', '.join(results['datenquelle_fahrzeug'].dropna().unique())}")
            
            return len(results)
        else:
            print(f"{YELLOW}⚠ Keine Fahrzeuge heute erstellt{RESET}")
            return 0
            
    except Exception as e:
        print(f"{RED}✗ Fehler beim Abrufen der Fahrzeuge: {e}{RESET}")
        return 0

def verify_fahrzeug_prozesse(client):
    """Fahrzeug Prozesse prüfen"""
    print_section("FAHRZEUG PROZESSE")
    
    query = """
    SELECT 
        fp.fin,
        fp.prozess_typ,
        fp.status,
        fp.bearbeiter,
        fp.prioritaet,
        fp.sla_deadline_datum,
        fp.tage_bis_sla_deadline,
        fp.datenquelle,
        DATE(fp.created_at) as erstellt_am,
        fs.marke,
        fs.modell
    FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` fp
    LEFT JOIN `ra-autohaus-tracker.autohaus.fahrzeuge_stamm` fs 
        ON fp.fin = fs.fin
    WHERE DATE(fp.created_at) = CURRENT_DATE()
    ORDER BY fp.created_at DESC
    LIMIT 10
    """
    
    try:
        results = client.query(query).to_dataframe()
        
        if len(results) > 0:
            print(f"{GREEN}✓ {len(results)} Prozesse heute erstellt{RESET}\n")
            
            # Tabelle ausgeben
            display_cols = ['fin', 'marke', 'modell', 'prozess_typ', 'status', 'bearbeiter', 'tage_bis_sla_deadline']
            print(tabulate(results[display_cols], headers='keys', tablefmt='grid', showindex=False))
            
            # SLA-Status analysieren
            print(f"\n⏰ SLA-Status:")
            critical = results[results['tage_bis_sla_deadline'] <= 1]
            overdue = results[results['tage_bis_sla_deadline'] < 0]
            
            if len(overdue) > 0:
                print(f"  {RED}• {len(overdue)} überfällige Prozesse!{RESET}")
            if len(critical) > 0:
                print(f"  {YELLOW}• {len(critical)} kritische Prozesse (≤1 Tag){RESET}")
            
            # Prozesstyp-Verteilung
            print(f"\n📈 Prozesstyp-Verteilung:")
            for ptype, count in results['prozess_typ'].value_counts().items():
                print(f"  • {ptype}: {count}")
            
            # Bearbeiter-Verteilung
            print(f"\n👥 Bearbeiter-Verteilung:")
            for bearbeiter, count in results['bearbeiter'].dropna().value_counts().items():
                print(f"  • {bearbeiter}: {count} Prozesse")
                
            return len(results)
        else:
            print(f"{YELLOW}⚠ Keine Prozesse heute erstellt{RESET}")
            return 0
            
    except Exception as e:
        print(f"{RED}✗ Fehler beim Abrufen der Prozesse: {e}{RESET}")
        return 0

def verify_data_consistency(client):
    """Datenkonsistenz prüfen"""
    print_section("DATENKONSISTENZ-PRÜFUNG")
    
    # Prüfe Fahrzeuge ohne Prozesse
    query_orphans = """
    SELECT COUNT(*) as anzahl
    FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm` fs
    WHERE NOT EXISTS (
        SELECT 1 
        FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` fp
        WHERE fp.fin = fs.fin
    )
    AND DATE(fs.created_at) = CURRENT_DATE()
    """
    
    # Prüfe doppelte FINs
    query_duplicates = """
    SELECT fin, COUNT(*) as anzahl
    FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
    GROUP BY fin
    HAVING COUNT(*) > 1
    """
    
    try:
        orphans = client.query(query_orphans).to_dataframe()
        duplicates = client.query(query_duplicates).to_dataframe()
        
        print("🔍 Konsistenz-Checks:")
        
        # Fahrzeuge ohne Prozesse
        orphan_count = orphans['anzahl'].iloc[0] if len(orphans) > 0 else 0
        if orphan_count > 0:
            print(f"  {YELLOW}• {orphan_count} Fahrzeuge ohne Prozesse (heute){RESET}")
        else:
            print(f"  {GREEN}• Alle Fahrzeuge haben Prozesse{RESET}")
        
        # Doppelte FINs
        if len(duplicates) > 0:
            print(f"  {RED}• {len(duplicates)} doppelte FINs gefunden!{RESET}")
            for _, row in duplicates.iterrows():
                print(f"    - {row['fin']}: {row['anzahl']}x")
        else:
            print(f"  {GREEN}• Keine doppelten FINs{RESET}")
            
    except Exception as e:
        print(f"{RED}✗ Fehler bei Konsistenzprüfung: {e}{RESET}")

def check_integration_sources(client):
    """Integration-Quellen prüfen"""
    print_section("INTEGRATION-QUELLEN")
    
    query = """
    SELECT 
        datenquelle,
        COUNT(*) as anzahl
    FROM (
        SELECT datenquelle_fahrzeug as datenquelle
        FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
        WHERE DATE(created_at) = CURRENT_DATE()
        
        UNION ALL
        
        SELECT datenquelle
        FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
        WHERE DATE(created_at) = CURRENT_DATE()
    )
    WHERE datenquelle IS NOT NULL
    GROUP BY datenquelle
    ORDER BY anzahl DESC
    """
    
    try:
        results = client.query(query).to_dataframe()
        
        if len(results) > 0:
            print("📡 Datenquellen heute:")
            for _, row in results.iterrows():
                source = row['datenquelle']
                count = row['anzahl']
                icon = "🔌" if source == "api" else "⚡" if source == "zapier" else "📧" if source == "email" else "🌸" if source == "flowers" else "❓"
                print(f"  {icon} {source}: {count} Einträge")
        else:
            print(f"{YELLOW}Keine Datenquellen-Informationen gefunden{RESET}")
            
    except Exception as e:
        print(f"{RED}✗ Fehler beim Prüfen der Datenquellen: {e}{RESET}")

def main():
    """Hauptfunktion"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}RA AUTOHAUS TRACKER - BIGQUERY VERIFIKATION{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Zeitstempel: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # BigQuery verbinden
    client = check_bigquery_connection()
    
    # Tests durchführen
    fahrzeuge_count = verify_fahrzeuge_stamm(client)
    prozesse_count = verify_fahrzeug_prozesse(client)
    verify_data_consistency(client)
    check_integration_sources(client)
    
    # Zusammenfassung
    print_section("ZUSAMMENFASSUNG")
    
    if fahrzeuge_count > 0 or prozesse_count > 0:
        print(f"{GREEN}✓ BigQuery-Integration funktioniert!{RESET}")
        print(f"\n📊 Heute erstellt:")
        print(f"  • {fahrzeuge_count} Fahrzeuge")
        print(f"  • {prozesse_count} Prozesse")
        
        print(f"\n💡 Nächste Schritte:")
        print(f"  1. Weitere Integrationstests durchführen")
        print(f"  2. Dashboard-KPIs überprüfen")
        print(f"  3. SLA-Monitoring testen")
    else:
        print(f"{YELLOW}⚠ Keine Testdaten gefunden{RESET}")
        print(f"\nFühre zuerst die Test-Suite aus:")
        print(f"  bash scripts/test_bigquery_integration.sh")
    
    print(f"\n🔍 BigQuery Console:")
    print(f"  https://console.cloud.google.com/bigquery?project=ra-autohaus-tracker")

if __name__ == "__main__":
    main()