# Datenmodelle - RA Autohaus Tracker

**Reinhardt Automobile GmbH**  
**Version:** 1.0.0-alpha  
**Letzte Aktualisierung:** 03.09.2025

## Überblick

Das RA Autohaus Tracker System verwendet **Pydantic Models** für Type-Safety und Validierung sowie **BigQuery-Tabellen** für persistente Datenspeicherung. Die Datenmodelle folgen dem **Domain-Driven Design** mit klaren Abgrenzungen zwischen Fahrzeugstammdaten und Prozessdaten.

## BigQuery-Schema

### Tabelle: `fahrzeuge_stamm`

**Zweck:** Normalisierte Fahrzeugstammdaten (eine Zeile pro FIN)

```sql
CREATE TABLE `ra-autohaus-tracker.autohaus.fahrzeuge_stamm` (
  -- Identifikation
  fin STRING NOT NULL,  -- Fahrzeugidentifizierungsnummer (Primary Key)
  
  -- Fahrzeugdaten
  marke STRING,                    -- Fahrzeughersteller
  modell STRING,                   -- Fahrzeugmodell
  antriebsart STRING,             -- Benzin, Diesel, Elektro, Hybrid
  farbe STRING,                   -- Fahrzeugfarbe
  baujahr INTEGER,                -- Baujahr
  datum_erstzulassung DATE,       -- Erstzulassungsdatum
  kw_leistung INTEGER,            -- Motorleistung in kW
  km_stand INTEGER,               -- Kilometerstand
  
  -- Ausstattung & Zustand
  anzahl_fahrzeugschluessel INTEGER,  -- Anzahl Schlüssel
  bereifungsart STRING,               -- Sommer/Winter/Ganzjahr
  anzahl_vorhalter INTEGER,           -- Vorbesitzer
  
  -- Kaufmännische Daten
  ek_netto NUMERIC(10,2),         -- Einkaufspreis netto
  besteuerungsart STRING,         -- Regel/Differenz/Export
  
  -- Metadaten
  ersterfassung_datum DATETIME,   -- Erste Erfassung
  aktiv BOOLEAN DEFAULT TRUE,     -- Fahrzeug aktiv
  erstellt_aus_email BOOLEAN,     -- Aus E-Mail erstellt
  datenquelle_fahrzeug STRING,    -- Datenquelle
  created_at TIMESTAMP,           -- Erstellungszeitpunkt
  updated_at TIMESTAMP            -- Letztes Update
)
PARTITION BY DATE(created_at)
CLUSTER BY fin, marke;
```

### Tabelle: `fahrzeug_prozesse`

**Zweck:** Prozess-Historie und Status-Tracking (mehrere Zeilen pro FIN)

```sql
CREATE TABLE `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` (
  -- Identifikation
  prozess_id STRING NOT NULL,     -- Eindeutige Prozess-ID
  fin STRING NOT NULL,            -- Fahrzeug-Referenz
  
  -- Prozess-Information
  prozess_typ STRING NOT NULL,    -- Einkauf, Aufbereitung, Foto, etc.
  status STRING NOT NULL,         -- Aktueller Status
  bearbeiter STRING,              -- Zuständige Person
  prioritaet INTEGER DEFAULT 5,   -- 1=hoch, 10=niedrig
  
  -- Zeiterfassung
  anlieferung_datum DATE,         -- Fahrzeug-Anlieferung
  start_timestamp DATETIME,       -- Prozess-Start
  ende_timestamp DATETIME,        -- Prozess-Ende
  dauer_minuten INTEGER,          -- Berechnete Dauer
  standzeit_tage INTEGER,         -- Standzeit seit letztem Update
  
  -- SLA-Management
  sla_tage INTEGER,              -- SLA-Vorgabe
  sla_deadline_datum DATE,       -- SLA-Deadline
  tage_bis_sla_deadline INTEGER, -- Verbleibende Tage
  
  -- Integration & Zusatzdaten
  datenquelle STRING,            -- api/zapier/email/flowers
  notizen STRING,                -- Prozess-Notizen
  zusatz_daten STRING,           -- JSON-Daten
  
  -- Audit-Felder
  erstellt_am DATETIME,          -- Erstellungszeitpunkt
  aktualisiert_am DATETIME,      -- Letztes Update
  created_at TIMESTAMP,          -- System-Timestamp
  updated_at TIMESTAMP           -- System-Update
)
PARTITION BY DATE(created_at)
CLUSTER BY fin, prozess_typ, bearbeiter;
```

## Pydantic Models

### Enums

