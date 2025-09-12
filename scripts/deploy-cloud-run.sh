#!/bin/bash
# Cloud Run Deployment

set -e

PROJECT_ID="ra-autohaus-tracker"
REGION="europe-west1"
SERVICE_NAME="ra-autohaus-tracker"
SERVICE_ACCOUNT="ra-dev-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com"

# Lese letztes gebautes Image
if [ -f .last-build-image ]; then
    IMAGE=$(cat .last-build-image)
else
    echo "❌ Kein Image gefunden. Bitte erst build-and-push.sh ausführen!"
    exit 1
fi

echo "🚀 Deploye zu Cloud Run..."
echo "   Service: ${SERVICE_NAME}"
echo "   Image: ${IMAGE}"
echo "   Region: ${REGION}"

gcloud run deploy ${SERVICE_NAME} \
  --image=${IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --service-account=${SERVICE_ACCOUNT} \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=3 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300 \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},BIGQUERY_DATASET=autohaus,ENVIRONMENT=production" \
  --set-secrets="EMAIL_PASSWORD=email-password:latest" \
  --labels="app=autohaus-tracker,environment=production,version=${VERSION}"

# Service URL abrufen
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --format='value(status.url)')

echo "✅ Deployment erfolgreich!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo "📚 API Docs: ${SERVICE_URL}/docs"
