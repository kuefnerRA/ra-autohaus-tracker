#!/usr/bin/env python3
"""Test-Script für Fahrzeug-Update-Logik"""

import asyncio
import os
from dotenv import load_dotenv

# Mock-Modus aktivieren
os.environ['USE_MOCK_BIGQUERY'] = 'true'

from src.services.bigquery_service import BigQueryService
from src.services.vehicle_service import VehicleService
from src.services.email_service import EmailParser

async def test_update_logic():
    print("🧪 Teste Update-Logik im Mock-Modus\n")
    
    # Services initialisieren
    bigquery_service = BigQueryService()
    vehicle_service = VehicleService(bigquery_service)
    email_parser = EmailParser()
    
    # 1. Prüfe existierendes Mock-Fahrzeug
    print("1️⃣ Prüfe Mock-Fahrzeug WVWZZZ1JZ8W123456...")
    existing = await vehicle_service.get_vehicle_details("WVWZZZ1JZ8W123456")
    if existing:
        print(f"   ✅ Gefunden: {existing.marke} {existing.modell}")
        print(f"   📊 Aktuelle Daten:")
        print(f"      - Farbe: {existing.farbe}")
        print(f"      - KM: {existing.km_stand}")
        print(f"      - EK: {existing.ek_netto}")
    
    # 2. Simuliere Email-Parsing
    print("\n2️⃣ Parse Test-Email...")
    test_body = """
    FIN: WVWZZZ1JZ8W123456
    Marke: Volkswagen
    Modell: Golf GTI
    Farbe: Blau
    KM-Stand: 26.500
    EK netto: 19.500,00
    """
    
    fahrzeug_dict, _ = email_parser.parse_email_content("Test", test_body)
    if fahrzeug_dict:
        print(f"   ✅ Geparsed: {fahrzeug_dict['fin']}")
        print(f"   📝 Neue Daten:")
        print(f"      - Modell: {fahrzeug_dict.get('modell')}")
        print(f"      - Farbe: {fahrzeug_dict.get('farbe')}")
        print(f"      - KM: {fahrzeug_dict.get('km_stand')}")
    
    # 3. Update durchführen
    print("\n3️⃣ Führe Update durch...")
    update_data = {
        'modell': 'Golf GTI',  # Änderung
        'farbe': 'Blau',       # Änderung  
        'km_stand': 26500      # Änderung
    }
    
    update_result = await vehicle_service.update_vehicle(
        fin="WVWZZZ1JZ8W123456",
        update_data=update_data,
        create_update_process=True
    )
    
    print(f"   ✅ Update durchgeführt:")
    print(f"      - Änderungen gemacht: {update_result['changes_made']}")
    print(f"      - Geänderte Felder: {update_result['fields_updated']}")
    
    # 4. Change-Log anzeigen
    if update_result['change_log']:
        print("\n4️⃣ Change-Log:")
        for change in update_result['change_log']:
            print(f"   📝 {change['field']}:")
            print(f"      Alt: {change['old_value']}")
            print(f"      Neu: {change['new_value']}")
    
    # 5. Verifiziere Update
    print("\n5️⃣ Verifiziere Update...")
    updated = await vehicle_service.get_vehicle_details("WVWZZZ1JZ8W123456")
    if updated:
        print(f"   ✅ Neue Werte:")
        print(f"      - Modell: {updated.modell}")
        print(f"      - Farbe: {updated.farbe}")
        print(f"      - KM: {updated.km_stand}")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_update_logic())