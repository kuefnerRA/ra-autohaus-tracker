#!/bin/bash
# Setup-Script für Google Cloud Umgebung

set -e  # Exit bei Fehlern

PROJECT_ID="ra-autohaus-tracker"
REGION="europe-west3"
SERVICE_ACCOUNT="ra-dev-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🔧 Konfiguriere Google Cloud Projekt..."
gcloud config set project ${PROJECT_ID}
gcloud config set run/region ${REGION}

echo "✅ Projekt: $(gcloud config get-value project)"
echo "✅ Region: $(gcloud config get-value run/region)"
echo "✅ Service Account: ${SERVICE_ACCOUNT}"

# Prüfe ob Service Account existiert
if gcloud iam service-accounts describe ${SERVICE_ACCOUNT} >/dev/null 2>&1; then
    echo "✅ Service Account existiert"
else
    echo "❌ Service Account existiert nicht!"
    exit 1
fi
