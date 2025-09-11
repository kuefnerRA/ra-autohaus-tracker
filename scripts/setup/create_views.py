#!/usr/bin/env python3
"""Erstellt nur die Monitoring Views"""

import os
from dotenv import load_dotenv
from google.cloud import bigquery
from setup_bigquery import create_monitoring_views

load_dotenv()

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
dataset_id = f"{project_id}.{os.getenv('BIGQUERY_DATASET', 'autohaus')}"

client = bigquery.Client(project=project_id)
create_monitoring_views(client, dataset_id)
print("✅ Views erfolgreich erstellt/aktualisiert")