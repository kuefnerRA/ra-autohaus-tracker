#!/bin/bash
# scripts/start-dev.sh

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════"
echo "🚀 RA Autohaus Tracker - Development Environment"
echo "════════════════════════════════════════════════════════════════"

# Konfiguration
SERVICE_ACCOUNT="ra-dev-local@ra-autohaus-tracker.iam.gserviceaccount.com"
PROJECT="ra-autohaus-tracker"
VENV_PATH="venv"  # Pfad zur virtuellen Umgebung

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Alte Server-Prozesse beenden
echo -e "${YELLOW}⏹  Stopping old processes...${NC}"
pkill -f "src.main" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true

# 2. Virtual Environment aktivieren oder erstellen
if [ -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}🐍 Activating virtual environment...${NC}"
    source $VENV_PATH/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}🐍 Creating virtual environment...${NC}"
    python3 -m venv $VENV_PATH
    source $VENV_PATH/bin/activate
    echo -e "${YELLOW}📦 Installing requirements...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Virtual environment created and activated${NC}"
fi

# Python Version anzeigen
PYTHON_VERSION=$(python --version)
echo -e "${GREEN}   Python: $PYTHON_VERSION${NC}"
echo -e "${GREEN}   Venv: $VIRTUAL_ENV${NC}"

# 3. Prüfe ob Impersonation noch aktiv ist
echo -e "${YELLOW}🔍 Checking authentication...${NC}"
if gcloud auth application-default print-access-token --impersonate-service-account=$SERVICE_ACCOUNT &>/dev/null; then
    echo -e "${GREEN}✅ Authentication valid${NC}"
else
    echo -e "${YELLOW}🔄 Setting up Service Account impersonation...${NC}"
    gcloud auth application-default login \
        --impersonate-service-account=$SERVICE_ACCOUNT \
        --project=$PROJECT
fi

# 4. Environment Variables setzen
export GOOGLE_CLOUD_PROJECT=$PROJECT
export BIGQUERY_DATASET="autohaus"
export GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=$SERVICE_ACCOUNT

# WICHTIG: GOOGLE_APPLICATION_CREDENTIALS darf NICHT gesetzt sein bei Impersonation!
unset GOOGLE_APPLICATION_CREDENTIALS

# 5. Dependencies prüfen (optional - nur wenn requirements.txt geändert)
if [ requirements.txt -nt $VENV_PATH/.last_install ]; then
    echo -e "${YELLOW}📦 Updating dependencies...${NC}"
    pip install -r requirements.txt
    touch $VENV_PATH/.last_install
fi

# 6. Verbindung testen
echo -e "${YELLOW}🔍 Testing BigQuery connection...${NC}"
python -c "
import sys
from google.cloud import bigquery
try:
    client = bigquery.Client(project='$PROJECT')
    datasets = list(client.list_datasets())
    print('✅ BigQuery connected successfully')
    print(f'   Project: $PROJECT')
    print(f'   Datasets: {[d.dataset_id for d in datasets]}')
    print(f'   Using SA: $SERVICE_ACCOUNT (via impersonation)')
except Exception as e:
    print(f'❌ Connection failed: {e}')
    sys.exit(1)
" || {
    echo -e "${RED}❌ BigQuery connection failed. Running re-authentication...${NC}"
    gcloud auth application-default login \
        --impersonate-service-account=$SERVICE_ACCOUNT \
        --project=$PROJECT
    
    # Nochmal testen nach Re-Auth
    python -c "
from google.cloud import bigquery
client = bigquery.Client(project='$PROJECT')
print('✅ BigQuery reconnected successfully')
    "
}

# 7. Quick API Test (optional)
echo -e "${YELLOW}🔍 Running quick API test...${NC}"
python -c "
try:
    from src.main import app
    from src.services.bigquery_service import BigQueryService
    print('✅ API modules loaded successfully')
except Exception as e:
    print(f'⚠️  Warning: {e}')
" || true

# 8. Server starten
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎯 Starting API server on http://localhost:8080${NC}"
echo -e "${GREEN}   Using Service Account: $SERVICE_ACCOUNT${NC}"
echo -e "${GREEN}   Project: $PROJECT${NC}"
echo -e "${GREEN}   Virtual Env: $VIRTUAL_ENV${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}📝 Quick Test Commands:${NC}"
echo "   curl http://localhost:8080/health"
echo "   curl http://localhost:8080/api/v1/fahrzeuge/"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Server mit Reload für Entwicklung starten
python -m src.main