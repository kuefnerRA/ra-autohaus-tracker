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
**Datum:** 04.09.2025
**Entwickler:** Thomas Küfner

1 und 3

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
