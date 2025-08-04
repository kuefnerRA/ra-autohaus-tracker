# RA Autohaus Tracker

Multi-Source Fahrzeugprozess-Tracking-System für Reinhardt Automobile.

## Features

- 🚗 Fahrzeug-Stammdatenmanagement
- 📊 Prozess-Tracking (Transport, Aufbereitung, Werkstatt, Foto, etc.)
- 📧 Multi-Source Datenintegration (E-Mail, Webhooks, Zapier)
- ⏱️ SLA-Monitoring und Alerts
- 📈 Dashboard mit Warteschlangen und KPIs
- ☁️ Cloud-native Architektur (Google Cloud)

## Technologie-Stack

- **Backend**: Python FastAPI
- **Datenbank**: Google BigQuery
- **Hosting**: Google Cloud Run
- **Frontend**: Looker Studio Dashboards
- **CI/CD**: GitHub Actions

## Entwicklung

### Voraussetzungen
- Python 3.11+
- Google Cloud CLI
- Docker (optional)

### Setup
```bash
# Repository klonen
git clone https://github.com/kuefnerRA/ra-autohaus-tracker.git
cd ra-autohaus-tracker

# Entwicklungsumgebung einrichten
./scripts/setup_local.sh

# Virtual Environment aktivieren
source venv/bin/activate

# Development Server starten
uvicorn src.main:app --reload
```

### API Dokumentation
- Lokale Entwicklung: http://localhost:8080/docs
- Test-Umgebung: TBD
- Produktion: TBD

## Deployment

### Test-Umgebung
```bash
./scripts/deploy_test.sh
```

### Produktion
```bash
./scripts/deploy_prod.sh
```

## Architektur

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flowers SW    │    │    Audaris      │    │   AutoCRM       │
│   (E-Mail/API)  │    │     (API)       │    │    (API)        │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴───────────┐
                    │   Cloud Run API         │
                    │   (FastAPI)             │
                    └─────────────┬───────────┘
                                  │
                    ┌─────────────┴───────────┐
                    │   BigQuery              │
                    │   (Data Warehouse)      │
                    └─────────────┬───────────┘
                                  │
                    ┌─────────────┴───────────┐
                    │   Looker Studio         │
                    │   (Dashboards)          │
                    └─────────────────────────┘
```

## Lizenz

Proprietär - Reinhardt Automobile GmbH
