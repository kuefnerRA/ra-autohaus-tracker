# Service-Architektur - RA Autohaus Tracker

**Reinhardt Automobile GmbH**  
**Version:** 1.1.0  
**Datum:** 14.10.2025  
**Autor:** Maximilian Reinhardt

## Überblick

Das RA Autohaus Tracker System implementiert eine **Service-orientierte Architektur (SOA)** mit klar getrennten Verantwortlichkeiten nach dem **Layered Architecture Pattern**. Jeder Service hat eine spezifische Rolle und kommuniziert über definierte Schnittstellen.

## Architektur-Prinzipien

### SOLID-Prinzipien
- **Single Responsibility**: Jeder Service hat genau eine Verantwortlichkeit
- **Open/Closed**: Erweiterbar ohne Änderung bestehender Services
- **Liskov Substitution**: Services sind austauschbar (z.B. Mock vs. Production)
- **Interface Segregation**: Klare, fokussierte Service-Interfaces
- **Dependency Inversion**: High-Level Services abhängig von Abstraktionen

### Dependency Injection
- **Singleton Pattern** für Service-Instanzen
- **Lazy Loading** mit `@lru_cache()`
- **Constructor Injection** für Service-Dependencies
- **Mock-Support** für Testing und lokale Entwicklung

## Service-Layer-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   FastAPI       │  │   REST APIs     │  │   WebHooks      │ │
│  │   Routes        │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Integration Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ UnifiedHandler  │  │ ZapierHandler   │  │ FlowersHandler  │ │
│  │                 │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Business Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  VehicleService │  │ ProcessService  │  │DashboardService │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  EmailService   │  │ProcessCleanup   │  │VINDecoderService│ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ BigQueryService │  │  InfoService    │  │  External APIs  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Core Components                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Dependencies   │  │ BackgroundTasks │  │   Performance   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ LoggingConfig   │  │    Mappings     │  │ ProcessConfig   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   BigQuery      │  │  Cloud Storage  │  │   Cloud Run     │ │
│  │   Database      │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Implementierte Services

### Data Layer Services

#### BigQueryService
**Datei:** `src/services/bigquery_service.py`

**Verantwortlichkeiten:**
- Zentrale BigQuery-Verbindungsverwaltung
- Service Account Impersonation
- CRUD-Operationen für alle Tabellen
- Parametrisierte Query-Ausführung
- Mock-Fallback für lokale Entwicklung

**Kernmethoden:**
```python
async def create_fahrzeug_stamm(fahrzeug_data: Dict[str, Any]) -> bool
async def create_fahrzeug_prozess(prozess_data: Dict[str, Any]) -> bool
async def get_fahrzeug_by_fin(fin: str) -> Optional[Dict[str, Any]]
async def get_fahrzeuge_mit_prozessen(limit: int, prozess_typ: str, bearbeiter: str) -> List[Dict[str, Any]]
async def health_check() -> Dict[str, Any]
```

**Konfiguration:**
- **Service Account:** `ra-autohaus-tracker-sa@ra-autohaus-tracker.iam.gserviceaccount.com`
- **Dataset:** `ra-autohaus-tracker.autohaus`
- **Tabellen:** `fahrzeuge_stamm`, `fahrzeug_prozesse`
- **Partitionierung:** Nach `created_at` (täglich)
- **Clustering:** Nach `fin`, `marke`, `prozess_typ`, `bearbeiter`

#### InfoService
**Datei:** `src/services/info_service.py`

**Verantwortlichkeiten:**
- System-Konfigurationsverwaltung
- Bearbeiter-Informationen
- SLA-Definitionen
- Prozesstyp-Konfigurationen

**Kernfunktionalitäten:**
- Bereitstellung von System-Metadaten
- Konfigurierbare Geschäftsregeln
- Mapping-Definitionen für Integrationen

### Business Layer Services

#### VehicleService
**Datei:** `src/services/vehicle_service.py`

**Verantwortlichkeiten:**
- Geschäftslogik für Fahrzeugverwaltung
- SLA-Berechnung und -Überwachung
- Fahrzeugvalidierung und Plausibilitätsprüfung
- Bearbeiter-Name-Normalisierung
- KPI-Berechnung und -Aggregation

**Dependencies:**
```python
VehicleService(bigquery_service: BigQueryService)
```

**Kernmethoden:**
```python
async def get_vehicles(limit: int, prozess_typ: str, bearbeiter: str, sla_critical_only: bool) -> List[FahrzeugMitProzess]
async def get_vehicle_details(fin: str) -> Optional[FahrzeugMitProzess]
async def create_complete_vehicle(fahrzeug_data: FahrzeugStammCreate, prozess_data: Optional[FahrzeugProzessCreate]) -> FahrzeugMitProzess
async def update_vehicle_status(fin: str, new_status: str, bearbeiter: str, notizen: str) -> bool
async def get_vehicle_kpis() -> List[KPIData]
```

