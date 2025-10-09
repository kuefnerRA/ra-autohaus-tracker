#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/thomas/dev/ra-autohaus-tracker')

from src.services.vin_decoder_service import VINDecoderService

print("\n🚗 VIN-DECODER TEST")
print("=" * 50)

test_cases = [
    ("WVWZZZ1JZ8W123456", "Volkswagen"),
    ("WAUZZZGE1NB038655", "Audi"),
    ("WBA12345678901234", "BMW"),
    ("WDD12345678901234", "Mercedes-Benz"),
    ("WP0ZZZ99ZTS392124", "Porsche"),
    ("TMBJJ7NE7L0123456", "Skoda"),
]

for fin, expected_marke in test_cases:
    result = VINDecoderService.decode_fin(fin)
    status = "✅" if result.get("marke") == expected_marke else "❌"
    print(f"{status} {fin} -> {result.get('marke', 'FEHLER')}")
    if result.get("baujahr"):
        print(f"    Baujahr: {result.get('baujahr')}")

print("\n✅ VIN-Decoder Test abgeschlossen")
