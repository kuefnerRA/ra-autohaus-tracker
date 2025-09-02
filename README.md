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
