#!/bin/bash
# Cloud Run Deployment

set -e

PROJECT_ID="ra-autohaus-tracker"
REGION="europe-west3"
SERVICE_NAME="ra-autohaus-tracker"
SERVICE_ACCOUNT="ra-dev-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com"

# Lese letztes gebautes Image
if [ -f .last-build-image ]; then
    IMAGE=$(head -n 1 .last-build-image)
    echo "📦 Verwende Image: ${IMAGE}"
else
    echo "❌ Kein Image gefunden. Bitte erst build-and-push.sh ausführen!"
    exit 1
fi

echo "🚀 Deploye zu Cloud Run..."
echo "   Service: ${SERVICE_NAME}"
echo "   Region: ${REGION}"
echo "   Service Account: ${SERVICE_ACCOUNT}"

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
  --set-secrets="EMAIL_ADDRESS=email-address:latest,EMAIL_PASSWORD=email-password:latest,IMAP_SERVER=imap-server:latest" \
  --labels="app=autohaus-tracker,environment=production"

# Service URL abrufen
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --format='value(status.url)')

echo ""
echo "✅ Deployment erfolgreich!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo "📚 API Docs: ${SERVICE_URL}/docs"
echo "🔗 Zapier Endpoint: ${SERVICE_URL}/api/integration/zapier"
