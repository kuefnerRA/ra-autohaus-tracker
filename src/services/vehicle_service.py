"""
Vehicle Service - Business Logic Layer
Reinhardt Automobile GmbH - RA Autohaus Tracker

Geschäftslogik für Fahrzeugverwaltung mit SLA-Berechnung und Prioritäts-Management.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid

import structlog
from src.services.bigquery_service import BigQueryService
from src.models.integration import (
    FahrzeugStammCreate, FahrzeugStammResponse,
    FahrzeugProzessCreate, FahrzeugProzessResponse,
    FahrzeugMitProzess, ProzessTyp, KPIData, ValidationError
)

# Strukturiertes Logging
logger = structlog.get_logger(__name__)

class VehicleService:
    """
    Geschäftslogik für Fahrzeugverwaltung.
    
    Verantwortlichkeiten:
    - Fahrzeug-CRUD mit Geschäftsregeln
    - SLA-Berechnung und Überwachung
    - Prioritäts-Management
    - Fahrzeug-Status-Tracking
    - KPI-Berechnung für Fahrzeuge
    """
    
    # Prozess-Konfiguration (SLA und Prioritäten)
    PROZESS_CONFIG = {
        ProzessTyp.EINKAUF: {"sla_stunden": 48, "priority_range": [1, 3]},
        ProzessTyp.ANLIEFERUNG: {"sla_stunden": 24, "priority_range": [2, 4]},
        ProzessTyp.AUFBEREITUNG: {"sla_stunden": 72, "priority_range": [3, 5]},
        ProzessTyp.FOTO: {"sla_stunden": 24, "priority_range": [4, 6]},
        ProzessTyp.WERKSTATT: {"sla_stunden": 168, "priority_range": [2, 5]},
        ProzessTyp.VERKAUF: {"sla_stunden": 720, "priority_range": [1, 3]}
    }
    
    # Bearbeiter-Mapping für Normalisierung
    BEARBEITER_MAPPING = {
        "Thomas K.": "Thomas Küfner",
        "Max R.": "Maximilian Reinhardt",
        "T. Küfner": "Thomas Küfner",
        "M. Reinhardt": "Maximilian Reinhardt",
    }
    
    def __init__(self, bigquery_service: BigQueryService):
        """
        Initialisiert VehicleService.
        
        Args:
            bigquery_service: Injected BigQuery Service
        """
        self.bigquery_service = bigquery_service
        self.logger = logger.bind(service="VehicleService")
    
    async def get_vehicles(
        self,
        limit: int = 100,
        prozess_typ: Optional[str] = None,
        bearbeiter: Optional[str] = None,
        sla_critical_only: bool = False
    ) -> List[FahrzeugMitProzess]:
        """
        Holt Fahrzeuge mit erweiterten Filteroptionen.
        """
        try:
            # Bearbeiter-Name normalisieren
            normalized_bearbeiter = self._normalize_bearbeiter_name(bearbeiter) if bearbeiter else None
            
            # Daten aus BigQuery abrufen
            fahrzeuge_raw = await self.bigquery_service.get_fahrzeuge_mit_prozessen(
                limit=limit,
                prozess_typ=prozess_typ,
                bearbeiter=normalized_bearbeiter
            )
            
            # Business Logic anwenden
            fahrzeuge = []
            for fahrzeug_raw in fahrzeuge_raw:
                fahrzeug = await self._enrich_vehicle_data(fahrzeug_raw)
                
                # SLA-Filter anwenden
                if sla_critical_only and not self._is_sla_critical(fahrzeug):
                    continue
                
                fahrzeuge.append(fahrzeug)
            
            self.logger.info("✅ Fahrzeuge erfolgreich abgerufen", 
                           count=len(fahrzeuge),
                           prozess_typ=prozess_typ,
                           bearbeiter=bearbeiter,
                           sla_critical=sla_critical_only)
            
            return fahrzeuge
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Abrufen der Fahrzeuge", error=str(e))
            raise
    
    async def get_vehicle_details(self, fin: str) -> Optional[FahrzeugMitProzess]:
        """
        Holt detaillierte Fahrzeugdaten für eine spezifische FIN.
        """
        try:
            # Validierung
            if not self._validate_fin(fin):
                raise ValueError(f"Ungültige FIN: {fin}")
            
            # Fahrzeug abrufen
            fahrzeuge = await self.bigquery_service.get_fahrzeuge_mit_prozessen(limit=1000)
            
            # Spezifische FIN filtern
            fahrzeug_raw = next((f for f in fahrzeuge if f.get('fin') == fin), None)
            
            if not fahrzeug_raw:
                self.logger.info("ℹ️ Fahrzeug nicht gefunden", fin=fin)
                return None
            
            # Anreicherung mit Business Logic
            fahrzeug = await self._enrich_vehicle_data(fahrzeug_raw)
            
            self.logger.info("✅ Fahrzeugdetails erfolgreich abgerufen", fin=fin)
            return fahrzeug
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Abrufen der Fahrzeugdetails", 
                            error=str(e), fin=fin)
            raise
    
    async def create_complete_vehicle(
        self,
        fahrzeug_data: FahrzeugStammCreate,
        prozess_data: Optional[FahrzeugProzessCreate] = None
    ) -> FahrzeugMitProzess:
        """
        Erstellt ein vollständiges Fahrzeug mit Stammdaten und optionalem Prozess.
        """
        try:
            # Validierung
            validation_errors = await self._validate_vehicle_data(fahrzeug_data)
            if validation_errors:
                raise ValueError(f"Validierungsfehler: {[e.error for e in validation_errors]}")
            
            # Fahrzeugstammdaten erstellen
            fahrzeug_dict = fahrzeug_data.model_dump(exclude_none=True)
            await self.bigquery_service.create_fahrzeug_stamm(fahrzeug_dict)
            
            # Optional: Prozess erstellen
            if prozess_data:
                # Prozess-ID generieren falls nicht vorhanden
                if not prozess_data.prozess_id:
                    prozess_data.prozess_id = self._generate_process_id(
                        fahrzeug_data.fin, 
                        prozess_data.prozess_typ
                    )
                
                # SLA-Berechnung
                prozess_dict = prozess_data.model_dump(exclude_none=True)
                prozess_dict = await self._calculate_sla_data(prozess_dict)
                
                await self.bigquery_service.create_fahrzeug_prozess(prozess_dict)
            
            # Vollständiges Fahrzeug zurückgeben
            created_vehicle = await self.get_vehicle_details(fahrzeug_data.fin)
            if not created_vehicle:
                raise RuntimeError("Fahrzeug konnte nach Erstellung nicht abgerufen werden")
            
            self.logger.info("✅ Fahrzeug vollständig erstellt", 
                           fin=fahrzeug_data.fin,
                           mit_prozess=prozess_data is not None)
            
            return created_vehicle
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Erstellen des Fahrzeugs", 
                            error=str(e), 
                            fin=fahrzeug_data.fin)
            raise
    
    async def update_vehicle_status(
        self,
        fin: str,
        new_status: str,
        bearbeiter: Optional[str] = None,
        notizen: Optional[str] = None
    ) -> bool:
        """
        Aktualisiert den Status eines Fahrzeugprozesses.
        """
        try:
            # Aktuelles Fahrzeug abrufen
            current_vehicle = await self.get_vehicle_details(fin)
            if not current_vehicle or not current_vehicle.prozess_id:
                raise ValueError(f"Kein aktiver Prozess für FIN {fin} gefunden")
            
            # Update-Daten vorbereiten
            if not current_vehicle.prozess_typ:
                raise ValueError(f"Fahrzeug {fin} hat keinen Prozesstyp")
            update_data = {
                'prozess_id': self._generate_process_id(fin, current_vehicle.prozess_typ, suffix="update"),
                'fin': fin,
                'prozess_typ': current_vehicle.prozess_typ,
                'status': new_status,
                'bearbeiter': self._normalize_bearbeiter_name(bearbeiter) if bearbeiter else current_vehicle.bearbeiter,
                'prioritaet': current_vehicle.prioritaet
            }
            
            if notizen:
                update_data['notizen'] = notizen
            
            # SLA-Daten neu berechnen
            update_data = await self._calculate_sla_data(update_data)
            
            await self.bigquery_service.create_fahrzeug_prozess(update_data)
            
            self.logger.info("✅ Fahrzeugstatus erfolgreich aktualisiert", 
                           fin=fin,
                           new_status=new_status,
                           bearbeiter=bearbeiter)
            
            return True
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Aktualisieren des Fahrzeugstatus", 
                            error=str(e), 
                            fin=fin)
            raise
    
    async def get_vehicle_kpis(self) -> List[KPIData]:
        """
        Berechnet Fahrzeug-bezogene KPIs.
        """
        try:
            # Alle Fahrzeuge abrufen
            all_vehicles = await self.get_vehicles(limit=1000)
            
            kpis = []
            
            # Gesamt-Fahrzeuganzahl
            kpis.append(KPIData(
                name="Gesamtfahrzeuge",
                value=len(all_vehicles),
                unit="Stück"
            ))
            
            # Fahrzeuge nach Prozesstyp
            prozess_counts = {}
            sla_critical_count = 0
            
            for vehicle in all_vehicles:
                if vehicle.prozess_typ:
                    prozess_counts[vehicle.prozess_typ] = prozess_counts.get(vehicle.prozess_typ, 0) + 1
                
                if self._is_sla_critical(vehicle):
                    sla_critical_count += 1
            
            # KPIs für jeden Prozesstyp
            for prozess_typ, count in prozess_counts.items():
                kpis.append(KPIData(
                    name=f"{prozess_typ} Fahrzeuge",
                    value=count,
                    unit="Stück"
                ))
            
            # SLA-kritische Fahrzeuge
            kpis.append(KPIData(
                name="SLA-kritische Fahrzeuge",
                value=sla_critical_count,
                unit="Stück",
                trend="up" if sla_critical_count > 0 else "stable"
            ))
            
            # Durchschnittlicher Einkaufspreis
            ek_prices = [v.ek_netto for v in all_vehicles if v.ek_netto]
            if ek_prices:
                avg_ek = sum(ek_prices) / len(ek_prices)
                kpis.append(KPIData(
                    name="Ø Einkaufspreis",
                    value=round(float(avg_ek), 2),
                    unit="EUR"
                ))
            
            self.logger.info("✅ Fahrzeug-KPIs erfolgreich berechnet", kpi_count=len(kpis))
            return kpis
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Berechnen der Fahrzeug-KPIs", error=str(e))
            return []
    
    # Private Helper Methods
    
    async def _enrich_vehicle_data(self, fahrzeug_raw: Dict[str, Any]) -> FahrzeugMitProzess:
        """Reichert Fahrzeugdaten mit Business Logic an."""
        # SLA-Berechnung
        if fahrzeug_raw.get('prozess_typ') and fahrzeug_raw.get('aktualisiert_am'):
            fahrzeug_raw = await self._calculate_sla_data(fahrzeug_raw)
        
        # Standzeit berechnen
        if fahrzeug_raw.get('aktualisiert_am'):
            if isinstance(fahrzeug_raw['aktualisiert_am'], str):
                aktualisiert_am = datetime.fromisoformat(fahrzeug_raw['aktualisiert_am'].replace('Z', '+00:00'))
            else:
                aktualisiert_am = fahrzeug_raw['aktualisiert_am']
            
            standzeit = (datetime.now() - aktualisiert_am.replace(tzinfo=None)).days
            fahrzeug_raw['standzeit_tage'] = standzeit
        
        return FahrzeugMitProzess(**fahrzeug_raw)
    
    async def _calculate_sla_data(self, prozess_data: Dict[str, Any]) -> Dict[str, Any]:
        """Berechnet SLA-relevante Felder."""
        prozess_typ = prozess_data.get('prozess_typ')
        
        if not prozess_typ:
            return prozess_data
            
        # String zu Enum konvertieren falls nötig
        if isinstance(prozess_typ, str):
            try:
                prozess_typ_enum = ProzessTyp(prozess_typ)
            except ValueError:
                return prozess_data
        else:
            prozess_typ_enum = prozess_typ
        
        if prozess_typ_enum not in self.PROZESS_CONFIG:
            return prozess_data
        
        config = self.PROZESS_CONFIG[prozess_typ_enum]
        sla_stunden = config['sla_stunden']
        
        # SLA-Deadline berechnen
        start_time = prozess_data.get('start_timestamp') or prozess_data.get('erstellt_am') or datetime.now()
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        sla_deadline = start_time + timedelta(hours=sla_stunden)
        prozess_data['sla_deadline_datum'] = sla_deadline.date()
        
        # Tage bis Deadline
        tage_bis_deadline = (sla_deadline.date() - date.today()).days
        prozess_data['tage_bis_sla_deadline'] = tage_bis_deadline
        
        # SLA-Tage setzen
        prozess_data['sla_tage'] = max(1, sla_stunden // 24)
        
        return prozess_data
    
    def _normalize_bearbeiter_name(self, bearbeiter: Optional[str]) -> Optional[str]:
        """Normalisiert Bearbeiternamen."""
        if not bearbeiter:
            return None
        
        # Exakte Übereinstimmung prüfen
        if bearbeiter in self.BEARBEITER_MAPPING:
            return self.BEARBEITER_MAPPING[bearbeiter]
        
        # Fallback: Original-Name zurückgeben
        return bearbeiter.strip()
    
    def _validate_fin(self, fin: str) -> bool:
        """Validiert FIN-Format (vereinfacht)."""
        if not fin or len(fin) != 17:
            return False
        
        # Basis-Validierung: alphanumerisch
        return fin.replace('-', '').replace(' ', '').isalnum()
    
    async def _validate_vehicle_data(self, fahrzeug_data: FahrzeugStammCreate) -> List[ValidationError]:
        """Validiert Fahrzeugdaten gegen Geschäftsregeln."""
        errors = []
        
        # FIN-Duplikat prüfen
        existing = await self.bigquery_service.get_fahrzeug_by_fin(fahrzeug_data.fin)
        if existing:
            errors.append(ValidationError(
                field="fin",
                error="FIN bereits vorhanden",
                value=fahrzeug_data.fin
            ))
        
        # Baujahr-Plausibilität
        if fahrzeug_data.baujahr and fahrzeug_data.baujahr > date.today().year + 1:
            errors.append(ValidationError(
                field="baujahr",
                error="Baujahr liegt in der Zukunft",
                value=fahrzeug_data.baujahr
            ))
        
        # Einkaufspreis-Plausibilität
        if fahrzeug_data.ek_netto and fahrzeug_data.ek_netto > 500000:
            errors.append(ValidationError(
                field="ek_netto",
                error="Einkaufspreis erscheint unrealistisch hoch",
                value=fahrzeug_data.ek_netto
            ))
        
        return errors
    
    def _generate_process_id(self, fin: str, prozess_typ: str, suffix: Optional[str] = None) -> str:
        """Generiert eine eindeutige Prozess-ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prozess_short = str(prozess_typ)[:3].upper()
        fin_short = fin[-6:] if len(fin) >= 6 else fin
        
        process_id = f"{prozess_short}_{fin_short}_{timestamp}"
        
        if suffix:
            process_id += f"_{suffix}"
        
        return process_id
    
    def _is_sla_critical(self, fahrzeug: FahrzeugMitProzess) -> bool:
        """Prüft ob ein Fahrzeug SLA-kritisch ist."""
        if not fahrzeug.tage_bis_sla_deadline:
            return False
        
        return fahrzeug.tage_bis_sla_deadline <= 1
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Gesundheitscheck für VehicleService.
        """
        try:
            # BigQuery-Service testen
            bigquery_health = await self.bigquery_service.health_check()
            
            # Basis-Funktionalität testen
            test_vehicles = await self.get_vehicles(limit=1)
            
            return {
                'status': 'healthy',
                'bigquery': bigquery_health['status'],
                'test_query': 'successful',
                'vehicle_count': len(test_vehicles)
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
