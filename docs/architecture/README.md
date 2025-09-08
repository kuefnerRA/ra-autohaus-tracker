# Architektur-Dokumentation - RA Autohaus Tracker

**Reinhardt Automobile GmbH**  
**Version:** 1.0.0-alpha  
**Stand:** 03.09.2025

## Überblick

Diese Dokumentation beschreibt die technische Architektur des **RA Autohaus Tracker Systems** - einer modernen Fahrzeugprozess-Tracking-Lösung für Reinhardt Automobile GmbH.

## System-Überblick

Das RA Autohaus Tracker System ist eine **Cloud-native Anwendung** auf Basis von **FastAPI**, **Google BigQuery** und **Google Cloud Run**. Es implementiert eine **Service-orientierte Architektur (SOA)** mit klaren Schichten-Trennung und **Domain-Driven Design** Prinzipien.

### Kern-Features
- 🚗 **Fahrzeugstammdaten-Verwaltung** mit FIN-basierter Identifikation
- 📊 **Prozess-Tracking** mit SLA-Monitoring für 6 Hauptprozesse
- 🔄 **Multi-Channel-Integration** (Zapier, E-Mail, APIs)
- 📈 **Real-time Dashboard** mit KPIs und Warteschlangen-Monitoring
- ⚡ **High-Performance** durch BigQuery-Backend mit Partitionierung

### Technologie-Stack
- **Backend:** FastAPI (Python 3.12) mit async/await
- **Datenbank:** Google BigQuery mit Service Account Impersonation
- **Hosting:** Google Cloud Run mit automatischem Scaling
- **Integrationen:** Zapier Webhooks, Flowers E-Mail, Audaris API
- **Type-Safety:** Pydantic Models mit vollständiger Validierung

## Dokumentationsstruktur

### 📋 [services.md](./services.md) - Service-Architektur
**Umfang:** Vollständige Service-Layer-Dokumentation
- Service-orientierte Architektur mit 4 Schichten
- Implementierte Services (BigQueryService, VehicleService)
- Dependency Injection und Lifecycle Management
- Geschäftslogik-Konfiguration (SLA, Bearbeiter-Mapping)
- Data Flow und Error Handling
- Testing-Strategie und Monitoring
- Deployment-Architektur und Roadmap

**Zielgruppe:** Entwickler, Solution Architects, DevOps

### 📊 [data-models.md](./data-models.md) - Datenmodelle
**Umfang:** Detaillierte Datenmodell-Dokumentation
- BigQuery-Schema mit Partitionierung und Clustering
- Pydantic Models mit Validierung und Type-Safety
- Datenbeziehungen und Geschäftsregeln
- SLA-Datenmodell und Integration-Mappings
- Audit-Logging und DSGVO-Compliance
- Performance-Optimierung und Schema-Evolution

**Zielgruppe:** Data Engineers, Backend-Entwickler, Database Architects

## Quick Start

### Für Entwickler
```bash
# Repository klonen
cd ra-autohaus-tracker

# Dependencies installieren
pip install -r requirements.txt

# Environment konfigurieren
cp .env.template .env
# .env mit Google Cloud Credentials befüllen

# System starten
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

### Für Administratoren
1. **Google Cloud Setup:** [services.md - Deployment-Architektur](./services.md#deployment-architektur)
2. **BigQuery Setup:** `python scripts/setup/setup_bigquery.py`
3. **Service Account:** [services.md - Environment-Konfiguration](./services.md#environment-konfiguration)
4. **Production Deployment:** Google Cloud Run mit CI/CD

## Systemarchitektur-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                      │
│         FastAPI REST API + Interactive Docs               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Business Layer                         │
│    VehicleService │ ProcessService │ DashboardService      │
│     (Phase 1)     │   (Phase 2)    │    (Phase 2)          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                            │
│  BigQueryService  │  InfoService   │   External APIs       │
│    (Phase 1)      │   (Phase 2)    │    (Audaris)          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                       │
│   Google BigQuery  │  Cloud Run    │   Cloud Storage       │
└─────────────────────────────────────────────────────────────┘
```

## Entwicklungsstand

### ✅ Phase 1 - Foundation Setup (Abgeschlossen)
- **Projekt-Setup:** Python 3.12 venv, Requirements, Struktur
- **BigQuery Setup:** Schema, Tabellen, Service Account, Beispieldaten
- **Core Services:** BigQueryService (Data Layer), VehicleService (Business Layer)
- **FastAPI Application:** REST-API, Dependency Injection, Error Handling
- **Lokale Tests:** Unit Tests für alle Services, Integration Tests

