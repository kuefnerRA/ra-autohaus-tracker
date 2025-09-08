#!/bin/bash
# scripts/setup-dev.sh - Mit source aufrufen!

echo "════════════════════════════════════════════════════════════════"
echo "🚀 RA Autohaus Tracker - Development Environment Setup"
echo "════════════════════════════════════════════════════════════════"

# Ins Projektverzeichnis wechseln
cd ~/dev/ra-autohaus-tracker

# Virtual Environment aktivieren/erstellen
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
else
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing requirements..."
    pip install -r requirements.txt
fi

# Environment Variables setzen
export GOOGLE_CLOUD_PROJECT="ra-autohaus-tracker"
export BIGQUERY_DATASET="autohaus"
export SERVICE_ACCOUNT="ra-dev-local@ra-autohaus-tracker.iam.gserviceaccount.com"
unset GOOGLE_APPLICATION_CREDENTIALS

# Authentication prüfen/erneuern
echo "🔍 Checking authentication..."
if ! gcloud auth application-default print-access-token --impersonate-service-account=$SERVICE_ACCOUNT &>/dev/null; then
    echo "🔄 Setting up Service Account impersonation..."
    gcloud auth application-default login \
        --impersonate-service-account=$SERVICE_ACCOUNT \
        --project=$GOOGLE_CLOUD_PROJECT
fi

# BigQuery Test
echo "🔍 Testing BigQuery connection..."
python -c "
from google.cloud import bigquery
client = bigquery.Client(project='$GOOGLE_CLOUD_PROJECT')
datasets = list(client.list_datasets())
print('✅ BigQuery connected: ', [d.dataset_id for d in datasets])
"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Environment ready!"
echo "   Python: $(python --version)"
echo "   Venv: $VIRTUAL_ENV"
echo "   Project: $GOOGLE_CLOUD_PROJECT"
echo ""
echo "📝 Available commands:"
echo "   run-server    - Start API server (foreground)"
echo "   run-server-bg - Start API server (background)"
echo "   stop-server   - Stop background server"
echo "   test-api      - Test API endpoints"
echo "════════════════════════════════════════════════════════════════"