#### ProcessService
**Datei:** `src/services/process_service.py`

**Verantwortlichkeiten:**
- Prozess-Lifecycle-Management
- Status-Übergänge und Validierung
- Prozess-Historie und Tracking
- Integration mit externen Systemen

**Kernfunktionalitäten:**
- Prozess-Erstellung und -Updates
- Automatische Status-Transitions
- SLA-Tracking pro Prozesstyp
- Bulk-Operationen für Prozesse

#### DashboardService
**Datei:** `src/services/dashboard_service.py`

**Verantwortlichkeiten:**
- Real-time KPI-Aggregation
- Dashboard-Datenaufbereitung
- Performance-Metriken
- Trend-Analysen

**Kernfunktionalitäten:**
- Echtzeit-Statistiken
- SLA-Performance-Monitoring
- Bearbeiter-Workload-Analyse
- Historische Datenauswertung

#### EmailService
**Datei:** `src/services/email_service.py`

**Verantwortlichkeiten:**
- E-Mail-Verarbeitung und -Parsing
- Flowers-E-Mail-Integration
- Template-Management
- Notification-Versand

**Kernfunktionalitäten:**
- Strukturierte E-Mail-Datenextraktion
- Automatische Prozess-Updates via E-Mail
- E-Mail-basierte Benachrichtigungen
- Template-Engine für Standardmails

#### ProcessCleanupService
**Datei:** `src/services/process_cleanup_service.py`

**Verantwortlichkeiten:**
- Automatische Datenbereinigung
- Veraltete Prozesse archivieren
- Duplikat-Erkennung und -Bereinigung
- Background-Job-Management

**Kernfunktionalitäten:**
- Scheduled Cleanup-Jobs
- Intelligente Duplikat-Erkennung
- Archivierung alter Prozesse
- Performance-Optimierung durch Datenreduktion

#### VINDecoderService
**Datei:** `src/services/vin_decoder_service.py`

**Verantwortlichkeiten:**
- VIN (Fahrzeugidentnummer) Dekodierung
- Fahrzeugdaten-Anreicherung
- Hersteller- und Modellerkennung
- Technische Datenextraktion

**Kernfunktionalitäten:**
- VIN-Validierung und -Parsing
- Automatische Marken-/Modellerkennung
- Baujahr-Extraktion
- Integration externer VIN-Datenbanken

### Integration Layer (Handlers)

#### UnifiedHandler
**Datei:** `src/handlers/unified_handler.py`

**Verantwortlichkeiten:**
- Zentrale Eingangsschnittstelle für alle Datenquellen
- Normalisierung heterogener Datenformate
- Routing zu spezialisierten Handlers
- Fehlerbehandlung und Retry-Logic

#### ZapierHandler
**Datei:** `src/handlers/zapier_handler.py`

**Verantwortlichkeiten:**
- Zapier-Webhook-Verarbeitung
- Feld-Mapping für Zapier-Daten
- Validierung eingehender Payloads
- Response-Formatierung für Zapier

**Endpoint:** `/api/v1/integration/zapier/webhook`

#### FlowersHandler
**Datei:** `src/handlers/flowers_handler.py`

**Verantwortlichkeiten:**
- Flowers-Software E-Mail-Parsing
- Strukturierte Datenextraktion
- Prozess-Updates aus E-Mails
- Fehlerhafte E-Mail-Behandlung

**Endpoint:** `/api/v1/integration/flowers/email`

#### DataTransformer
**Datei:** `src/handlers/data_transformer.py`

**Verantwortlichkeiten:**
- Datenformat-Transformation
- Feld-Mapping zwischen Systemen
- Datenvalidierung und -Bereinigung
- Type-Conversion und Normalisierung

### Core Components

#### Dependencies
**Datei:** `src/core/dependencies.py`

**Verantwortlichkeiten:**
- Service-Lifecycle-Management
- Dependency Injection Container
- Singleton-Pattern-Implementation
- Service-Factory-Funktionen

**Kernfunktionen:**
```python
@lru_cache()
def get_bigquery_service() -> BigQueryService
@lru_cache()
def get_vehicle_service() -> VehicleService
async def startup_services()
async def shutdown_services()
async def check_all_services_health()
```

#### BackgroundTasks
**Datei:** `src/core/background_tasks.py`

