#!/usr/bin/env bash
set -euo pipefail

# Google Cloud Login ohne WSL-Interop
echo "🔐 Logging in to Google Cloud (no browser mode)..."
gcloud auth login --no-browser

# Projekt setzen
PROJECT_ID="ra-autohaus-tracker"
echo "📌 Setting default project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# Artifact Registry Docker Auth konfigurieren
REGION="europe-west3"
echo "🐳 Configuring Docker auth for Artifact Registry in region: $REGION"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" -q

echo "✅ Google Cloud login and setup complete."
