#!/bin/bash
set -e

PROJECT_ID="ra-autohaus-tracker"
SA_NAME="ra-autohaus-tracker-sa"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

echo "🔐 Service Account für RA Autohaus Tracker erstellen"

# 1. Service Account erstellen
gcloud iam service-accounts create $SA_NAME \
    --display-name="RA Autohaus Tracker Service Account" \
    --description="Service Account für BigQuery und Cloud Run"

# 2. BigQuery-Berechtigungen setzen
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/bigquery.jobUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/bigquery.user"

# 3. Cloud Run Service mit neuem Service Account aktualisieren
echo "🚀 Cloud Run Service mit Service Account aktualisieren..."
gcloud run services update ra-autohaus-tracker \
    --service-account=$SA_EMAIL \
    --region=europe-west3

echo "✅ Service Account konfiguriert: $SA_EMAIL"
echo "🎯 Cloud Run verwendet jetzt dedizierten Service Account"