**Verantwortlichkeiten:**
- Asynchrone Task-Verwaltung
- Scheduled Jobs Koordination
- Task-Queue-Management
- Background-Worker-Orchestrierung

**Implementierte Tasks:**
- Process Cleanup (alle 10 Minuten in Production)
- SLA-Monitoring (kontinuierlich)
- Daten-Synchronisation

#### LoggingConfig
**Datei:** `src/core/logging_config.py`

**Verantwortlichkeiten:**
- Strukturiertes Logging-Setup
- Log-Level-Konfiguration
- Log-Format-Definition
- Performance-Logging

**Features:**
- Structlog-Integration
- JSON-Renderer für Production
- Console-Renderer für Development
- Request-ID-Tracking

#### Performance
**Datei:** `src/core/performance.py`

**Verantwortlichkeiten:**
- Performance-Metriken-Erfassung
- Response-Time-Tracking
- Database-Query-Profiling
- Memory-Usage-Monitoring

**Metriken:**
- API Response Times
- BigQuery Query Performance
- Service-Operation-Dauer
- Background-Task-Execution-Time

#### Mappings
**Datei:** `src/core/mappings.py`

**Verantwortlichkeiten:**
- Zentrale Mapping-Definitionen
- Bearbeiter-Name-Normalisierung
- Prozesstyp-Mappings
- Feld-Transformations-Regeln

**Mapping-Tabellen:**
```python
BEARBEITER_MAPPING = {
    "Thomas K.": "Thomas Küfner",
    "Max R.": "Maximilian Reinhardt",
    "T. Küfner": "Thomas Küfner",
    "M. Reinhardt": "Maximilian Reinhardt"
}
```

#### ProcessConfig
**Datei:** `src/core/process_config.py`

**Verantwortlichkeiten:**
- Prozess-Konfigurationen
- SLA-Definitionen
- Status-Übergangs-Matrix
- Prioritäts-Regeln

**Konfiguration:**
```python
PROZESS_CONFIG = {
    ProzessTyp.EINKAUF:      {"sla_stunden": 48,  "priority_range": [1, 3]},
    ProzessTyp.ANLIEFERUNG:  {"sla_stunden": 24,  "priority_range": [2, 4]},
    ProzessTyp.AUFBEREITUNG: {"sla_stunden": 72,  "priority_range": [3, 5]},
    ProzessTyp.FOTO:         {"sla_stunden": 24,  "priority_range": [4, 6]},
    ProzessTyp.WERKSTATT:    {"sla_stunden": 168, "priority_range": [2, 5]},
    ProzessTyp.VERKAUF:      {"sla_stunden": 720, "priority_range": [1, 3]}
}
```

### API Routes

#### Vehicles Route
**Datei:** `src/api/routes/vehicles.py`  
**Prefix:** `/api/v1/fahrzeuge`

**Endpoints:**
- `GET /` - Liste aller Fahrzeuge
- `GET /{fin}` - Fahrzeugdetails
- `POST /` - Neues Fahrzeug anlegen
- `PUT /{fin}` - Fahrzeug aktualisieren
- `DELETE /{fin}` - Fahrzeug löschen
- `GET /kpis` - KPI-Dashboard-Daten

#### Process Route
**Datei:** `src/api/routes/process.py`  
**Prefix:** `/api/v1/prozesse`

**Endpoints:**
- `GET /` - Prozessliste
- `GET /{prozess_id}` - Prozessdetails
- `POST /` - Neuer Prozess
- `PUT /{prozess_id}` - Prozess-Update
- `POST /bulk` - Bulk-Prozess-Updates

#### Dashboard Route
**Datei:** `src/api/routes/dashboard.py`  
**Prefix:** `/api/v1/dashboard`

**Endpoints:**
- `GET /overview` - Dashboard-Übersicht
- `GET /sla-status` - SLA-Performance
- `GET /workload` - Bearbeiter-Auslastung
- `GET /trends` - Trend-Analysen

#### Integration Route
**Datei:** `src/api/routes/integration.py`  
**Prefix:** `/api/v1/integration`

**Endpoints:**
- `POST /zapier/webhook` - Zapier-Integration
- `POST /flowers/email` - Flowers-Email-Parser
- `POST /unified` - Unified Data Handler

#### Email Route
**Datei:** `src/api/routes/email.py`  
**Prefix:** `/api/v1/email`

**Endpoints:**
- `POST /parse` - E-Mail-Parsing
- `POST /send` - E-Mail-Versand
- `GET /templates` - Template-Liste
- `POST /templates` - Template erstellen

#### Info Route
**Datei:** `src/api/routes/info.py`  
**Prefix:** `/api/v1/info`