### 🔄 Phase 2 - Business Logic (Abgeschlossen)
- **ProcessService:** Zapier/E-Mail Integration, Unified Data Processing
- **DashboardService:** Real-time KPIs, SLA-Monitoring, Analytics
- **InfoService:** System-Konfiguration, Prozess-Management

### ✅ Phase 1-3 - Abgeschlossen (04.09.2025)
- **34 Tests** implementiert (30 Unit, 4 Integration)
- **7 Services** (BigQuery, Vehicle, Process, Dashboard, Info + 2 Handler)
- **Integration Layer** mit Zapier & Flowers Webhooks funktionsfähig
- **Test Coverage:** InfoService 94%, DashboardService 77%

### 🚀 Phase 4 - Production (Geplant)
- **Google Cloud Run:** Production Deployment, Auto-Scaling
- **CI/CD Pipeline:** GitHub Actions, Automated Testing, Deployments
- **Monitoring:** Cloud Operations, Structured Logging, Alerting
- **Security:** WAF, IAM Policies, Secrets Management

### ToDo
- **Erweiterte APIs:** Webhooks, Background Tasks, Advanced Filtering
- **Zapier Integration:** Webhook-Endpoints, Feldmapping, Fehlerbehandlung
- **Flowers E-Mail:** IMAP-Integration, E-Mail-Parsing, Auto-Processing
- **Audaris API:** Fahrzeugdaten-Sync, External Data Enrichment
- **Background Jobs:** Async Processing, Queue Management

## API-Endpoints

## Implementierte API-Endpunkte (Stand: 04.09.2025)

### 🚗 Fahrzeuge (7 Endpunkte)
- GET `/api/v1/fahrzeuge/` - Fahrzeugliste mit Filtern
- POST `/api/v1/fahrzeuge/` - Neues Fahrzeug erstellen  
- GET `/api/v1/fahrzeuge/{fin}` - Fahrzeugdetails abrufen
- PUT `/api/v1/fahrzeuge/{fin}/status` - Status aktualisieren
- GET `/api/v1/fahrzeuge/kpis/overview` - Fahrzeug-KPIs
- GET `/api/v1/fahrzeuge/statistics/summary` - Fahrzeug-Statistiken
- GET `/api/v1/fahrzeuge/health` - Vehicle Service Health

### 📋 Process Management (5 Endpunkte)
- POST `/api/v1/process/zapier/webhook` - Zapier-Webhook (alt)
- POST `/api/v1/process/email/parse` - Email-Parser (alt)
- POST `/api/v1/process/unified` - Unified Data Processing
- GET `/api/v1/process/health` - Process Service Health
- GET `/api/v1/process/info` - Process Service Info

### 📊 Dashboard (6 Endpunkte)
- GET `/api/v1/dashboard/kpis` - Haupt-KPIs
- GET `/api/v1/dashboard/warteschlangen` - Warteschlangen-Status
- GET `/api/v1/dashboard/sla` - SLA-Übersicht
- GET `/api/v1/dashboard/bearbeiter` - Bearbeiter-Workload
- GET `/api/v1/dashboard/statistik/{prozess_typ}` - Prozess-Statistik
- GET `/api/v1/dashboard/trends` - Trend-Analyse

### ℹ️ Info (8 Endpunkte)
- GET `/api/v1/info/prozesse` - Alle Prozess-Definitionen
- GET `/api/v1/info/prozesse/{prozess_typ}` - Einzelne Prozess-Definition
- GET `/api/v1/info/bearbeiter` - Alle Bearbeiter
- GET `/api/v1/info/bearbeiter/{name}` - Einzelner Bearbeiter
- GET `/api/v1/info/status` - Status-Definitionen
- GET `/api/v1/info/system` - System-Konfiguration
- GET `/api/v1/info/mappings` - Integration-Mappings
- GET `/api/v1/info/health` - Info Service Health

### 🔗 Integration (2 Endpunkte)
- POST `/api/v1/integration/zapier/webhook` - Zapier-Integration (neu)
- POST `/api/v1/integration/flowers/email` - Flowers Email-Integration

### 🛠 System (4 Endpunkte)
- GET `/` - API Root
- GET `/health` - System Health-Check
- GET `/info` - System Information
- GET `/dev/reset-services` - [DEV] Service Reset

**Gesamt: 32 implementierte Endpunkte**

## Geschäftsprozesse

