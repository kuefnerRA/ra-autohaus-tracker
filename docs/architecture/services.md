# Service-Architektur - RA Autohaus Tracker

**Reinhardt Automobile GmbH**  
**Version:** 1.0.0-alpha  
**Datum:** 03.09.2025  
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
│                     Business Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  VehicleService │  │ ProcessService  │  │DashboardService │ │
│  │   (Phase 1)     │  │   (Phase 2)     │  │   (Phase 2)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ BigQueryService │  │  InfoService    │  │  External APIs  │ │
│  │   (Phase 1)     │  │   (Phase 2)     │  │    (Audaris)    │ │
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

## Implementierte Services (Phase 1)

### BigQueryService (Data Layer)

**Datei:** `src/services/bigquery_service.py`

**Verantwortlichkeiten:**
- Zentrale BigQuery-Verbindungsverwaltung
- Service Account Impersonation
- CRUD-Operationen für `fahrzeuge_stamm` und `fahrzeug_prozesse`
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

### VehicleService (Business Layer)

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

**Geschäftsregeln:**
- **FIN-Validierung:** 17-stellige alphanumerische Fahrzeugidentifizierungsnummer
- **Duplikat-Prüfung:** Keine doppelten FINs im System
- **Baujahr-Plausibilität:** Nicht in der Zukunft liegend
- **Einkaufspreis-Grenze:** Maximum 500.000 EUR (Plausibilitätsprüfung)

## Geschäftslogik-Konfiguration

### SLA-Konfiguration nach Prozesstyp

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

**SLA-Berechnung:**
- **Start-Zeit:** `prozess.start_timestamp` oder `prozess.erstellt_am`
- **Deadline:** Start-Zeit + SLA-Stunden
- **Kritisch:** Wenn `tage_bis_deadline <= 1`
- **Überfällig:** Wenn `tage_bis_deadline < 0`

### Bearbeiter-Mapping

```python
BEARBEITER_MAPPING = {
    "Thomas K.": "Thomas Küfner",
    "Max R.": "Maximilian Reinhardt",
    "T. Küfner": "Thomas Küfner",
    "M. Reinhardt": "Maximilian Reinhardt"
}
```

**Zweck:** Normalisierung unterschiedlicher Namensformate aus verschiedenen Datenquellen (Zapier, E-Mail, manuelle Eingabe).

## Data Flow

### Fahrzeug-Erstellung
```
1. API Request → VehicleService.create_complete_vehicle()
2. Geschäftsregeln validieren → _validate_vehicle_data()
3. Fahrzeugstammdaten speichern → BigQueryService.create_fahrzeug_stamm()
4. Optional: Prozess erstellen → BigQueryService.create_fahrzeug_prozess()
5. SLA-Daten berechnen → _calculate_sla_data()
6. Vollständiges Fahrzeug zurückgeben
```

### Fahrzeug-Abruf mit Prozessen
```
1. API Request → VehicleService.get_vehicles()
2. Filter normalisieren (Bearbeiter-Mapping)
3. JOIN-Query ausführen → BigQueryService.get_fahrzeuge_mit_prozessen()
4. Business Logic anwenden → _enrich_vehicle_data()
5. SLA-Filter anwenden → _is_sla_critical()
6. Pydantic Models konvertieren → FahrzeugMitProzess
```

### KPI-Berechnung
```
1. Alle Fahrzeuge abrufen → get_vehicles(limit=1000)
2. Aggregationen berechnen:
   - Gesamtanzahl Fahrzeuge
   - Verteilung nach Prozesstyp
   - SLA-kritische Fahrzeuge
   - Durchschnittlicher Einkaufspreis
3. KPIData Models erstellen
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
```

## Dependency Injection

### Service-Initialisierung
```python
# src/core/dependencies.py

@lru_cache()
def get_bigquery_service() -> BigQueryService:
    """Singleton BigQuery Service."""
    return BigQueryService(
        project_id=os.getenv('GOOGLE_CLOUD_PROJECT'),
        dataset_name=os.getenv('BIGQUERY_DATASET')
    )

@lru_cache()
def get_vehicle_service() -> VehicleService:
    """Singleton Vehicle Service mit BigQuery Dependency."""
    bigquery_service = get_bigquery_service()
    return VehicleService(bigquery_service=bigquery_service)
```

### Lifecycle Management
```python
async def startup_services():
    """Services beim Application-Start initialisieren."""
    bigquery_service = get_bigquery_service()
    vehicle_service = get_vehicle_service()
    health = await check_all_services_health()
    
async def shutdown_services():
    """Services beim Application-Shutdown aufräumen."""
    # Cleanup-Logik falls erforderlich
```

