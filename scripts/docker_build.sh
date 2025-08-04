#!/bin/bash
set -e

PROJECT_ID="ra-autohaus-tracker"
SERVICE_NAME="ra-autohaus-tracker"
TAG=${1:-"latest"}

echo "🐳 Docker Build für RA Autohaus Tracker"
echo "Project: $PROJECT_ID"
echo "Tag: $TAG"

# Docker Image bauen
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:$TAG .

echo "✅ Docker Image gebaut: gcr.io/$PROJECT_ID/$SERVICE_NAME:$TAG"
echo "📝 Nächste Schritte:"
echo "1. Lokal testen: docker run -p 8080:8080 gcr.io/$PROJECT_ID/$SERVICE_NAME:$TAG"
echo "2. Zu GCR pushen: docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$TAG"
