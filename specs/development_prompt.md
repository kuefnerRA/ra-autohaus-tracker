# Entwicklungs-Prompt für RA Autohaus Tracker - Neuentwicklung

## Projekt-Kontext

Entwickle ein **Fahrzeugprozess-Tracking-System** für **Reinhardt Automobile GmbH** mit absolut sauberer Architektur und normalisierten Datenbank-Design.
Die Fahrzeuge sind immer einem Prozess und einem Status des Prozesses zugeordnet. 

Es soll eine API bereitgestellt werden, über die Prozeßänderungen bzw. Statusänderungen zu Fahrzeugen übermittelt werden können. Jedes Fahrzeug ist immer einem eindeutigen Prozess zugeordnet und darin einem Status. Die Statushistorie zu jedem Fahrzeug soll gespeichert werden. Zu jedem Prozeß gehört auch ein Bearbeiter.
Ein Fahrzeug wird über die FIN eindeutig identifiziert. Fahrzeugstammdaten werden unabhängig vom Status gespeichert. Es soll möglich sein, bei der Übermittlung einer Statusänderung Fahrzeugstammdaten zu übermitteln, die dann auch gespeichert werden.
Die Prozessinformationen kommen aus einem Workflow Management System namens Flowers.
Zusätzliche Informationen zu Fahrzeugen, die nicht in Flowers enthalten sind, können über eine API zu einem Fahrzeugverwaltungssytsem namens Audaris abgerufen werden.

Die API wird über unterschiedliche Kanäle (Email, Zapier Webhook, Allgemeiner Webhook) aufgerufen, für die unterschiedliche Endpunkte vorgesehen sind.
Wichtig ist die Ermittlung von Prozeßlaufzeiten, nach prozesstyp und Bearbeiter.
Die API soll über Google Cloud Run bereitgestellt werden.
Die Datenspeicherung soll über BigQuery erfolgen
Das Setup von Cloud Run und Big Query soll über Skripte erfolgen.
Das Deployment von Entwicklungs- und Produktionsumgebung soll über Skripte erfolgen.
Die Authentifizierung an GC soll über Service-Accounts erfolgen.

## Wichtige Vorgehensweisen
Die Entwicklung soll in angemessenen Schritten erfolgen. Jeder Entwicklungsschritt soll immer zuerst lokal getestet werden, es sollen alle erkannten Fehler zuerst lokal beseitigt werden, bevor es zum nächsten Schritt weitergeht.

## Technische Anforderungen

### **Entwicklungsumgebung:**
- **Python 3.12** mit venv
- **FastAPI** Framework  
- **BigQuery** als zentrale Datenbank
- **Google Cloud Run** für Production-Deployment
- **GitHub** Repository: `ra-autohaus-tracker`
- **Projekt-ID:** `ra-autohaus-tracker`
- **Dataset:** `autohaus`

### **Code-Qualität (KRITISCH):**
- **Maximale Codehygiene:** Keine IDE-Fehler (Pylance/mypy)
- **Type-Safety:** Vollständige Type-Annotations für alle Funktionen
- **Import-Konsistenz:** Alle Imports mit `src.` Prefix
- **Zeichenkodierung:** UTF-8 für deutsche Umlaute (für, über, Küfner)
- **Error-Handling:** Comprehensive exception handling mit aussagekräftigen Logs

### **Architektur-Prinzipien:**
- **Modular:** Klare Service-Trennung nach Domain
- **SOLID-Prinzipien:** Single Responsibility, Dependency Injection
- **API-First:** RESTful Design mit automatischer OpenAPI-Dokumentation
- **Async/Await:** Für alle I/O-Operationen

## Datenbank-Design (Normalisiert)

### **Tabelle: `fahrzeuge_stamm`** (Stammdaten)
```sql
CREATE TABLE fahrzeuge_stamm (
  fin STRING NOT NULL,
  marke STRING,
  modell STRING,
  antriebsart STRING,
  farbe STRING,
  baujahr INTEGER,
  ersterfassung_datum DATETIME DEFAULT CURRENT_DATETIME(),
  aktiv BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  erstellt_aus_email BOOLEAN DEFAULT FALSE,
  datenquelle_fahrzeug STRING DEFAULT 'api',
  datum_erstzulassung DATE,
  kw_leistung INTEGER,
  km_stand INTEGER,
  anzahl_fahrzeugschluessel INTEGER,
  bereifungsart STRING,
  anzahl_vorhalter INTEGER,
  ek_netto NUMERIC,
  besteuerungsart STRING
);
```