```python
class ProzessTyp(str, Enum):
    """Verfügbare Prozesstypen nach Geschäftsprozess."""
    EINKAUF = "Einkauf"
    ANLIEFERUNG = "Anlieferung"
    AUFBEREITUNG = "Aufbereitung"
    FOTO = "Foto"
    WERKSTATT = "Werkstatt"
    VERKAUF = "Verkauf"

class Antriebsart(str, Enum):
    """Fahrzeug-Antriebsarten nach Marktstandard."""
    BENZIN = "Benzin"
    DIESEL = "Diesel"
    ELEKTRO = "Elektro"
    HYBRID = "Hybrid"
    PLUGIN_HYBRID = "Plugin-Hybrid"
    ERDGAS = "Erdgas"
    AUTOGAS = "Autogas"

class Datenquelle(str, Enum):
    """Datenquellen für Integration-Tracking."""
    API = "api"          # Direkte API-Eingabe
    ZAPIER = "zapier"    # Zapier Webhook
    EMAIL = "email"      # E-Mail Integration
    FLOWERS = "flowers"  # Flowers Workflow System
    AUDARIS = "audaris"  # Audaris Fahrzeugverwaltung
    MANUAL = "manual"    # Manuelle Eingabe
```

### Fahrzeug-Models

#### FahrzeugStammCreate
**Zweck:** Eingabedaten für neue Fahrzeuge

```python
class FahrzeugStammCreate(BaseModel):
    fin: str = Field(..., min_length=17, max_length=17)
    marke: Optional[str] = Field(None, max_length=100)
    modell: Optional[str] = Field(None, max_length=100)
    antriebsart: Optional[Antriebsart] = None
    farbe: Optional[str] = Field(None, max_length=50)
    baujahr: Optional[int] = Field(None, ge=1900, le=2030)
    datum_erstzulassung: Optional[date] = None
    kw_leistung: Optional[int] = Field(None, gt=0)
    km_stand: Optional[int] = Field(None, ge=0)
    anzahl_fahrzeugschluessel: Optional[int] = Field(None, ge=0, le=10)
    bereifungsart: Optional[Bereifungsart] = None
    anzahl_vorhalter: Optional[int] = Field(None, ge=0)
    ek_netto: Optional[Decimal] = Field(None, ge=0)
    besteuerungsart: Optional[Besteuerungsart] = None
    
    @validator('fin')
    def validate_fin(cls, v):
        """FIN-Format validieren."""
        return v.upper().replace('-', '').replace(' ', '')
```

#### FahrzeugProzessCreate
**Zweck:** Eingabedaten für neue Prozesse

```python
class FahrzeugProzessCreate(BaseModel):
    prozess_id: str = Field(..., min_length=1, max_length=100)
    fin: str = Field(..., min_length=17, max_length=17)
    prozess_typ: ProzessTyp
    status: str = Field(..., min_length=1, max_length=100)
    bearbeiter: Optional[str] = Field(None, max_length=100)
    prioritaet: Optional[int] = Field(5, ge=1, le=10)
    start_timestamp: Optional[datetime] = None
    ende_timestamp: Optional[datetime] = None
    sla_tage: Optional[int] = Field(None, gt=0)
    notizen: Optional[str] = Field(None, max_length=1000)
    zusatz_daten: Optional[Dict[str, Any]] = None
```

#### FahrzeugMitProzess
**Zweck:** Kombinierte Fahrzeug- und Prozessdaten für API-Responses

```python
class FahrzeugMitProzess(BaseModel):
    """Denormalisiertes Model für effiziente API-Responses."""
    
    # Fahrzeug-Stammdaten
    fin: str
    marke: Optional[str] = None
    modell: Optional[str] = None
    antriebsart: Optional[str] = None
    farbe: Optional[str] = None
    baujahr: Optional[int] = None
    ek_netto: Optional[Decimal] = None
    
    # Prozess-Daten (aktueller Prozess)
    prozess_id: Optional[str] = None
    prozess_typ: Optional[str] = None
    status: Optional[str] = None
    bearbeiter: Optional[str] = None
    prioritaet: Optional[int] = None
    sla_deadline_datum: Optional[date] = None
    tage_bis_sla_deadline: Optional[int] = None
    standzeit_tage: Optional[int] = None
    prozess_aktualisiert_am: Optional[datetime] = None
```

## Datenbeziehungen

### 1:N Beziehung - Fahrzeug zu Prozessen
```
fahrzeuge_stamm (1) ←→ (N) fahrzeug_prozesse
    fin                     fin (Foreign Key)
```

**Geschäftsregel:** Ein Fahrzeug kann mehrere Prozesse durchlaufen (Historie), aber nur einen aktiven Prozess haben.

### Aktiver Prozess Ermittlung
```sql
-- Aktuellster Prozess pro Fahrzeug
SELECT *,
  ROW_NUMBER() OVER (
    PARTITION BY fin 
    ORDER BY aktualisiert_am DESC
  ) as rn
FROM fahrzeug_prozesse
WHERE rn = 1
```

## Datenvalidierung

### FIN-Validierung
- **Format:** 17-stellige alphanumerische Zeichenfolge
- **Eindeutigkeit:** Keine Duplikate im System
- **Normalisierung:** Großschreibung, Entfernung von Bindestrichen/Leerzeichen

