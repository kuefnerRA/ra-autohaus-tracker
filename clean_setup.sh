#!/bin/bash
# clean_setup.sh - Sauberes Setup für RA Autohaus Tracker

set -e

echo "🧹 RA Autohaus Tracker - Sauberes Repository Setup"
echo "Aktuelles Verzeichnis: $(pwd)"

# 1. Google Cloud SDK verschieben (falls gewünscht)
if [ -d "google-cloud-sdk" ]; then
    echo "📦 Google Cloud SDK gefunden - verschiebe nach ~/google-cloud-sdk"
    mv google-cloud-sdk ~/google-cloud-sdk-backup
    echo "✅ Google Cloud SDK nach ~/google-cloud-sdk-backup verschoben"
fi

# 2. Git Repository initialisieren
echo "📋 Git Repository initialisieren..."
git init
git branch -M main

# 3. Remote Repository verbinden
echo "🔗 Remote Repository verbinden..."
git remote add origin https://github.com/kuefnerRA/ra-autohaus-tracker.git

# 4. GitHub Repository Status prüfen
echo "🔍 GitHub Repository Status prüfen..."
git ls-remote origin &>/dev/null && echo "✅ GitHub Repository erreichbar" || echo "⚠️  GitHub Repository nicht erreichbar - aber das ist OK"

# 5. Komplette Verzeichnisstruktur erstellen
echo "📁 Verzeichnisstruktur erstellen..."
mkdir -p .github/workflows
mkdir -p src/{models,handlers,services,utils}
mkdir -p tests
mkdir -p scripts
mkdir -p config
mkdir -p docs

# 6. .gitignore erstellen
echo "🚫 .gitignore erstellen..."
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/

# Environment Variables
.env
*.env
config/local.env

# Google Cloud
key.json
service-account-key.json
*-key.json
google-cloud-sdk/

# IDE
.vscode/settings.json
.idea/

# Logs
*.log
logs/

# Testing
.coverage
.pytest_cache/
htmlcov/

# OS
.DS_Store
Thumbs.db

# Project specific
tmp/
data/
*.backup
EOF

# 7. README.md erstellen
echo "📖 README.md erstellen..."
cat > README.md << 'EOF'
# RA Autohaus Tracker

Multi-Source Fahrzeugprozess-Tracking-System für Reinhardt Automobile.

## Überblick

Dieses System ermöglicht die zentrale Verfolgung aller Fahrzeugprozesse von der Anlieferung bis zur Auslieferung. Es integriert Daten aus verschiedenen Quellen (Flowers Software, Audaris, AutoCRM) und bietet Echzeit-Dashboards für optimale Prozesssteuerung.

## Features

- 🚗 **Fahrzeug-Stammdatenmanagement** - Zentrale Verwaltung aller Fahrzeugdaten
- 📊 **Prozess-Tracking** - Transport, Aufbereitung, Werkstatt, Foto, Vertrieb
- 📧 **Multi-Source Integration** - E-Mail, Webhooks, Zapier-Integration
- ⏱️ **SLA-Monitoring** - Automatische Überwachung und Alerts
- 📈 **Live-Dashboards** - Warteschlangen, KPIs, Bearbeiter-Performance
- ☁️ **Cloud-Native** - Skalierbare Google Cloud Architektur

## Technologie-Stack

- **Backend**: Python FastAPI
- **Datenbank**: Google BigQuery
- **Hosting**: Google Cloud Run
- **Dashboards**: Looker Studio
- **CI/CD**: GitHub Actions
- **Monitoring**: Google Cloud Logging

## Architektur

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flowers SW    │    │    Audaris      │    │   AutoCRM       │
│                 │    │                 │    │                 │
│ • E-Mail        │    │ • API           │    │ • CRM Prozesse  │
│ • Webhooks      │    │ • Fahrzeugdaten │    │ • Vertrieb      │
│ • Zapier        │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴───────────┐
                    │   Cloud Run API         │
                    │                         │
                    │ • Multi-Source Handler  │
                    │ • Process Management    │
                    │ • SLA Monitoring        │
                    │ • Dashboard APIs        │
                    └─────────────┬───────────┘
                                  │
                    ┌─────────────┴───────────┐
                    │   BigQuery              │
                    │                         │
                    │ • Fahrzeug-Stammdaten  │
                    │ • Prozess-Transaktionen │
                    │ • SLA-Views             │
                    │ • Performance-Metriken  │
                    └─────────────┬───────────┘
                                  │
                    ┌─────────────┴───────────┐
                    │   Looker Studio         │
                    │                         │
                    │ • Executive Dashboard   │
                    │ • Warteschlangen        │
                    │ • Bearbeiter-KPIs       │
                    │ • SLA-Alerts            │
                    └─────────────────────────┘
```

## Entwicklung

### Voraussetzungen
- Python 3.11+
- Google Cloud CLI
- Docker (optional)
- Git

### Lokales Setup
```bash
# Repository klonen
git clone https://github.com/kuefnerRA/ra-autohaus-tracker.git
cd ra-autohaus-tracker

# Entwicklungsumgebung einrichten
./scripts/setup_local.sh

# Virtual Environment aktivieren
source venv/bin/activate