**Endpoints:**
- `GET /system` - System-Information
- `GET /config` - Konfiguration
- `GET /bearbeiter` - Bearbeiter-Liste
- `GET /prozess-typen` - Prozesstyp-Definitionen

## Geschäftslogik-Konfiguration

### SLA-Berechnung
- **Start-Zeit:** `prozess.start_timestamp` oder `prozess.erstellt_am`
- **Deadline:** Start-Zeit + SLA-Stunden
- **Kritisch:** Wenn `tage_bis_deadline <= 1`
- **Überfällig:** Wenn `tage_bis_deadline < 0`

### Geschäftsregeln
- **FIN-Validierung:** 17-stellige alphanumerische Fahrzeugidentifizierungsnummer
- **Duplikat-Prüfung:** Keine doppelten FINs im System
- **Baujahr-Plausibilität:** Nicht in der Zukunft liegend
- **Einkaufspreis-Grenze:** Maximum 500.000 EUR (Plausibilitätsprüfung)
- **Auto-Fahrzeugerstellung:** Bei Prozess ohne Fahrzeug wird automatisch ein Fahrzeugstamm angelegt

## Data Flow

### Fahrzeug-Erstellung
```
1. API Request → VehicleService.create_complete_vehicle()
2. Optional: VIN-Dekodierung → VINDecoderService.decode()
3. Geschäftsregeln validieren → _validate_vehicle_data()
4. Fahrzeugstammdaten speichern → BigQueryService.create_fahrzeug_stamm()
5. Optional: Prozess erstellen → BigQueryService.create_fahrzeug_prozess()
6. SLA-Daten berechnen → _calculate_sla_data()
7. Vollständiges Fahrzeug zurückgeben
```

### Integration-Flow (Zapier/Flowers)
```
1. Webhook/Email → Integration Route
2. Handler-Verarbeitung → ZapierHandler/FlowersHandler
3. Daten-Transformation → DataTransformer
4. Unified Processing → UnifiedHandler
5. Auto-Fahrzeug-Check → VehicleService
6. Prozess-Erstellung → ProcessService
7. Response/Acknowledgment
```

### Background-Cleanup
```
1. Scheduler-Trigger (alle 10 Min)
2. ProcessCleanupService.execute()
3. Identifikation alter/duplikater Prozesse
4. Archivierung/Bereinigung
5. Performance-Statistiken Update
```

## Environment-Konfiguration

### Produktive Umgebung
```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=ra-autohaus-tracker
BIGQUERY_DATASET=autohaus
USE_MOCK_BIGQUERY=false
GOOGLE_SERVICE_ACCOUNT=ra-autohaus-tracker-sa@ra-autohaus-tracker.iam.gserviceaccount.com

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080

# Background Jobs
ENABLE_BACKGROUND_JOBS=true
CLEANUP_INTERVAL_MINUTES=10
```

### Entwicklungsumgebung
```bash
# Google Cloud Configuration  
GOOGLE_CLOUD_PROJECT=ra-autohaus-tracker
BIGQUERY_DATASET=autohaus
USE_MOCK_BIGQUERY=false  # oder true für lokale Entwicklung

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080
API_RELOAD=true

# Background Jobs
ENABLE_BACKGROUND_JOBS=false
```

## Error Handling

### Service-Level Error Handling
- **BigQueryService:** GoogleAPIError, NotFound, Timeout-Handling
- **VehicleService:** ValidationError, BusinessRuleViolation, DataNotFound
- **ProcessService:** StatusTransitionError, ProcessNotFound
- **EmailService:** ParseError, TemplateNotFound
- **VINDecoderService:** InvalidVIN, DecodingError
- **Structured Logging:** Alle Errors mit Context-Informationen
- **Graceful Degradation:** Mock-Fallback bei Service-Ausfällen

### Standard Error Response Pattern
```python
try:
    result = await service.operation()
    logger.info("✅ Operation erfolgreich", context_data)
    return result
except SpecificException as e:
    logger.error("❌ Spezifischer Fehler", error=str(e))
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error("💥 Unerwarteter Fehler", error=str(e))
    raise HTTPException(status_code=500, detail="Interner Serverfehler")
```

## Testing-Strategie

### Unit Tests
- **Services:** Mock Dependencies, isolierte Business-Logic-Tests
- **Handlers:** Input-Validation, Transformation-Tests
- **Core Components:** Configuration-Tests, Mapping-Tests
- **Pydantic Models:** Validierung und Serialisierung