## Error Handling

### Service-Level Error Handling
- **BigQueryService:** GoogleAPIError, NotFound, Timeout-Handling
- **VehicleService:** ValidationError, BusinessRuleViolation, DataNotFound
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
- **BigQueryService:** Mock BigQuery Client, Parametrisierte Queries testen
- **VehicleService:** Mock BigQueryService, Geschäftslogik isoliert testen
- **Pydantic Models:** Validierung und Serialisierung testen

### Integration Tests
- **Service-Kommunikation:** Echte Service-Dependencies
- **BigQuery Integration:** Testdaten in separatem Dataset
- **End-to-End:** API-Requests bis zur Datenbank

### Health Checks
- **Service-Level:** `health_check()` Methode in jedem Service
- **System-Level:** `/health` Endpoint für Monitoring
- **Dependency-Check:** Alle abhängigen Services prüfen

## Monitoring & Observability

### Structured Logging
```python
logger = structlog.get_logger(__name__)
logger.info("Operation erfolgreich", 
           service="VehicleService",
           operation="create_vehicle",
           fin="WVWZZZ1JZ8W123456",
           duration_ms=150)
```

### Metriken
- **Response Times:** Service-Operation-Dauer
- **Error Rates:** Fehlerquote nach Service und Operation
- **Business Metrics:** KPIs, SLA-Verletzungen, Fahrzeugdurchsatz

### Health Check Endpoints
- **`/health`:** System-weiter Health Check
- **`/api/v1/fahrzeuge/health`:** Vehicle Service Health
- **Service-interne Health Checks:** BigQuery-Verbindung, Dependencies

## Deployment-Architektur

### Lokale Entwicklung
- **Mock-Services:** Lokale Entwicklung ohne Google Cloud
- **Hot Reload:** Automatischer Code-Reload bei Änderungen
- **Debug-Endpoints:** Erweiterte Logging und Debugging-Features

### Google Cloud Run Production
- **Container-Deployment:** Automatisches Scaling basierend auf Traffic
- **Service Account Impersonation:** Sichere BigQuery-Authentifizierung  
- **Environment-based Configuration:** Produktions- vs. Entwicklungskonfiguration
- **Health Check Integration:** Google Cloud Load Balancer Health Checks

## Roadmap - Geplante Services (Phase 2+)

### ProcessService (Integration Layer)
- **Zapier Webhook Integration:** Automatische Prozess-Updates
- **Flowers Email Processing:** E-Mail-basierte Statusänderungen  
- **Unified Data Processing:** Einheitliche Verarbeitung aus verschiedenen Quellen
- **Background Tasks:** Asynchrone Verarbeitung von Prozess-Updates

### DashboardService (Analytics Layer)
- **Real-time KPIs:** Live-Dashboard-Daten
- **SLA-Monitoring:** Überwachung und Alerting bei SLA-Verletzungen
- **Bearbeiter-Workload:** Kapazitätsplanung und Arbeitsverteilung
- **Historische Analysen:** Trend-Analyse und Reporting

### InfoService (Configuration Layer)
- **System-Konfiguration:** Zentrale Verwaltung von Prozess-Definitionen
- **Bearbeiter-Management:** Dynamische Bearbeiter-Zuordnung
- **SLA-Konfiguration:** Anpassbare SLA-Vorgaben nach Prozesstyp
- **Integration-Mappings:** Konfigurierbare Feld-Mappings für verschiedene Datenquellen

## Wartung und Weiterentwicklung

### Code-Qualität
- **Type Safety:** Vollständige Type-Annotations mit Pydantic
- **SOLID-Prinzipien:** Saubere Architektur-Patterns
- **Error Handling:** Comprehensive Exception-Management
- **Documentation:** Inline-Dokumentation und Architecture Decision Records

### Performance-Optimierung
- **BigQuery Query-Optimierung:** Partitionierung und Clustering
- **Caching-Strategien:** Redis für häufige Abfragen (zukünftige Erweiterung)
- **Async/Await:** Non-blocking I/O für bessere Concurrency
- **Connection Pooling:** Effiziente Ressourcen-Nutzung

### Security
- **Service Account Impersonation:** Principle of Least Privilege
- **Input Validation:** Pydantic-basierte Eingabevalidierung
- **SQL Injection Prevention:** Parametrisierte Queries
- **Error Information Disclosure:** Sichere Error-Messages in Produktion
