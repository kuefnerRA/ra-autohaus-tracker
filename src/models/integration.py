# src/models/integration.py
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class UnifiedProcessData(BaseModel):
    """Einheitliches Datenformat für alle Integrationen (E-Mail, Zapier, Webhook)"""
    fin: str = Field(..., min_length=17, max_length=17)
    prozess_typ: str  # Einer der 6 Hauptprozesse
    status: str
    bearbeiter: Optional[str] = None
    prioritaet: int = Field(5, ge=1, le=10)
    notizen: Optional[str] = None
    datenquelle: str
    external_timestamp: Optional[datetime] = None
    
    # Fahrzeugdaten (optional - für Auto-Create)
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
    
    zusatz_daten: Optional[Dict[str, Any]] = None


class IntegrationResponse(BaseModel):
    """Standardisierte Antwort für alle Integrationen"""
    success: bool
    message: str
    fin: str
    prozess_typ: str
    status: str
    prozess_id: Optional[str] = None
    vehicle_created: bool = False
    bearbeiter_mapped: Optional[str] = None
    warnings: List[str] = []
    datenquelle: str


class ZapierInput(BaseModel):
    """Rohdaten von Zapier (flexibel)"""
    # Pflichtfelder - flexible Feldnamen
    fin: Optional[str] = None
    fahrzeug_fin: Optional[str] = None
    vehicle_fin: Optional[str] = None
    FIN: Optional[str] = None
    
    prozess_typ: Optional[str] = None
    prozess_name: Optional[str] = None
    prozess: Optional[str] = None
    process_name: Optional[str] = None
    
    status: Optional[str] = None
    neuer_status: Optional[str] = None
    new_status: Optional[str] = None
    
    # Optionale Felder
    bearbeiter: Optional[str] = None
    bearbeiter_name: Optional[str] = None
    notizen: Optional[str] = None
    prioritaet: Optional[int] = 5
    
    # Fahrzeugdaten
    marke: Optional[str] = None
    modell: Optional[str] = None
    antriebsart: Optional[str] = None
    farbe: Optional[str] = None
    baujahr: Optional[int] = None
    datum_erstzulassung: Optional[str] = None
    kw_leistung: Optional[int] = None
    km_stand: Optional[int] = None
    anzahl_fahrzeugschluessel: Optional[int] = None
    bereifungsart: Optional[str] = None
    anzahl_vorhalter: Optional[int] = None
    ek_netto: Optional[float] = None
    besteuerungsart: Optional[str] = None
    
    def get_fin(self) -> Optional[str]:
        """FIN aus verschiedenen möglichen Feldnamen extrahieren"""
        return self.fin or self.fahrzeug_fin or self.vehicle_fin or self.FIN
    
    def get_prozess_typ(self) -> Optional[str]:
        """Prozess-Typ aus verschiedenen Feldnamen extrahieren"""
        return (self.prozess_typ or self.prozess_name or 
                self.prozess or self.process_name)
    
    def get_status(self) -> Optional[str]:
        """Status aus verschiedenen Feldnamen extrahieren"""
        return self.status or self.neuer_status or self.new_status
    
    def get_bearbeiter(self) -> Optional[str]:
        """Bearbeiter aus verschiedenen Feldnamen extrahieren"""
        return self.bearbeiter or self.bearbeiter_name


class EmailInput(BaseModel):
    """Rohdaten aus E-Mail-Parsing"""
    betreff: str
    inhalt: str
    absender: str
    empfangen_am: datetime
    
    # Geparste Daten aus E-Mail-Content
    fin: Optional[str] = None
    prozess_typ: Optional[str] = None
    status: Optional[str] = None
    bearbeiter: Optional[str] = None
    marke: Optional[str] = None
    farbe: Optional[str] = None


class WebhookInput(BaseModel):
    """Rohdaten von direkten Flowers Webhooks"""
    fahrzeug_id: str
    fin: Optional[str] = None
    prozess: str
    status: str
    bearbeiter: Optional[str] = None
    timestamp: Optional[datetime] = None
    zusatz_daten: Optional[Dict[str, Any]] = None