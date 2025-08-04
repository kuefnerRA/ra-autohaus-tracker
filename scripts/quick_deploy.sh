#!/bin/bash
set -e

echo "⚡ Quick Deploy zu Test-Umgebung"

# Virtual Environment aktivieren
source venv/bin/activate

# Code-Qualität prüfen
echo "1. Code-Qualität prüfen..."
flake8 src --count --exit-zero
black --check src || (echo "Formatiere Code..." && black src)

# Docker Build
echo "2. Docker Image bauen..."
bash scripts/docker_build.sh test

# Google Cloud authentifizieren
echo "3. Google Cloud Setup..."
gcloud config set project ra-autohaus-tracker
gcloud auth configure-docker

# Deploy
echo "4. Deploy zu Cloud Run..."
docker push gcr.io/ra-autohaus-tracker/ra-autohaus-tracker:test

gcloud run deploy ra-autohaus-tracker-test \
    --image gcr.io/ra-autohaus-tracker/ra-autohaus-tracker:test \
    --platform managed \
    --region europe-west3 \
    --allow-unauthenticated \
    --set-env-vars "ENVIRONMENT=test" \
    --memory 1Gi \
    --cpu 1

# URL abrufen
URL=$(gcloud run services describe ra-autohaus-tracker-test --region=europe-west3 --format="value(status.url)")
echo "✅ Deployment abgeschlossen!"
echo "🌐 URL: $URL"
echo "🔍 Health Check: $URL/health"