"""
Pydantic Models für RA Autohaus Tracker
Reinhardt Automobile GmbH - Maximilian Reinhardt

Type-Safe Data Models für API-Validierung und Business Logic.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, validator, ConfigDict

# Enums für konstante Werte
class ProzessTyp(str, Enum):
    """Verfügbare Prozesstypen."""
    EINKAUF = "Einkauf"
    ANLIEFERUNG = "Anlieferung"
    AUFBEREITUNG = "Aufbereitung"
    FOTO = "Foto"
    WERKSTATT = "Werkstatt"
    VERKAUF = "Verkauf"

class Antriebsart(str, Enum):
    """Fahrzeug-Antriebsarten."""
    BENZIN = "Benzin"
    DIESEL = "Diesel"
    ELEKTRO = "Elektro"
    HYBRID = "Hybrid"
    PLUGIN_HYBRID = "Plugin-Hybrid"
    ERDGAS = "Erdgas"
    AUTOGAS = "Autogas"

class Besteuerungsart(str, Enum):
    """Besteuerungsarten für Fahrzeuge."""
    REGEL = "Regel"
    DIFFERENZ = "Differenz"
    EXPORT = "Export"

class Bereifungsart(str, Enum):
    """Bereifungsarten."""
    SOMMER = "Sommer"
    WINTER = "Winter"
    GANZJAHR = "Ganzjahr"

class Datenquelle(str, Enum):
    """Datenquellen für Integration-Tracking."""
    API = "api"
    ZAPIER = "zapier"
    EMAIL = "email"
    FLOWERS = "flowers"
    AUDARIS = "audaris"
    MANUAL = "manual"

# Base Models
class BaseTimestampModel(BaseModel):
    """Base Model mit Zeitstempel-Feldern."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True
    )

# Fahrzeug Models
class FahrzeugStammCreate(BaseModel):
    """Model für Fahrzeugstammdaten-Erstellung."""
    fin: str = Field(..., min_length=17, max_length=17, description="Fahrzeugidentifizierungsnummer (17-stellig)")
    marke: Optional[str] = Field(None, max_length=100, description="Fahrzeughersteller")
    modell: Optional[str] = Field(None, max_length=100, description="Fahrzeugmodell")
    antriebsart: Optional[Antriebsart] = Field(None, description="Antriebsart des Fahrzeugs")
    farbe: Optional[str] = Field(None, max_length=50, description="Fahrzeugfarbe")
    baujahr: Optional[int] = Field(None, ge=1900, le=2030, description="Baujahr")
    datum_erstzulassung: Optional[date] = Field(None, description="Datum der Erstzulassung")
    kw_leistung: Optional[int] = Field(None, gt=0, description="Motorleistung in kW")
    km_stand: Optional[int] = Field(None, ge=0, description="Kilometerstand")
    anzahl_fahrzeugschluessel: Optional[int] = Field(None, ge=0, le=10, description="Anzahl Fahrzeugschlüssel")
    bereifungsart: Optional[Bereifungsart] = Field(None, description="Art der Bereifung")
    anzahl_vorhalter: Optional[int] = Field(None, ge=0, description="Anzahl Vorbesitzer")
    ek_netto: Optional[Decimal] = Field(None, ge=0, description="Einkaufspreis netto in EUR")
    besteuerungsart: Optional[Besteuerungsart] = Field(None, description="Art der Besteuerung")
    erstellt_aus_email: Optional[bool] = Field(False, description="Wurde aus E-Mail erstellt")
    datenquelle_fahrzeug: Optional[Datenquelle] = Field(Datenquelle.API, description="Quelle der Fahrzeugdaten")
    
    @validator('fin')
    def validate_fin(cls, v):
        """Validiert FIN-Format (vereinfacht)."""
        if not v.replace('-', '').replace(' ', '').isalnum():
            raise ValueError('FIN muss alphanumerisch sein')
        return v.upper().replace('-', '').replace(' ', '')
    
    @validator('baujahr')
    def validate_baujahr(cls, v, values):
        """Validiert Baujahr gegen Erstzulassung."""
        if v and 'datum_erstzulassung' in values and values['datum_erstzulassung']:
            if v > values['datum_erstzulassung'].year:
                raise ValueError('Baujahr kann nicht nach Erstzulassung liegen')
        return v

class FahrzeugStammResponse(FahrzeugStammCreate, BaseTimestampModel):
    """Model für Fahrzeugstammdaten-Response."""
    ersterfassung_datum: Optional[datetime] = None
    aktiv: bool = True

# Prozess Models
class FahrzeugProzessCreate(BaseModel):
    """Model für Fahrzeugprozess-Erstellung."""
    prozess_id: str = Field(..., min_length=1, max_length=100, description="Eindeutige Prozess-ID")
    fin: str = Field(..., min_length=17, max_length=17, description="Fahrzeug-FIN")
    prozess_typ: ProzessTyp = Field(..., description="Art des Prozesses")
    status: str = Field(..., min_length=1, max_length=100, description="Aktueller Status")
    bearbeiter: Optional[str] = Field(None, max_length=100, description="Zuständiger Bearbeiter")
    prioritaet: Optional[int] = Field(5, ge=1, le=10, description="Priorität (1=höchste, 10=niedrigste)")
    anlieferung_datum: Optional[date] = Field(None, description="Datum der Fahrzeug-Anlieferung")
    start_timestamp: Optional[datetime] = Field(None, description="Prozess-Startzeit")
    ende_timestamp: Optional[datetime] = Field(None, description="Prozess-Endzeit")
    sla_tage: Optional[int] = Field(None, gt=0, description="SLA-Vorgabe in Tagen")
    datenquelle: Optional[Datenquelle] = Field(Datenquelle.API, description="Quelle der Prozessdaten")
    notizen: Optional[str] = Field(None, max_length=1000, description="Prozess-Notizen")
    zusatz_daten: Optional[Dict[str, Any]] = Field(None, description="Zusätzliche strukturierte Daten")
    
    @validator('ende_timestamp')
    def validate_timestamps(cls, v, values):
        """Validiert dass Ende-Zeit nach Start-Zeit liegt."""
        if v and 'start_timestamp' in values and values['start_timestamp']:
            if v <= values['start_timestamp']:
                raise ValueError('Ende-Zeit muss nach Start-Zeit liegen')
        return v

class FahrzeugProzessResponse(FahrzeugProzessCreate, BaseTimestampModel):
    """Model für Fahrzeugprozess-Response."""
    dauer_minuten: Optional[int] = None
    standzeit_tage: Optional[int] = None
    sla_deadline_datum: Optional[date] = None
    tage_bis_sla_deadline: Optional[int] = None
    erstellt_am: Optional[datetime] = None
    aktualisiert_am: Optional[datetime] = None

# Combined Models
class FahrzeugMitProzess(BaseModel):
    """Model für Fahrzeug mit aktuellem Prozess."""
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

# Dashboard Models
class KPIData(BaseModel):
    """Model für Dashboard-KPIs."""
    name: str
    value: Union[int, float, str]
    unit: Optional[str] = None
    trend: Optional[str] = None  # up, down, stable
    comparison: Optional[str] = None  # vs. last period

# Response Models
class StandardResponse(BaseModel):
    """Standard API Response Model."""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Error Models
class ValidationError(BaseModel):
    """Model für Validierungsfehler."""
    field: str
    error: str
    value: Optional[Any] = None