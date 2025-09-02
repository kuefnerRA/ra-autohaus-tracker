#!/bin/bash
# RA Autohaus Tracker - Verbessertes Projekt Setup
# Maximilian Reinhardt - Reinhardt Automobile GmbH

set -e  # Script bei Fehlern beenden

echo "🚀 Setze RA Autohaus Tracker Projekt auf..."

# Python-Version prüfen
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d" " -f2 | cut -d"." -f1,2)
REQUIRED_VERSION="3.12"

echo "🐍 Python Version: $PYTHON_VERSION"

if ! python3 -c "import sys; assert sys.version_info >= (3, 12)" 2>/dev/null; then
    echo "❌ Python 3.12 oder höher ist erforderlich. Aktuelle Version: $PYTHON_VERSION"
    echo "Bitte installiere Python 3.12: https://www.python.org/downloads/"
    exit 1
fi

# Projekt-Verzeichnis erstellen
echo "📁 Erstelle Projekt-Struktur..."

# Python Virtual Environment
echo "🔧 Erstelle Virtual Environment..."
if command -v python3.12 &> /dev/null; then
    python3.12 -m venv venv
else
    python3 -m venv venv
fi

# Virtual Environment aktivieren
echo "⚡ Aktiviere Virtual Environment..."
source venv/bin/activate

# Python-Version im venv prüfen
VENV_PYTHON_VERSION=$(python --version 2>&1 | cut -d" " -f2)
echo "✅ Virtual Environment Python Version: $VENV_PYTHON_VERSION"

# Pip upgraden
echo "📦 Upgrade pip..."
pip install --upgrade pip

# Projektstruktur erstellen
echo "📂 Erstelle Projektstruktur..."
mkdir -p src/{core,services,api/routes,models,handlers}
mkdir -p tests/{unit,integration}
mkdir -p scripts/{setup,deploy}
mkdir -p docs

# __init__.py Dateien erstellen
echo "🔨 Erstelle __init__.py Dateien..."
touch src/__init__.py
touch src/core/__init__.py  
touch src/services/__init__.py
touch src/api/__init__.py
touch src/api/routes/__init__.py
touch src/models/__init__.py
touch src/handlers/__init__.py
touch tests/__init__.py

# Requirements.txt erstellen (Python 3.12 kompatibel)
echo "📋 Erstelle requirements.txt..."
cat > requirements.txt << 'EOF'
# FastAPI & Server
fastapi>=0.109.0,<0.115.0
uvicorn[standard]>=0.27.0,<0.31.0

# Google Cloud
google-cloud-bigquery>=3.15.0,<4.0.0
google-auth>=2.27.0,<3.0.0

# Pydantic & Validation  
pydantic>=2.6.0,<3.0.0
pydantic-settings>=2.2.0,<3.0.0
email-validator>=2.1.0,<3.0.0

# HTTP & Multipart
python-multipart>=0.0.7,<0.1.0
httpx>=0.26.0,<0.28.0

# Logging & Structure
structlog>=24.1.0,<25.0.0
rich>=13.7.0,<14.0.0

# Environment & Config
python-dotenv>=1.0.0,<2.0.0
typing-extensions>=4.9.0,<5.0.0

# Testing
pytest>=8.0.0,<9.0.0
pytest-asyncio>=0.23.0,<0.25.0

# Development (optional)
# black>=24.0.0,<25.0.0
# isort>=5.13.0,<6.0.0
# mypy>=1.8.0,<2.0.0
EOF

# .env Template erstellen
echo "⚙️ Erstelle .env Template..."
cat > .env.template << 'EOF'
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=ra-autohaus-tracker
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
BIGQUERY_DATASET=autohaus

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
USE_MOCK_BIGQUERY=true

# API Configuration  
API_HOST=0.0.0.0
API_PORT=8080
API_RELOAD=true

# Integration Settings
FLOWERS_EMAIL_ENABLED=true
ZAPIER_WEBHOOK_SECRET=your-webhook-secret
EOF

# Lokale .env für Development erstellen
echo "📝 Erstelle lokale .env Datei..."
cp .env.template .env

# .gitignore erstellen
echo "🚫 Erstelle .gitignore..."
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv/

# Google Cloud
service-account*.json
*.json
!package*.json

# Environment
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Logs
*.log
logs/

# OS
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Build
build/
dist/
*.egg-info/
EOF

# README.md erstellen  
echo "📚 Erstelle README.md..."
cat > README.md << 'EOF'
# RA Autohaus Tracker

Fahrzeugprozess-Tracking-System für Reinhardt Automobile GmbH

## Quick Start

