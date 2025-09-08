# RA Autohaus Tracker

Fahrzeugprozess-Tracking-System für Reinhardt Automobile GmbH

## ✅ Phase 1-3 erfolgreich abgeschlossen

### Zusammenfassung
Der RA Autohaus Tracker ist bereit für Phase 4 (Deployment). Alle geplanten Features der ersten drei Phasen wurden implementiert und getestet.

### Implementierte Features
- **7 Services:** BigQuery, Vehicle, Process, Dashboard, Info, Unified & Integration Handler
- **15+ API-Endpoints:** Vollständige REST API mit Swagger-Dokumentation
- **2 Webhook-Integrationen:** Zapier & Flowers Email funktionsfähig
- **Normalisierte Datenbank:** 2 BigQuery-Tabellen mit Partitionierung

### Test-Coverage
- **34 Tests gesamt:** 30 Unit-Tests, 4 Integration-Tests
- **InfoService:** 94% Coverage
- **DashboardService:** 77% Coverage  
- **Integration-Tests:** 100% bestanden

### Technische Highlights
- Service-orientierte Architektur mit Dependency Injection
- Vollständige Type-Safety mit Pydantic Models
- Unified Data Processing für alle Datenquellen
- SLA-Monitoring und KPI-Dashboard vorbereitet
- **Service Account Impersonation** für sichere lokale Entwicklung

### Nächste Schritte (Phase 4)
- [ ] Google Cloud Run Deployment
- [ ] CI/CD Pipeline mit GitHub Actions
- [ ] Production Monitoring Setup
- [ ] Load Testing & Performance-Optimierung

### Endpoints bereit für Integration
- `POST /api/v1/integration/zapier/webhook` - Zapier-Daten empfangen
- `POST /api/v1/integration/flowers/email` - Email-Parser
- `GET /api/v1/dashboard/kpis` - Real-time KPIs
- `GET /api/v1/info/prozesse` - Prozess-Definitionen

---

**Status:** Ready for Deployment 🚀  
**Datum:** 08.09.2025  
**Entwickler:** Thomas Küfner

## Quick Start

### Entwicklungsumgebung einrichten (täglich)

```bash
# Repository klonen (einmalig)
git clone https://github.com/reinhardtautomobile/ra-autohaus-tracker.git
cd ra-autohaus-tracker

# Development Environment starten (täglich)
source scripts/setup-dev.sh  # Aktiviert venv & Authentication
run-server-bg                # Startet Server im Hintergrund

# API testen
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/fahrzeuge/

# Server Management
server-status   # Status prüfen
server-logs     # Logs anschauen
stop-server     # Server stoppen
```

### Alternative: Manuelle Einrichtung

```bash
# Virtual Environment aktivieren
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Service Account Impersonation einrichten
gcloud auth application-default login \
    --impersonate-service-account=ra-dev-local@ra-autohaus-tracker.iam.gserviceaccount.com

# Server starten
python -m src.main
```

## Development Setup

### Service Account Impersonation

Das Projekt nutzt Service Account Impersonation für sichere lokale Entwicklung ohne Key-Dateien:

```bash
# Impersonation-Berechtigung einrichten (einmalig)
gcloud iam service-accounts add-iam-policy-binding \
    ra-dev-local@ra-autohaus-tracker.iam.gserviceaccount.com \
    --member="user:kuefner@reinhardtautomobile.de" \
    --role="roles/iam.serviceAccountTokenCreator"
```

### Benötigte IAM-Rollen

Der Service Account `ra-dev-local` benötigt folgende Rollen:

**Basis-Entwicklung:**
- `roles/bigquery.dataEditor`
- `roles/bigquery.jobUser`
- `roles/bigquery.user`
- `roles/storage.objectAdmin`
- `roles/logging.viewer`
- `roles/monitoring.viewer`

**Phase 4 (Deployment):**
- `roles/run.developer`
- `roles/cloudbuild.builds.editor`
- `roles/artifactregistry.writer`
- `roles/iam.serviceAccountUser`
- `roles/secretmanager.secretAccessor`

### Development Scripts

| Script | Zweck | Verwendung |
|--------|-------|------------|
| `scripts/setup-dev.sh` | Environment Setup mit venv & Auth | `source scripts/setup-dev.sh` |
| `scripts/server-control.sh` | Server Management | `./scripts/server-control.sh {start\|stop\|status}` |
| `scripts/test_credentials.py` | Auth-Test | `python scripts/test_credentials.py` |

## Architektur

- **FastAPI** Backend mit async/await
- **BigQuery** als zentrale Datenbank mit Service Account Impersonation
- **Google Cloud Run** für Production
- **Integrationen**: Zapier, Flowers Email, Audaris API
- **Authentication**: Service Account Impersonation (Development) / Service Account (Production)

## Services

- **BigQueryService**: Data Layer mit Connection Management
- **VehicleService**: Business Logic mit SLA-Monitoring
- **ProcessService**: Integration Logic (Phase 2)
- **DashboardService**: Analytics & KPIs (Phase 2)
- **InfoService**: System Configuration (Phase 2)
- **UnifiedHandler**: Zentrale Datenverarbeitung (Phase 3)
- **Integration Handlers**: Zapier & Flowers (Phase 3)

## Development Phases

