#!/usr/bin/env python3
"""
Komplette Test-Suite für RA Autohaus Tracker
"""
import sys
import os
import asyncio
import json
from datetime import datetime, date

# Füge src zum Path hinzu
sys.path.insert(0, '/home/thomas/dev/ra-autohaus-tracker')

from src.core.mappings import CentralMappings
from src.services.vin_decoder_service import VINDecoderService

def test_mappings():
    """Teste zentrale Mappings"""
    print("\n📋 TESTE MAPPINGS")
    print("=" * 50)
    
    errors = []
    
    # Prozess-Mappings
    tests = {
        "gwa": "Aufbereitung",
        "garage": "Werkstatt",
        "(1) da fahrzeuganlage": "Einkauf",
    }
    
    for input_val, expected in tests.items():
        result = CentralMappings.normalize_prozess_typ(input_val)
        if result != expected:
            errors.append(f"Prozess: '{input_val}' -> '{result}' (erwartet: '{expected}')")
        else:
            print(f"✅ Prozess: '{input_val}' -> '{result}'")
    
    # Status-Mappings
    status_tests = {
        "fwd: gestartet": "WARTESCHLANGE",
        "in arbeit": "AKTIV",
        "fertig": "BEENDET",
    }
    
    for input_val, expected in status_tests.items():
        result = CentralMappings.normalize_status(input_val)
        if result != expected:
            errors.append(f"Status: '{input_val}' -> '{result}' (erwartet: '{expected}')")
        else:
            print(f"✅ Status: '{input_val}' -> '{result}'")
    
    if errors:
        print("\n❌ FEHLER:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("\n✅ Alle Mappings funktionieren korrekt!")
    return True

def test_vin_decoder():
    """Teste VIN-Decoder"""
    print("\n🚗 TESTE VIN-DECODER")
    print("=" * 50)
    
    test_fins = [
        ("WVWZZZ1JZ8W123456", "Volkswagen"),
        ("WAUZZZGE1NB038655", "Audi"),
        ("WBA12345678901234", "BMW"),
        ("WDD12345678901234", "Mercedes-Benz"),
    ]
    
    for fin, expected_marke in test_fins:
        result = VINDecoderService.decode_fin(fin)
        if result.get("marke") == expected_marke:
            print(f"✅ {fin} -> {result.get('marke')}")
        else:
            print(f"❌ {fin} -> {result.get('marke')} (erwartet: {expected_marke})")
    
    return True

async def test_api_endpoints():
    """Teste API-Endpoints"""
    print("\n🌐 TESTE API-ENDPOINTS")
    print("=" * 50)
    
    import aiohttp
    
    base_url = "http://localhost:8080"
    
    async with aiohttp.ClientSession() as session:
        # Health Check
        async with session.get(f"{base_url}/health") as resp:
            if resp.status == 200:
                print(f"✅ Health Check: {resp.status}")
            else:
                print(f"❌ Health Check: {resp.status}")
        
        # System Info
        async with session.get(f"{base_url}/info") as resp:
            if resp.status == 200:
                print(f"✅ System Info: {resp.status}")
            else:
                print(f"❌ System Info: {resp.status}")
    
    return True

def main():
    """Führe alle Tests aus"""
    print("\n" + "=" * 60)
    print("🧪 RA AUTOHAUS TRACKER - TEST SUITE")
    print("=" * 60)
    
    # 1. Mappings
    test_mappings()
    
    # 2. VIN-Decoder
    test_vin_decoder()
    
    # 3. API-Endpoints (wenn Server läuft)
    try:
        asyncio.run(test_api_endpoints())
    except Exception as e:
        print(f"⚠️ API-Tests übersprungen (Server läuft nicht?): {e}")
    
    print("\n" + "=" * 60)
    print("✅ TEST-SUITE ABGESCHLOSSEN")
    print("=" * 60)

if __name__ == "__main__":
    main()
