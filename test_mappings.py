#!/usr/bin/env python3
import sys
import os

# Füge src zum Python-Path hinzu
sys.path.insert(0, '/home/thomas/dev/ra-autohaus-tracker')

from src.core.mappings import CentralMappings

print("🔍 Teste Mappings...\n")

# Prozess-Mappings
print("Prozess-Mappings:")
test_cases = [
    ("gwa", "Aufbereitung"),
    ("garage", "Werkstatt"),
    ("(1) da fahrzeuganlage", "Einkauf"),
]

for input_val, expected in test_cases:
    result = CentralMappings.normalize_prozess_typ(input_val)
    status = "✅" if result == expected else "❌"
    print(f"  {status} '{input_val}' -> '{result}' (erwartet: '{expected}')")

# Status-Mappings
print("\nStatus-Mappings:")
status_cases = [
    ("fwd: gestartet", "WARTESCHLANGE"),
    ("in arbeit", "AKTIV"),
    ("fertig", "BEENDET"),
]

for input_val, expected in status_cases:
    result = CentralMappings.normalize_status(input_val)
    status = "✅" if result == expected else "❌"
    print(f"  {status} '{input_val}' -> '{result}' (erwartet: '{expected}')")

# Bearbeiter-Mappings
print("\nBearbeiter-Mappings:")
bearbeiter_cases = [
    ("Thomas K.", "Thomas Küfner"),
    ("Max R.", "Maximilian Reinhardt"),
]

for input_val, expected in bearbeiter_cases:
    result = CentralMappings.normalize_bearbeiter(input_val)
    status = "✅" if result == expected else "❌"
    print(f"  {status} '{input_val}' -> '{result}' (erwartet: '{expected}')")

print("\n✅ Alle Mappings-Tests abgeschlossen!")