### Geschäftsregeln
```python
# Baujahr-Plausibilität
if baujahr > datetime.now().year + 1:
    raise ValueError("Baujahr liegt in der Zukunft")

# Erstzulassung nach Baujahr
if datum_erstzulassung and baujahr:
    if datum_erstzulassung.year < baujahr:
        raise ValueError("Erstzulassung vor Baujahr")

# Einkaufspreis-Plausibilität
if ek_netto and ek_netto > 500000:
    raise ValueError("Einkaufspreis unrealistisch hoch")
```

## SLA-Datenmodell

### SLA-Berechnung
```python
sla_deadline = prozess.start_timestamp + timedelta(hours=sla_stunden)
tage_bis_deadline = (sla_deadline.date() - date.today()).days

# Status-Klassifizierung
if tage_bis_deadline < 0:
    status = "überfällig"
elif tage_bis_deadline <= 1:
    status = "kritisch"
elif tage_bis_deadline <= 3:
    status = "warnung"
else:
    status = "ok"
```

### SLA-Konfiguration per Prozesstyp
| Prozesstyp    | SLA (Stunden) | SLA (Tage) | Prioritätsbereich |
|---------------|---------------|------------|------------------|
| Einkauf       | 48            | 2          | 1-3              |
| Anlieferung   | 24            | 1          | 2-4              |
| Aufbereitung  | 72            | 3          | 3-5              |
| Foto          | 24            | 1          | 4-6              |
| Werkstatt     | 168           | 7          | 2-5              |
| Verkauf       | 720           | 30         | 1-3              |

## Integration-Datenmodelle

### Zapier Integration
```python
class ZapierWebhookData(BaseModel):
    """Flexible Datenstruktur für Zapier Webhooks."""
    
    # Alternative Feldnamen für FIN
    fin: Optional[str] = None
    vin: Optional[str] = None
    vehicle_id: Optional[str] = None
    
    # Fahrzeugdaten (deutsch/englisch)
    marke: Optional[str] = None
    make: Optional[str] = None
    modell: Optional[str] = None
    model: Optional[str] = None
    
    # Prozessdaten
    prozess_typ: Optional[str] = None
    process_type: Optional[str] = None
    process: Optional[str] = None  # Mapping erforderlich
    
    # Raw Data für Debugging
    raw_data: Optional[Dict[str, Any]] = None
```

### Prozess-Mapping
```python
# Zapier → Interne Prozesstypen
PROZESS_MAPPING = {
    "gwa": "Aufbereitung",
    "garage": "Werkstatt", 
    "photos": "Foto",
    "sales": "Verkauf",
    "purchase": "Einkauf",
    "delivery": "Anlieferung"
}
```

## Audit & Compliance

### Audit Log Model (Optional)
```python
class AuditLogEntry(BaseModel):
    log_id: str
    tabelle: str                    # fahrzeuge_stamm/fahrzeug_prozesse
    operation: str                  # INSERT/UPDATE/DELETE
    fin: Optional[str] = None
    prozess_id: Optional[str] = None
    alte_werte: Optional[Dict] = None
    neue_werte: Optional[Dict] = None
    benutzer: Optional[str] = None
    quelle: Optional[str] = None    # API Endpoint
    ip_adresse: Optional[str] = None
    zeitstempel: datetime
```

### DSGVO-Compliance
- **Datenminimierung:** Nur geschäftsrelevante Daten
- **Zweckbindung:** Daten nur für Fahrzeugprozess-Tracking
- **Löschkonzept:** Fahrzeuge als "inaktiv" markieren statt löschen
- **Audit-Trail:** Alle Änderungen nachvollziehbar

## Performance-Optimierung

### BigQuery-Optimierungen
```sql
-- Partitionierung nach Datum
PARTITION BY DATE(created_at)

-- Clustering für häufige Filter
CLUSTER BY fin, marke                    -- fahrzeuge_stamm
CLUSTER BY fin, prozess_typ, bearbeiter  -- fahrzeug_prozesse
```

### Query-Patterns
```sql
-- Effizient: Filter auf Clustered Columns
SELECT * FROM fahrzeuge_stamm 
WHERE fin = 'WVWZZZ1JZ8W123456'

-- Effizient: Partition Pruning
SELECT * FROM fahrzeug_prozesse
WHERE DATE(created_at) >= '2025-01-01'
  AND prozess_typ = 'Aufbereitung'

-- Ineffizient: Full Table Scan
SELECT * FROM fahrzeuge_stamm
WHERE farbe = 'Rot'  -- nicht geclustered
```

## Migration & Schema Evolution

### Versionierung
- **Schema-Versionen:** Tracking in Dokumentation
- **Backward Compatibility:** Neue Felder optional
- **Migration Scripts:** SQL-Scripts für Schema-Änderungen

### Geplante Erweiterungen
- **Fahrzeugbilder:** Cloud Storage URLs
- **Dokumente:** PDF-Links für Fahrzeugpapiere
- **GPS-Tracking:** Standortdaten für Fahrzeuglogistik
- **Kosten-Tracking:** Aufbereitung-/Werkstattkosten pro Fahrzeug