### Integration Tests
- **Service-Kommunikation:** Echte Service-Dependencies
- **BigQuery Integration:** Testdaten in separatem Dataset
- **End-to-End:** API-Requests bis zur Datenbank
- **Webhook-Tests:** Mock-Payloads von Zapier/Flowers

### Performance Tests
- **Load Testing:** Concurrent Request Handling
- **Query Performance:** BigQuery-Optimierung
- **Background Jobs:** Task-Execution-Time

## Monitoring & Observability

### Structured Logging
```python
logger = structlog.get_logger(__name__)
logger.info("Operation erfolgreich", 
           service="VehicleService",
           operation="create_vehicle",
           fin="WVWZZZ1JZ8W123456",
           duration_ms=150,
           request_id=request.state.request_id)
```

### Metriken
- **Response Times:** Service-Operation-Dauer
- **Error Rates:** Fehlerquote nach Service und Operation
- **Business Metrics:** KPIs, SLA-Verletzungen, Fahrzeugdurchsatz
- **Integration Metrics:** Webhook-Success-Rate, Email-Parse-Rate
- **Background Job Metrics:** Execution-Time, Cleanup-Count

### Health Check Endpoints
- **`/health`:** System-weiter Health Check
- **`/api/v1/fahrzeuge/health`:** Vehicle Service Health
- **Service-interne Health Checks:** BigQuery-Verbindung, Dependencies
- **Integration Health:** Externe API-Verfügbarkeit

## Deployment-Architektur

### Lokale Entwicklung
- **Mock-Services:** Lokale Entwicklung ohne Google Cloud
- **Hot Reload:** Automatischer Code-Reload bei Änderungen
- **Debug-Endpoints:** Erweiterte Logging und Debugging-Features
- **Test-Datenbank:** Separates BigQuery-Dataset für Tests

### Google Cloud Run Production
- **Container-Deployment:** Automatisches Scaling basierend auf Traffic
- **Service Account Impersonation:** Sichere BigQuery-Authentifizierung  
- **Environment-based Configuration:** Produktions- vs. Entwicklungskonfiguration
- **Health Check Integration:** Google Cloud Load Balancer Health Checks
- **Background Job Orchestration:** Cloud Scheduler Integration

## Wartung und Weiterentwicklung

### Code-Qualität
- **Type Safety:** Vollständige Type-Annotations mit Pydantic
- **SOLID-Prinzipien:** Saubere Architektur-Patterns
- **Error Handling:** Comprehensive Exception-Management
- **Documentation:** Inline-Dokumentation und Architecture Decision Records
- **Code Reviews:** Merge-Request-basierte Qualitätskontrolle

### Performance-Optimierung
- **BigQuery Query-Optimierung:** Partitionierung und Clustering
- **Caching-Strategien:** In-Memory-Caching für häufige Abfragen
- **Async/Await:** Non-blocking I/O für bessere Concurrency
- **Connection Pooling:** Effiziente Ressourcen-Nutzung
- **Lazy Loading:** Services nur bei Bedarf initialisieren

### Security
- **Service Account Impersonation:** Principle of Least Privilege
- **Input Validation:** Pydantic-basierte Eingabevalidierung
- **SQL Injection Prevention:** Parametrisierte Queries
- **Error Information Disclosure:** Sichere Error-Messages in Produktion
- **API Rate Limiting:** DDoS-Schutz (geplant)
- **Authentication/Authorization:** OAuth2-Integration (geplant)

## Roadmap - Zukünftige Erweiterungen

### Phase 4 - Q4 2025
- **Redis-Integration:** Caching-Layer für Performance
- **GraphQL API:** Alternative API-Schnittstelle
- **Audit-Log-Service:** Vollständige Änderungsverfolgung
- **Notification-Service:** Push-Notifications und Alerts

### Phase 5 - Q1 2026
- **ML-Integration:** Predictive Analytics für SLA-Vorhersagen
- **Multi-Tenant-Support:** Mandantenfähigkeit
- **API Gateway:** Rate-Limiting und API-Key-Management
- **Reporting-Service:** Automatisierte Report-Generierung

## Versionierung

### Aktuelle Version: 1.1.0
- **Major Release 1:** Produktivsetzung Core-Funktionalität
- **Minor Release 1:** Integration Layer vollständig implementiert
- **Patch Level 0:** Stabile Version ohne kritische Bugs

### Changelog
- **1.1.0** (14.10.2025): Integration Layer, Background Tasks, VIN-Decoder
- **1.0.0** (03.09.2025): Initial Release mit Core-Services
- **0.9.0** (15.08.2025): Beta-Version mit BigQuery-Integration
- **0.5.0** (01.08.2025): Alpha-Version mit Mock-Services