```bash
# Repository klonen oder Setup-Script ausführen
cd ra-autohaus-tracker

# Environment aktivieren
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Environment konfigurieren
cp .env.template .env
# .env mit eigenen Werten befüllen

# Lokale Entwicklung starten
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

## Architektur

- **FastAPI** Backend mit async/await
- **BigQuery** als zentrale Datenbank  
- **Google Cloud Run** für Production
- **Integrationen**: Zapier, Flowers Email, Audaris API

## Services

- **BigQueryService**: Data Layer
- **VehicleService**: Business Logic
- **ProcessService**: Integration Logic *(Phase 2)*
- **DashboardService**: Analytics & KPIs *(Phase 2)*
- **InfoService**: System Configuration *(Phase 2)*

## Development

### Phase 1 - MVP (Aktuell)
- [x] BigQuery Setup & Schema
- [x] Core Services (BigQuery, Vehicle)
- [x] FastAPI Application
- [x] Vehicle API Endpoints
- [x] Dependency Injection
- [ ] Lokale Tests

### Phase 2 - Business Logic
- [ ] ProcessService Implementation
- [ ] Dashboard Service & KPIs
- [ ] Erweiterte API Endpoints

### Phase 3 - Integrationen  
- [ ] Zapier Webhook Integration
- [ ] Flowers Email Handler
- [ ] Unified Data Processing

### Phase 4 - Production
- [ ] Google Cloud Run Deployment
- [ ] CI/CD Pipeline
- [ ] Production Monitoring

## API Endpoints

- `GET /health` - System Health Check
- `GET /info` - System Information
- `GET /api/v1/fahrzeuge` - Fahrzeuge abrufen
- `GET /api/v1/fahrzeuge/{fin}` - Fahrzeug Details
- `POST /api/v1/fahrzeuge` - Fahrzeug erstellen
- `PUT /api/v1/fahrzeuge/{fin}/status` - Status aktualisieren

## Environment Variables

Siehe `.env.template` für alle verfügbaren Konfigurationsoptionen.

## Testing

```bash
# Unit Tests
pytest tests/unit/

# Integration Tests  
pytest tests/integration/

# Alle Tests
pytest
```
EOF

# Dependencies installieren
echo "📦 Installiere Dependencies..."
echo "   Das kann einige Minuten dauern..."

if ! pip install -r requirements.txt; then
    echo "❌ Fehler beim Installieren der Dependencies"
    echo "🔧 Versuche Fallback-Installation..."
    
    # Einzelne wichtige Pakete installieren
    pip install fastapi uvicorn pydantic python-dotenv structlog rich
    
    echo "⚠️ Basis-Pakete installiert. Weitere Pakete können später nachinstalliert werden."
    echo "   Führe 'pip install -r requirements.txt' erneut aus, wenn Probleme behoben sind."
else
    echo "✅ Alle Dependencies erfolgreich installiert"
fi

# Basis-Module erstellen für sofortigen Test
echo "🔧 Erstelle Basis-Module..."

# Leeres main.py für ersten Test
cat > src/main.py << 'EOF'
"""
FastAPI Main Application - Basis Version
RA Autohaus Tracker MVP
"""

from fastapi import FastAPI

app = FastAPI(
    title="RA Autohaus Tracker",
    version="1.0.0-alpha"
)

@app.get("/")
def root():
    return {"message": "RA Autohaus Tracker MVP läuft!"}

@app.get("/health")  
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=True)
EOF

# Test-Script erstellen
echo "🧪 Erstelle Test-Script..."
cat > test_setup.py << 'EOF'
#!/usr/bin/env python3
"""
Setup-Test für RA Autohaus Tracker
"""

def test_imports():
    """Testet ob alle wichtigen Module importiert werden können."""
    try:
        import fastapi
        print("✅ FastAPI importiert")
        
        import uvicorn
        print("✅ Uvicorn importiert")
        
        import pydantic
        print("✅ Pydantic importiert")
        
        import structlog
        print("✅ Structlog importiert")
        
        print("\n🎉 Alle Basis-Module erfolgreich importiert!")
        return True
        
    except ImportError as e:
        print(f"❌ Import-Fehler: {e}")
        return False

def test_app():
    """Testet ob die FastAPI App startet."""
    try:
        from src.main import app
        print("✅ FastAPI App erfolgreich importiert")
        return True
    except Exception as e:
        print(f"❌ App-Import-Fehler: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Teste Setup...")
    
    if test_imports() and test_app():
        print("\n✅ Setup-Test erfolgreich!")
        print("🚀 Du kannst jetzt mit der Entwicklung beginnen:")
        print("   uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload")
    else:
        print("\n❌ Setup-Test fehlgeschlagen")
        print("   Prüfe die Fehler oben und führe 'pip install -r requirements.txt' erneut aus")
EOF

echo "🎉 Setup abgeschlossen!"
echo ""
echo "📋 Nächste Schritte:"
echo "1. Setup testen: python test_setup.py"
echo "2. App starten: uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload"
echo "3. Browser öffnen: http://localhost:8080"
echo "4. API Docs: http://localhost:8080/docs"
echo ""
echo "🔧 Bei Problemen:"
echo "- Prüfe Python Version: python --version"
echo "- Virtual Environment aktiviert? source venv/bin/activate"
echo "- Dependencies neu installieren: pip install -r requirements.txt"

# Setup-Test ausführen
echo ""
echo "🧪 Führe Setup-Test aus..."
python test_setup.py