#!/bin/bash
# scripts/deploy_cloud_run.sh - Deploy RA Autohaus Tracker to Google Cloud Run
set -e

PROJECT_ID="ra-autohaus-tracker"
SERVICE_NAME="ra-autohaus-tracker"
REGION="europe-west3"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Deploying RA Autohaus Tracker to Google Cloud Run"
echo "=================================================="
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "Image: $IMAGE_NAME"
echo ""

# 1. Projekt setzen
echo "📋 Setting up Google Cloud project..."
gcloud config set project $PROJECT_ID

# 2. APIs aktivieren
echo "🔧 Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    bigquery.googleapis.com

# 3. Dockerfile erstellen
echo "🐳 Creating Dockerfile..."
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Arbeitsverzeichnis setzen
WORKDIR /app

# System-Dependencies installieren
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
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

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# FastAPI starten
CMD exec uvicorn src.main:app --host 0.0.0.0 --port $PORT --workers 1
EOF

# 4. .dockerignore erstellen
echo "📁 Creating .dockerignore..."
cat > .dockerignore << 'EOF'
venv/
__pycache__/
*.pyc
.git/
.gitignore
README.md
.vscode/
tests/
docs/
*.log
.env
*.backup
node_modules/
.DS_Store
Thumbs.db
EOF

# 5. Cloud Build Config erstellen
echo "⚙️ Creating Cloud Build configuration..."
cat > cloudbuild.yaml << 'EOF'
steps:
  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ra-autohaus-tracker', '.']
    
  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ra-autohaus-tracker']
    
  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'ra-autohaus-tracker'
      - '--image=gcr.io/$PROJECT_ID/ra-autohaus-tracker'
      - '--region=europe-west3'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=1Gi'
      - '--cpu=1'
      - '--concurrency=100'
      - '--timeout=900'
      - '--set-env-vars=ENVIRONMENT=production,GCP_PROJECT_ID=$PROJECT_ID'

images:
  - 'gcr.io/$PROJECT_ID/ra-autohaus-tracker'

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'E2_HIGHCPU_8'
EOF

# 6. Container bauen und deployen
echo "🔨 Building and deploying container..."
gcloud builds submit --config cloudbuild.yaml .

# 7. Service-URL abrufen
echo "🌐 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo "✅ Deployment erfolgreich!"
echo "📡 Service URL: $SERVICE_URL"
echo "🔗 API Docs: $SERVICE_URL/docs"
echo "❤️ Health Check: $SERVICE_URL/health"
echo ""
echo "🔧 Webhook URLs für Flowers:"
echo "📧 E-Mail: $SERVICE_URL/webhooks/flowers/email"
echo "🔗 Direkt: $SERVICE_URL/webhooks/flowers/direct"
echo "⚡ Zapier: $SERVICE_URL/webhooks/zapier"
echo ""
echo "📊 Dashboard URLs:"
echo "📈 KPIs: $SERVICE_URL/dashboard/kpis"
echo "🚗 GWA Warteschlange: $SERVICE_URL/dashboard/gwa-warteschlange"
echo "📊 Warteschlangen Status: $SERVICE_URL/dashboard/warteschlangen-status"
echo ""
echo "🎯 Production-ready RA Autohaus Tracker ist live!"