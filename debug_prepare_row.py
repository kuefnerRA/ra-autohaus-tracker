import sys
sys.path.insert(0, '/home/thomas/dev/ra-autohaus-tracker')

from src.services.bigquery_service import BigQueryService

# Test-Daten mit individueller Deadline
test_data = {
    'prozess_id': 'TEST_123',
    'fin': 'TEST',
    'prozess_typ': 'Werkstatt',
    'status': 'WARTESCHLANGE',
    'individuelle_deadline': '2025-10-09T18:00:00',
    'individuelle_deadline_gesetzt': True,
    'sla_deadline_datum': '2025-10-09'
}

service = BigQueryService()
prepared = service._prepare_prozess_row(test_data)

print("\n🔍 PREPARED ROW für BigQuery:")
print("=" * 50)
for key, value in prepared.items():
    if 'deadline' in key or 'sla' in key:
        print(f"  {key}: {value}")
print("=" * 50)
print(f"\n❓ Hat individuelle_deadline: {'individuelle_deadline' in prepared}")
print(f"❓ Wert: {prepared.get('individuelle_deadline')}")