### **Tabelle: `fahrzeug_prozesse`** (Prozess-Tracking)
```sql
CREATE TABLE fahrzeug_prozesse (
  prozess_id STRING NOT NULL,
  fin STRING NOT NULL,
  prozess_typ STRING NOT NULL,
  status STRING NOT NULL,
  bearbeiter STRING,
  prioritaet INTEGER DEFAULT 5,
  anlieferung_datum DATE,
  start_timestamp DATETIME,
  ende_timestamp DATETIME,
  dauer_minuten INTEGER,
  sla_tage INTEGER,
  sla_deadline_datum DATE,
  tage_bis_sla_deadline INTEGER,
  standzeit_tage INTEGER,
  datenquelle STRING DEFAULT 'api',
  notizen STRING,
  zusatz_daten STRING,
  erstellt_am DATETIME DEFAULT CURRENT_DATETIME(),
  aktualisiert_am DATETIME DEFAULT CURRENT_DATETIME(),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

## Geschäftslogik-Anforderungen

### **Fahrzeugprozesse (6 Haupttypen):**
```python
PROZESSE = {
    "Einkauf": {"sla_stunden": 48, "priority_range": [1,3]},
    "Anlieferung": {"sla_stunden": 24, "priority_range": [2,4]},
    "Aufbereitung": {"sla_stunden": 72, "priority_range": [3,5]},
    "Foto": {"sla_stunden": 24, "priority_range": [4,6]},
    "Werkstatt": {"sla_stunden": 168, "priority_range": [2,5]},
    "Verkauf": {"sla_stunden": 720, "priority_range": [1,3]}
}
```

### **Bearbeiter-Mapping:**
```python
BEARBEITER_MAPPING = {
    "Thomas K.": "Thomas Küfner",
    "Max R.": "Maximilian Reinhardt",
}
```

### **Integration-Mappings:**
```python
PROZESS_MAPPING = {
    "gwa": "Aufbereitung",
    "garage": "Werkstatt",
    "photos": "Foto", 
    "sales": "Verkauf",
    "purchase": "Einkauf",
    "delivery": "Anlieferung"
}
```

## Service-Architektur

### **1. BigQueryService (Data Layer):**
- **Zweck:** Zentrale Datenbankoperationen für beide Tabellen
- **Verantwortung:** CRUD für `fahrzeuge_stamm` und `fahrzeug_prozesse`
- **Features:** Schema-Validierung, JOIN-Queries, Mock-Fallback
- **Methods:** `create_fahrzeug_stamm()`, `create_fahrzeug_prozess()`, `get_fahrzeuge_mit_prozessen()`

### **2. VehicleService (Business Layer):**
- **Zweck:** Fahrzeug-spezifische Geschäftslogik
- **Dependency:** `BigQueryService`
- **Features:** SLA-Berechnung, Prioritäts-Labels, Fahrzeug-Status-Management
- **Methods:** `get_vehicles()`, `get_vehicle_details()`, `create_complete_vehicle()`

### **3. ProcessService (Integration Layer):**
- **Zweck:** Multi-Source Data Processing (Zapier, E-Mail, APIs)
- **Dependency:** `BigQueryService` + `FlowersHandler`
- **Features:** Unified Data Processing, Bearbeiter-Mapping, Auto-Vehicle-Creation
- **Methods:** `process_unified_data()`, `create_process()`, `update_process_status()`

### **4. DashboardService (Analytics Layer):**
- **Zweck:** KPIs, Statistiken, Warteschlangen-Monitoring
- **Dependency:** `BigQueryService`
- **Features:** Real-time KPIs, SLA-Überwachung, Kapazitäts-Management
- **Methods:** `get_kpis()`, `get_warteschlangen()`, `get_sla_overview()`

### **5. InfoService (Configuration Layer):**
- **Zweck:** System-Konfiguration, Prozess-Definitionen
- **Dependency:** Keine (statische Daten)
- **Features:** Prozess-Info, Bearbeiter-Info, System-Config

## API-Endpunkt-Design

### **Fahrzeug-Management:**
```
GET    /fahrzeuge                    # Liste mit Filtern
GET    /fahrzeuge/{fin}              # Details für spezifische FIN  
POST   /fahrzeuge                    # Neues Fahrzeug erstellen
PUT    /fahrzeuge/{fin}/status       # Status-Update
```

### **Dashboard & Analytics:**
```
GET    /dashboard/kpis              # Haupt-KPIs
GET    /dashboard/warteschlangen    # Warteschlangen-Status
GET    /dashboard/sla               # SLA-Übersicht
GET    /dashboard/bearbeiter        # Bearbeiter-Workload
```

### **Integration-Webhooks:**
```
POST   /integration/zapier/webhook     # Zapier-Integration
POST   /integration/email/webhook      # Flowers Email-Integration
GET    /integration/debug/mappings     # Debug-Info
GET    /integration/health            # Integration-Health
```

### **System-Information:**
```
GET    /info/prozesse              # Prozess-Definitionen
GET    /info/bearbeiter            # Bearbeiter-Info  
GET    /info/system                # System-Konfiguration
GET    /health                     # Gesamt-Health-Check
```

## Entwicklungsrichtlinien

### **Dependency Injection:**
- **Zentrale BigQueryService** einmal initialisiert
- **Lazy Loading** mit `@lru_cache()` für Service-Dependencies
- **Legacy-Support** für Rückwärtskompatibilität während Entwicklung

### **Error-Handling Standard:**
```python
try:
    # Business Logic
    result = await service.operation()
    logger.info(f"✅ Operation erfolgreich: {context}")
    return result
