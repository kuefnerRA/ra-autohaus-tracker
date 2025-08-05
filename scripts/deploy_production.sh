#!/bin/bash
# scripts/deploy_local_docker.sh - Deploy mit lokalem Docker Build (umgeht Cloud Build Probleme)
set -e

PROJECT_ID="ra-autohaus-tracker"
SERVICE_NAME="ra-autohaus-tracker"
REGION="europe-west3"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
IMAGE_TAG="latest"
FULL_IMAGE="$IMAGE_NAME:$IMAGE_TAG"

echo "🚀 RA Autohaus Tracker - Lokaler Docker Deploy"
echo "=============================================="
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "Image: $FULL_IMAGE"
echo ""

# 1. Projekt setzen
echo "📋 Setting up Google Cloud project..."
gcloud config set project $PROJECT_ID

# 2. APIs aktivieren (falls noch nicht)
echo "🔧 Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    bigquery.googleapis.com

# 3. Docker für GCR konfigurieren
echo "🐳 Configuring Docker for Google Container Registry..."
gcloud auth configure-docker gcr.io --quiet

# 4. Dockerfile erstellen (falls nicht vorhanden)
if [ ! -f "Dockerfile" ]; then
    echo "📄 Creating Dockerfile..."
    cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Arbeitsverzeichnis setzen
WORKDIR /app

# System-Dependencies installieren
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY src/ ./src/
COPY . .

# Port für Cloud Run
ENV PORT=8080
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production
ENV GCP_PROJECT_ID=ra-autohaus-tracker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# User für Sicherheit
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# FastAPI starten
CMD exec uvicorn src.main:app --host 0.0.0.0 --port $PORT --workers 1
EOF
fi

# 5. .dockerignore erstellen (falls nicht vorhanden)
if [ ! -f ".dockerignore" ]; then
    echo "📁 Creating .dockerignore..."
    cat > .dockerignore << 'EOF'
# Development
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
.tox/
.coverage
.cache
*.log

# Git
.git/
.gitignore

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Documentation
docs/
README.md
*.md

# Testing
tests/
.pytest_cache/

# Backup files
*.backup
*.old

# Temporary files
tmp/
temp/

# Environment files
.env
*.env

# Build artifacts
build/
dist/
*.egg-info/
EOF
fi

# 6. Docker Image lokal bauen
echo "🔨 Building Docker image locally..."
docker buildx create --use --name mybuilder 2>/dev/null || true
docker buildx build -t $FULL_IMAGE . --platform linux/amd64 --load

# 7. Image zu Google Container Registry pushen
echo "📤 Pushing image to Google Container Registry..."
docker push $FULL_IMAGE

# 8. Cloud Run Service deployen
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $FULL_IMAGE \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --concurrency 100 \
    --timeout 900 \
    --max-instances 10 \
    --set-env-vars ENVIRONMENT=production,GCP_PROJECT_ID=$PROJECT_ID \
    --port 8080

# 9. Service-URL abrufen
echo "🌐 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

# 10. Deployment-Ergebnis anzeigen
echo ""
echo "🎉 =============================================="
echo "✅ Deployment erfolgreich abgeschlossen!"
echo "🎉 =============================================="
echo ""
echo "📡 Service URL: $SERVICE_URL"
echo "🔗 API Docs: $SERVICE_URL/docs"
echo "❤️ Health Check: $SERVICE_URL/health"
echo ""
echo "🔧 Webhook URLs für Flowers Integration:"
echo "📧 E-Mail Webhook: $SERVICE_URL/webhooks/flowers/email"
echo "🔗 Direct Webhook: $SERVICE_URL/webhooks/flowers/direct"
echo "⚡ Zapier Webhook: $SERVICE_URL/webhooks/zapier"
echo ""
echo "📊 Dashboard URLs:"
echo "📈 KPIs: $SERVICE_URL/dashboard/kpis"
echo "🚗 GWA Warteschlange: $SERVICE_URL/dashboard/gwa-warteschlange"
echo "📊 Warteschlangen Status: $SERVICE_URL/dashboard/warteschlangen-status"
echo "🔍 Debug Warteschlange: $SERVICE_URL/debug/warteschlange-data"
echo ""
echo "🧪 Test Commands:"
echo "curl $SERVICE_URL/health"
echo "curl $SERVICE_URL/dashboard/kpis"
echo ""
echo "🎯 RA Autohaus Tracker ist jetzt produktiv verfügbar!"
echo "📝 Notieren Sie sich die Service URL für die Flowers-Integration."

# 11. Schnelltest durchführen
echo ""
echo "🧪 Performing quick health check..."
if curl -s --fail "$SERVICE_URL/health" > /dev/null; then
    echo "✅ Health check successful - Service is running!"
else
    echo "⚠️ Health check failed - Please check the logs:"
    echo "gcloud logs read --service=$SERVICE_NAME --region=$REGION"
fi

echo ""
echo "🎉 Deployment completed successfully!"