### ✅ Phase 1 - MVP (Abgeschlossen)
- [x] BigQuery Setup & Schema
- [x] Core Services (BigQuery, Vehicle)
- [x] FastAPI Application
- [x] Vehicle API Endpoints
- [x] Dependency Injection
- [x] Lokale Tests

### ✅ Phase 2 - Business Logic (Abgeschlossen)
- [x] ProcessService Implementation
- [x] Dashboard Service & KPIs
- [x] Erweiterte API Endpoints
- [x] InfoService für Konfiguration

### ✅ Phase 3 - Integrationen (Abgeschlossen)
- [x] Zapier Webhook Integration
- [x] Flowers Email Handler
- [x] Unified Data Processing
- [x] Integration Tests

### 🚀 Phase 4 - Production (In Arbeit)
- [ ] Google Cloud Run Deployment
- [ ] CI/CD Pipeline mit GitHub Actions
- [ ] Production Monitoring Setup
- [ ] Load Testing & Performance-Optimierung

## API Endpoints

### Fahrzeuge
- `GET /api/v1/fahrzeuge` - Fahrzeuge abrufen
- `GET /api/v1/fahrzeuge/{fin}` - Fahrzeug Details
- `POST /api/v1/fahrzeuge` - Fahrzeug erstellen
- `PUT /api/v1/fahrzeuge/{fin}/status` - Status aktualisieren

### Dashboard
- `GET /api/v1/dashboard/kpis` - Haupt-KPIs
- `GET /api/v1/dashboard/warteschlangen` - Warteschlangen-Status
- `GET /api/v1/dashboard/sla` - SLA-Übersicht
- `GET /api/v1/dashboard/bearbeiter` - Bearbeiter-Workload

### Integration
- `POST /api/v1/integration/zapier/webhook` - Zapier-Integration
- `POST /api/v1/integration/flowers/email` - Flowers Email-Integration

### System
- `GET /health` - System Health Check
- `GET /info` - System Information
- `GET /docs` - Swagger UI Documentation

## Environment Variables

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=ra-autohaus-tracker
BIGQUERY_DATASET=autohaus
SERVICE_ACCOUNT=ra-dev-local@ra-autohaus-tracker.iam.gserviceaccount.com

# Environment
ENVIRONMENT=development  # oder production
LOG_LEVEL=DEBUG         # oder INFO für Production

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080
```

Siehe `.env.template` für alle verfügbaren Konfigurationsoptionen.

## Testing

```bash
# Alle Tests ausführen
pytest

# Unit Tests
pytest tests/unit/

# Integration Tests  
pytest tests/integration/

# Mit Coverage
pytest --cov=src --cov-report=html

# Einzelnen Test ausführen
pytest tests/unit/test_info_service.py -v
```

## Docker Support (Phase 4)

```bash
# Build
docker build -t ra-autohaus-tracker .

# Run mit Host-Credentials (Development)
docker run -p 8080:8080 \
    -v ~/.config/gcloud:/root/.config/gcloud:ro \
    -e GOOGLE_CLOUD_PROJECT=ra-autohaus-tracker \
    ra-autohaus-tracker

# Production Build (mit Cloud Build)
gcloud builds submit --tag gcr.io/ra-autohaus-tracker/api
```

## Troubleshooting

### Authentication-Probleme

```bash
# Token erneuern
gcloud auth application-default login \
    --impersonate-service-account=ra-dev-local@ra-autohaus-tracker.iam.gserviceaccount.com

# Credentials testen
python scripts/test_credentials.py
```

### Service Account nicht in Console sichtbar

Service Accounts ohne Rollen werden in der IAM-Übersicht nicht angezeigt.
Lösung: Mindestens eine Rolle zuweisen oder unter "Service Accounts" nachschauen.

### Server läuft bereits

```bash
# Prozess finden und beenden
pkill -f "src.main"
# oder
stop-server
```

## Dokumentation

- **[Architecture Documentation](./docs/architecture.md)** - System-Überblick
- **[Service Documentation](./docs/services.md)** - Service-Layer Details
- **[Data Models](./docs/data-models.md)** - Datenmodell-Dokumentation
- **[Development Setup](./docs/development-setup.md)** - Entwicklungsumgebung
- **API Documentation** - http://localhost:8080/docs (Swagger UI)

## Projekt-Struktur

```
ra-autohaus-tracker/
├── src/
│   ├── api/             # API Routes & Endpoints
│   ├── core/            # Core Configuration & Dependencies
│   ├── models/          # Pydantic Models
│   ├── services/        # Business Logic Services
│   └── main.py          # FastAPI Application
├── tests/
│   ├── unit/            # Unit Tests
│   └── integration/     # Integration Tests
├── scripts/
│   ├── setup-dev.sh     # Development Environment Setup
│   ├── server-control.sh # Server Management
│   └── test_credentials.py # Auth Testing
├── docs/                # Dokumentation
├── .env.template        # Environment Template
├── requirements.txt     # Python Dependencies
├── Dockerfile          # Container Definition
└── README.md           # Diese Datei
```

## Kontakt & Support

**Technische Ansprechpartner:**
- **Maximilian Reinhardt** - Geschäftsführer, Product Owner
- **Thomas Küfner** - Lead Developer, Domain Expert

**Repository:** https://github.com/reinhardtautomobile/ra-autohaus-tracker

---

*Letzte Aktualisierung: 08.09.2025*