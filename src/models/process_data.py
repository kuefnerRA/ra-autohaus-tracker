# src/models/process_data.py
from datetime import datetime, date
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# Fahrzeug-Modelle
class VehicleBase(BaseModel):
    """Basis-Fahrzeugmodell"""
    fin: str = Field(..., min_length=17, max_length=17)
    marke: Optional[str] = None
    modell: Optional[str] = None
    antriebsart: Optional[str] = None
    farbe: Optional[str] = None
    baujahr: Optional[int] = None
    datum_erstzulassung: Optional[date] = None
    kw_leistung: Optional[int] = None
    km_stand: Optional[int] = None
    anzahl_fahrzeugschluessel: Optional[int] = None
    bereifungsart: Optional[str] = None
    anzahl_vorhalter: Optional[int] = None
    ek_netto: Optional[float] = None
    besteuerungsart: Optional[str] = None

class VehicleCreate(VehicleBase):
    """Fahrzeug erstellen"""
    pass

class VehicleUpdate(BaseModel):
    """Fahrzeug aktualisieren - alle Felder optional"""
    marke: Optional[str] = None
    modell: Optional[str] = None
    antriebsart: Optional[str] = None
    farbe: Optional[str] = None
    baujahr: Optional[int] = None
    datum_erstzulassung: Optional[date] = None
    kw_leistung: Optional[int] = None
    km_stand: Optional[int] = None
    anzahl_fahrzeugschluessel: Optional[int] = None
    bereifungsart: Optional[str] = None
    anzahl_vorhalter: Optional[int] = None
    ek_netto: Optional[float] = None
    besteuerungsart: Optional[str] = None

class VehicleResponse(VehicleBase):
    """Fahrzeug-Antwort mit zusätzlichen Feldern"""
    id: str
    erstellt_am: datetime
    aktualisiert_am: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Prozess-Modelle
class ProcessBase(BaseModel):
    """Basis-Prozessmodell"""
    fin: str = Field(..., min_length=17, max_length=17)
    prozess_typ: str
    status: str
    bearbeiter: Optional[str] = None
    prioritaet: int = Field(5, ge=1, le=10)
    notizen: Optional[str] = None

class ProcessCreate(ProcessBase):
    """Prozess erstellen"""
    pass

class ProcessUpdate(BaseModel):
    """Prozess aktualisieren"""
    status: Optional[str] = None
    bearbeiter: Optional[str] = None
    prioritaet: Optional[int] = Field(None, ge=1, le=10)
    notizen: Optional[str] = None

class ProcessStatusUpdate(BaseModel):
    """Nur Status aktualisieren"""
    status: str
    bearbeiter: Optional[str] = None
    notizen: Optional[str] = None

class ProcessResponse(ProcessBase):
    """Prozess-Antwort mit zusätzlichen Feldern"""
    id: str
    process_id: str
    erstellt_am: datetime
    aktualisiert_am: Optional[datetime] = None
    sla_status: Optional[str] = None
    dauer_minuten: Optional[int] = None
    
    class Config:
        from_attributes = True

# Status-Enums für Validierung
PROZESS_TYPEN = [
    "Einkauf",
    "Anlieferung", 
    "Aufbereitung",
    "Foto",
    "Werkstatt",
    "Verkauf"
]

PROZESS_STATUS = [
    "wartend",
    "gestartet",
    "in_bearbeitung",
    "pausiert",
    "abgeschlossen",
    "abgebrochen"
]

# SLA-Referenz
SLA_ZEITEN = {
    "Einkauf": 480,      # 8 Stunden
    "Anlieferung": 1440, # 24 Stunden  
    "Aufbereitung": 2880, # 48 Stunden
    "Foto": 240,         # 4 Stunden
    "Werkstatt": 4320,   # 72 Stunden
    "Verkauf": 1440      # 24 Stunden
}