# Development Server starten
./scripts/start_dev.sh
```

### API Dokumentation
- **Lokale Entwicklung**: http://localhost:8080/docs
- **Test-Umgebung**: TBD
- **Produktion**: TBD

### Wichtige Endpunkte
- `GET /health` - System Health Check
- `POST /fahrzeuge` - Fahrzeug anlegen
- `POST /prozesse/start` - Prozess starten
- `GET /dashboard/warteschlangen` - Aktuelle Warteschlangen
- `GET /dashboard/sla-alerts` - SLA-Verletzungen

## Deployment

### Test-Umgebung
```bash
./scripts/deploy_test.sh
```

### Produktion (nur für autorisierte Personen)
```bash
./scripts/deploy_prod.sh
```

## Konfiguration

### Environment Variables
- `ENVIRONMENT` - Umgebung (development/test/prod)
- `GCP_PROJECT_ID` - Google Cloud Projekt ID
- `BIGQUERY_DATASET` - BigQuery Dataset Name

### SLA-Zeiten
- **Transport**: 7 Tage
- **Aufbereitung**: 2 Tage
- **Werkstatt**: 10 Tage
- **Foto**: 3 Tage

## Support

Bei Fragen oder Problemen wenden Sie sich an:
- **Thomas Küfner** - thomas.kuefner@reinhardt-automobile.de
- **GitHub Issues**: https://github.com/kuefnerRA/ra-autohaus-tracker/issues

## Lizenz

Proprietär - Reinhardt Automobile GmbH
EOF

# 8. Requirements.txt erstellen
echo "📦 Requirements.txt erstellen..."
cat > requirements.txt << 'EOF'
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Google Cloud
google-cloud-bigquery==3.13.0
google-cloud-run==0.10.3
google-cloud-logging==3.8.0
google-cloud-secret-manager==2.17.0

# Data & Validation
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
python-email-validator==2.1.0

# HTTP & Requests
requests==2.31.0
httpx==0.25.2

# Date & Time
python-dateutil==2.8.2

# Production Server
gunicorn==21.2.0

# Development & Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
flake8==6.1.0
isort==5.12.0
pre-commit==3.6.0

# Utilities
python-dotenv==1.0.0
structlog==23.2.0
EOF

# 9. Python Package Struktur erstellen
echo "🐍 Python Package Struktur erstellen..."

# src/__init__.py
touch src/__init__.py

# src/models/__init__.py und basis models
cat > src/models/__init__.py << 'EOF'
"""Data models for the RA Autohaus Tracker."""

from .vehicle_process import VehicleProcess, ProcessStatus, ProcessType

__all__ = ["VehicleProcess", "ProcessStatus", "ProcessType"]
EOF

# src/handlers/__init__.py
cat > src/handlers/__init__.py << 'EOF'
"""Request handlers for different data sources."""
EOF

# src/services/__init__.py
cat > src/services/__init__.py << 'EOF'
"""Business logic and external service integrations."""
EOF

# src/utils/__init__.py
cat > src/utils/__init__.py << 'EOF'
"""Utility functions and helpers."""
EOF

# tests/__init__.py
cat > tests/__init__.py << 'EOF'
"""Test suite for RA Autohaus Tracker."""
EOF

# 10. Konfigurationsdateien erstellen
echo "⚙️  Konfigurationsdateien erstellen..."

# config/test.env
cat > config/test.env << 'EOF'
ENVIRONMENT=test
GCP_PROJECT_ID=ra-autohaus-tracker
BIGQUERY_DATASET=autohaus
LOG_LEVEL=DEBUG
PORT=8080
EOF

# config/prod.env
cat > config/prod.env << 'EOF'
ENVIRONMENT=prod
GCP_PROJECT_ID=ra-autohaus-tracker
BIGQUERY_DATASET=autohaus
LOG_LEVEL=INFO
PORT=8080
EOF

# 11. Scripts erstellen
echo "🔧 Essential Scripts erstellen..."

# scripts/setup_local.sh
cat > scripts/setup_local.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Lokale Entwicklungsumgebung für RA Autohaus Tracker"

# Virtual Environment erstellen/aktivieren
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual Environment aktiviert"
else
    echo "📦 Virtual Environment erstellen..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Dependencies installieren
echo "📚 Dependencies installieren..."
pip install --upgrade pip
pip install -r requirements.txt

# VS Code Konfiguration
echo "💻 VS Code Konfiguration..."
mkdir -p .vscode
cat > .vscode/settings.json << 'VSCODE_EOF'
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/venv": true
    }
}
VSCODE_EOF

echo "✅ Setup abgeschlossen!"
echo "📝 Nächste Schritte:"
echo "1. Virtual Environment aktivieren: source venv/bin/activate"
echo "2. Google Cloud auth: gcloud auth application-default login"
echo "3. VS Code starten: code ."
EOF

# scripts/start_dev.sh
cat > scripts/start_dev.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 RA Autohaus Tracker Development Server"

# Virtual Environment aktivieren
source venv/bin/activate

# Environment Variables
export PYTHONPATH=$(pwd)
export ENVIRONMENT=development
export GCP_PROJECT_ID=ra-autohaus-tracker

echo "🌐 Starting server on http://localhost:8080"
echo "📖 API Docs: http://localhost:8080/docs"

uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
EOF

# Scripts ausführbar machen
chmod +x scripts/*.sh

echo "✅ Repository-Struktur vollständig erstellt!"
echo ""
echo "📁 Verzeichnisstruktur:"
find . -type d -not -path './.*' | sort

echo ""
echo "📝 Nächste Schritte:"
echo "1. Virtual Environment einrichten: ./scripts/setup_local.sh"
echo "2. Ersten Commit erstellen: git add . && git commit -m 'Initial setup'"
echo "3. Zu GitHub pushen: git push -u origin main"ls

