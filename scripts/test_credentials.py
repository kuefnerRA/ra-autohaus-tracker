# test_credentials.py
#!/usr/bin/env python3
import os
import json
from pathlib import Path
from google.auth import default
from google.cloud import bigquery

print("=" * 60)
print("CREDENTIALS CHECK")
print("=" * 60)

# Environment Variables
print("\n📁 Environment Variables:")
print(f"  GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '❌ NOT SET')}")
print(f"  GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT', '❌ NOT SET')}")
print(f"  GCP_PROJECT: {os.environ.get('GCP_PROJECT', '❌ NOT SET')}")

# ADC File Check
adc_paths = [
    Path.home() / ".config/gcloud/application_default_credentials.json",
    Path("/home/thomas/.config/gcloud/application_default_credentials.json"),
]

print("\n📄 ADC Files:")
for path in adc_paths:
    if path.exists():
        print(f"  ✅ {path} (exists)")
        with open(path) as f:
            data = json.load(f)
            print(f"     Type: {data.get('type', 'unknown')}")
            print(f"     Client ID: {data.get('client_id', 'N/A')[:30]}...")
    else:
        print(f"  ❌ {path} (not found)")

# Google Auth Default
print("\n🔐 Google Auth Default:")
try:
    credentials, project = default()
    print(f"  ✅ Project: {project}")
    print(f"  ✅ Credentials Type: {type(credentials).__name__}")
    
    if hasattr(credentials, 'service_account_email'):
        print(f"  ✅ Service Account: {credentials.service_account_email}")
    
    # Test BigQuery
    print("\n🗄️ BigQuery Test:")
    client = bigquery.Client(project=project, credentials=credentials)
    
    # List datasets
    datasets = list(client.list_datasets())
    print(f"  ✅ Datasets found: {[d.dataset_id for d in datasets]}")
    
    # Test query
    query = "SELECT CURRENT_TIMESTAMP() as now"
    result = list(client.query(query))
    print(f"  ✅ Query successful: {result[0]['now']}")
    
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 60)