### Fahrzeugprozesse (6 Haupttypen)
1. **Einkauf** (SLA: 48h) - Fahrzeugakquisition und -bewertung
2. **Anlieferung** (SLA: 24h) - Physische Fahrzeugübernahme
3. **Aufbereitung** (SLA: 72h) - Fahrzeugvorbereitung für Verkauf
4. **Foto** (SLA: 24h) - Professionelle Fahrzeugfotografie
5. **Werkstatt** (SLA: 168h) - Reparaturen und TÜV-Vorbereitung
6. **Verkauf** (SLA: 720h) - Verkaufsprozess und Kundenbetreuung

### SLA-Monitoring
- **Kritisch:** ≤ 1 Tag bis Deadline
- **Warnung:** ≤ 3 Tage bis Deadline
- **Überfällig:** Deadline überschritten
- **Automatische Alerts:** Bei SLA-Verletzungen (geplant)

## Datenfluss

```
1. Datenerfassung
   ├── Manuelle Eingabe (API)
   ├── Zapier Webhooks
   ├── Flowers E-Mail
   └── Audaris API Sync

2. Validierung & Processing
   ├── Pydantic Model Validation
   ├── Geschäftsregeln-Prüfung
   ├── FIN-Duplikat-Check
   └── SLA-Berechnung

3. Datenspeicherung
   ├── BigQuery fahrzeuge_stamm
   ├── BigQuery fahrzeug_prozesse
   └── Audit Logging

4. Business Intelligence
   ├── KPI-Berechnung
   ├── SLA-Monitoring
   ├── Warteschlangen-Analyse
   └── Dashboard-Updates
```

## Sicherheit & Compliance

### Authentifizierung
- **Google Cloud Service Account** mit Impersonation
- **Principle of Least Privilege** für BigQuery-Zugriffe
- **API-Schlüssel** für externe Integrationen (geplant)

### Datenvalidierung
- **Pydantic Models** mit Type-Safety und Input Validation
- **SQL Injection Prevention** durch parametrisierte Queries
- **Error Information Disclosure** Prevention in Production

### DSGVO-Compliance
- **Datenminimierung** - nur geschäftsrelevante Daten
- **Zweckbindung** - ausschließlich Fahrzeugprozess-Tracking
- **Audit Trail** - vollständige Nachvollziehbarkeit aller Änderungen
- **Löschkonzept** - Fahrzeuge als "inaktiv" markieren

## Performance & Skalierung

### BigQuery-Optimierungen
- **Partitionierung** nach `created_at` (täglich)
- **Clustering** nach häufigen Filter-Feldern (`fin`, `marke`, `prozess_typ`)
- **Query-Optimierung** mit parametrisierten Abfragen
- **Connection Pooling** für effiziente Ressourcen-Nutzung

### Anwendungsperformance
- **Async/Await** für non-blocking I/O-Operationen  
- **Dependency Injection** mit Singleton-Pattern
- **Structured Logging** mit Context-Informationen
- **Health Checks** auf Service- und System-Ebene

## Wartung & Support

### Code-Qualität
- **Type Safety** mit vollständigen Type-Annotations
- **SOLID-Prinzipien** in Service-Architektur
- **Error Handling** mit strukturiertem Exception-Management
- **Dokumentation** mit Architecture Decision Records

### Monitoring
- **Structured Logging** mit structlog und JSON-Format
- **Health Check Endpoints** für alle Services
- **Performance Metriken** (Response Times, Error Rates)
- **Business Metriken** (SLA-Verletzungen, Fahrzeugdurchsatz)

### Backup & Recovery
- **BigQuery Automatic Backups** (7 Tage Standard, 90 Tage konfigurierbar)
- **Point-in-Time Recovery** für Datenwiederherstellung
- **Export-Funktionen** für Datenmigration und Archivierung

## Kontakt & Support

**Technische Ansprechpartner:**
- **Maximilian Reinhardt** - Geschäftsführer, Product Owner
- **Thomas Küfner** - Hauptbearbeiter, Domain Expert

**Dokumentation:**
- **GitHub Repository:** ra-autohaus-tracker
- **API-Dokumentation:** `/docs` Endpoint (Swagger UI)
- **Architektur-Updates:** Diese Dokumentation wird bei größeren Änderungen aktualisiert

**Support:**
- **Issues:** GitHub Issue Tracker
- **Deployment:** Google Cloud Console
- **Monitoring:** Cloud Operations Suite

---

*Diese Dokumentation ist ein Living Document und wird kontinuierlich mit der Systementwicklung aktualisiert.*
