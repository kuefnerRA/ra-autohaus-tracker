#!/usr/bin/env python3
"""
Script zur Anreicherung von Fahrzeugen ohne Marke
"""

import asyncio
import os
import sys

# Pfad zum src-Verzeichnis hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.vin_decoder_service import VINDecoderService
from src.services.vehicle_service import VehicleService
from src.services.bigquery_service import BigQueryService
from src.core.dependencies import get_vehicle_service, get_bigquery_service

async def main():
    print("🚗 Starte Fahrzeug-Anreicherung...")
    
    # Services initialisieren
    vehicle_service = get_vehicle_service()
    
    # Batch-Anreicherung ausführen
    stats = await VINDecoderService.enrich_vehicle_batch(
        vehicle_service=vehicle_service,
        limit=50  # Erstmal nur 50 Fahrzeuge
    )
    
    print(f"\n📊 Ergebnis:")
    print(f"  - Verarbeitet: {stats.get('processed', 0)}")
    print(f"  - Angereichert: {stats.get('enriched', 0)}")
    print(f"  - Fehlgeschlagen: {stats.get('failed', 0)}")

if __name__ == "__main__":
    asyncio.run(main())