except SpecificException as e:
    logger.error(f"❌ Spezifischer Fehler: {e}")
    return fallback_response()
except Exception as e:
    logger.error(f"💥 Unerwarteter Fehler: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

### **Logging-Standard:**
```python
logger = logging.getLogger(__name__)
# ✅ Erfolg, ❌ Fehler, ⚠️ Warnung, 📊 Daten-Info, 🚀 Startup
```

## Integrations-Anforderungen

### **Zapier-Integration:**
- **Flexibles Schema:** Unterstützt verschiedene Feldnamen
- **Prozess-Mapping:** `gwa` → `Aufbereitung`
- **Bearbeiter-Normalisierung:** `Thomas K.` → `Thomas Küfner`
- **Background Tasks:** Für BigQuery-Speicherung

### **Flowers Email-Integration:**
- **E-Mail-Parsing:** Strukturierte Daten aus E-Mails extrahieren
- **Auto-Vehicle-Creation:** Fahrzeuge automatisch anlegen wenn Stammdaten vorhanden
- **Unified Processing:** Gleiche Verarbeitung wie Zapier-Daten

## Deployment & Testing

### **Development:**
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

### **Production (Google Cloud Run):**
```bash
gcloud run deploy ra-autohaus-tracker \
  --source . \
  --region europe-west3 \
  --allow-unauthenticated
```

### **Test-Suite:** 
- **Unit Tests:** Für jeden Service  
- **Integration Tests:** Für API-Endpunkte
- **Schema Tests:** BigQuery-Operationen
- **Mock-Support:** Für offline-Entwicklung

## Projektstruktur

```
ra-autohaus-tracker/
├── src/
│   ├── __init__.py
│   ├── main.py                     # FastAPI App mit Lifecycle
│   ├── core/
│   │   ├── __init__.py
│   │   └── dependencies.py         # Service Injection mit @lru_cache
│   ├── services/
│   │   ├── __init__.py
│   │   ├── bigquery_service.py     # Data Layer (zentral)
│   │   ├── vehicle_service.py      # Business Layer
│   │   ├── process_service.py      # Integration Layer  
│   │   ├── dashboard_service.py    # Analytics Layer
│   │   └── info_service.py         # Configuration Layer
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── vehicles.py         # Fahrzeug-Endpunkte
│   │       ├── dashboard.py        # Dashboard-Endpunkte
│   │       ├── integration.py      # Webhook-Endpunkte
│   │       └── info.py             # System-Info-Endpunkte
│   ├── models/
│   │   ├── __init__.py
│   │   └── integration.py          # Pydantic Models
│   └── handlers/
│       ├── __init__.py
│       └── flowers_handler.py      # E-Mail-Verarbeitung
├── tests/
├── requirements.txt
├── .env
└── README.md
```

## Erfolgs-Kriterien

**Das System ist erfolgreich wenn:**

1. **Keine IDE-Fehler:** Pylance zeigt 0 Probleme
2. **Alle Tests grün:** Unit + Integration Tests
3. **Schema-Konsistenz:** BigQuery-Operationen ohne "Unrecognized name" Fehler
4. **Integration funktioniert:** Zapier und Flowers speichern Daten korrekt in BigQuery
5. **Dashboard zeigt echte Daten:** KPIs aus BigQuery statt Mock-Daten
6. **Production-Deployment:** Google Cloud Run läuft stabil

**Starte die Entwicklung mit einem minimalen MVP:** Nur BigQueryService + VehicleService + ein einfacher Dashboard-Endpunkt. Erweitere schrittweise um weitere Services.

**Verwende Test-Driven Development:** Schreibe Tests für jeden Service bevor die Implementierung erfolgt.

**Deployment-Strategie:** Lokale Entwicklung zuerst, dann Cloud Run Deployment mit CI/CD über GitHub Actions.

---

Entwickle das System vollständig neu mit diesem Prompt als Grundlage. Beginne mit der BigQuery-Tabellen-Erstellung und dem minimalen Service-Setup.