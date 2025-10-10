"""
Vehicle Service - Business Logic Layer
Reinhardt Automobile GmbH - RA Autohaus Tracker

Geschäftslogik für Fahrzeugverwaltung mit SLA-Berechnung und Prioritäts-Management.
"""

import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid
import time
from src.core.logging_config import LoggerMixin

import structlog
from src.services.bigquery_service import BigQueryService
from src.models.integration import (
    FahrzeugStammCreate, FahrzeugProzessCreate,
    FahrzeugProzessResponse, FahrzeugProzessRequest, FahrzeugMitProzess,
    ProzessTyp, KPIData, ValidationError
)
from src.core.process_config import ProcessConfig
from src.core.mappings import CentralMappings

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
        start_time = time.time() 
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
            
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info("⏱️ Performance",
                        operation="get_vehicles", 
                        duration_ms=round(duration_ms, 2),
                        count=len(fahrzeuge))
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
                prozess_dict = prozess_data.model_dump(exclude_none=False)
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
    
    async def update_vehicle(
        self,
        fin: str,
        update_data: Dict[str, Any],
        create_update_process: bool = True
    ) -> Dict[str, Any]:
        """
        Aktualisiert Fahrzeugstammdaten mit Business-Validierung.
        
        Args:
            fin: Fahrzeugidentifizierungsnummer
            update_data: Zu aktualisierende Felder
            create_update_process: Ob ein Update-Prozess erstellt werden soll
            
        Returns:
            Dict mit Update-Ergebnis und Change-Log
        """
        try:
            # FIN-Validierung
            if not self._validate_fin(fin):
                raise ValueError(f"Ungültige FIN: {fin}")
            
            # Fahrzeug muss existieren
            existing = await self.bigquery_service.get_fahrzeug_by_fin(fin)
            if not existing:
                raise ValueError(f"Fahrzeug {fin} nicht gefunden - Update nicht möglich")
            
            # Validierung der Update-Daten
            validation_errors = await self._validate_update_data(fin, update_data)
            if validation_errors:
                raise ValueError(f"Validierungsfehler: {validation_errors}")
            
            # Datentyp-Konvertierungen für Geldbeträge
            money_fields = ['ek_netto', 'vk_netto', 'ek_brutto', 'vk_brutto']
            for field in money_fields:
                if field in update_data and update_data[field] is not None:
                    # Konvertiere zu Decimal für BigQuery NUMERIC
                    update_data[field] = Decimal(str(update_data[field]))
                        
            # Update durchführen
            update_result = await self.bigquery_service.update_fahrzeug_stamm(
                fin=fin,
                update_data=update_data,
                log_changes=True
            )
            
          
            self.logger.info("✅ Fahrzeug erfolgreich aktualisiert", 
                            fin=fin,
                            fields_updated=update_result['fields_updated'])
            
            return update_result
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Fahrzeug-Update", 
                            error=str(e), fin=fin)
            raise

    async def _validate_update_data(
        self, 
        fin: str, 
        update_data: Dict[str, Any]
    ) -> List[str]:
        """
        Validiert Update-Daten gegen Geschäftsregeln.
        
        Returns:
            Liste von Validierungsfehlern (leer wenn alles OK)
        """
        errors = []
        
        # Baujahr-Plausibilität
        if 'baujahr' in update_data:
            current_year = date.today().year
            if update_data['baujahr'] > current_year + 1:
                errors.append(f"Baujahr {update_data['baujahr']} liegt in der Zukunft")
            elif update_data['baujahr'] < 1900:
                errors.append(f"Baujahr {update_data['baujahr']} ist unrealistisch")
        
        # Kilometerstand darf nicht negativ sein
        if 'km_stand' in update_data and update_data['km_stand'] is not None:
            if update_data['km_stand'] < 0:
                errors.append("Kilometerstand kann nicht negativ sein")
        
        # EK-Preis Plausibilität
        if 'ek_netto' in update_data and update_data['ek_netto'] is not None:
            ek_value = float(update_data['ek_netto'])
            if ek_value < 0:
                errors.append("Einkaufspreis kann nicht negativ sein")
            elif ek_value > 1000000:
                errors.append(f"Einkaufspreis {ek_value} EUR erscheint unrealistisch hoch")
        
        # Anzahl Schlüssel Plausibilität
        if 'anzahl_fahrzeugschluessel' in update_data:
            if update_data['anzahl_fahrzeugschluessel'] > 10:
                errors.append("Mehr als 10 Fahrzeugschlüssel sind ungewöhnlich")
        
        return errors

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
    
    async def create_vehicle_process(
        self,
        fin: str,
        prozess_data: FahrzeugProzessCreate
    ) -> FahrzeugProzessResponse:
        """
        Erstellt einen neuen Prozess für ein bestehendes Fahrzeug.
        Beendet automatisch alle noch offenen Prozesse des Fahrzeugs.
        """
        try:
            # DEBUG
            self.logger.info("🔍 DEBUG - prozess_data empfangen", 
                            has_deadline=hasattr(prozess_data, 'individuelle_deadline'),
                            deadline_value=getattr(prozess_data, 'individuelle_deadline', None))

            # Validierung
            if not self._validate_fin(fin):
                raise ValueError(f"Ungültige FIN: {fin}")
            
            # Prüfen ob Fahrzeug existiert
            fahrzeug = await self.bigquery_service.get_fahrzeug_by_fin(fin)
            if not fahrzeug:
                raise ValueError(f"Fahrzeug mit FIN {fin} nicht gefunden")
            
            # Alle offenen Prozesse des Fahrzeugs beenden
            await self._close_open_processes(fin, prozess_data.prozess_typ)
            
            # Rest der bestehenden Logik...
            if not prozess_data.prozess_id:
                prozess_data.prozess_id = self._generate_process_id(
                    fin, 
                    prozess_data.prozess_typ
                )
            
            # Prozess-Daten vorbereiten
            prozess_dict = prozess_data.model_dump(exclude_none=True)
            prozess_dict['fin'] = fin

            # DEBUG
            self.logger.info("🔍 DEBUG - prozess_dict vor SLA", 
                            has_deadline='individuelle_deadline' in prozess_dict,
                            keys=list(prozess_dict.keys()))

            # Individuelle Deadline durchreichen wenn vorhanden
            if prozess_data.individuelle_deadline:
                prozess_dict['individuelle_deadline'] = prozess_data.individuelle_deadline

            # SLA-Daten berechnen (berücksichtigt jetzt individuelle_deadline)
            prozess_dict = await self._calculate_sla_data(prozess_dict)
            
            # Bearbeiter normalisieren
            if prozess_dict.get('bearbeiter'):
                prozess_dict['bearbeiter'] = self._normalize_bearbeiter_name(
                    prozess_dict['bearbeiter']
                )
            
            # Zeitstempel setzen
            now = datetime.now()
            prozess_dict['start_timestamp'] = now
            prozess_dict['erstellt_am'] = now
            prozess_dict['aktualisiert_am'] = now

            # Wenn Status BEENDET, dann auch ende_timestamp setzen
            if prozess_dict.get('status') == 'BEENDET':
                prozess_dict['ende_timestamp'] = now
                self.logger.info("Prozess wird als BEENDET angelegt - setze ende_timestamp", 
                                prozess_id=prozess_dict['prozess_id'])
            
            # In BigQuery speichern
            success = await self.bigquery_service.create_fahrzeug_prozess(prozess_dict)
            
            if not success:
                raise RuntimeError("Prozess konnte nicht gespeichert werden")
            
            # Response-Objekt erstellen
            response = FahrzeugProzessResponse(**prozess_dict)
            
            self.logger.info("✅ Fahrzeugprozess erfolgreich erstellt", 
                        fin=fin,
                        prozess_id=response.prozess_id,
                        prozess_typ=response.prozess_typ,
                        sla_deadline=response.sla_deadline_datum)
            
            return response
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Erstellen des Fahrzeugprozesses", 
                            error=str(e), 
                            fin=fin)
            raise

    async def _close_open_processes(self, fin: str, neuer_prozess_typ: str):
        """
        Beendet alle offenen Prozesse eines Fahrzeugs.
        Strategie:
        1. Versuche direkt zu beenden wenn alt genug
        2. Bei jungen Prozessen oder Fehler → in cleanup_queue einplanen
        """
        try:
            # Alle offenen Prozesse des Fahrzeugs finden
            find_query = f"""
            SELECT ... 
            FROM `{self.bigquery_service.dataset_ref}.fahrzeug_prozesse`
            WHERE fin = @fin
            AND ende_timestamp IS NULL
            """

            # Und dann die Query mit Parametern ausführen:
            params = [bigquery.ScalarQueryParameter("fin", "STRING", fin)]
            open_processes = await self.bigquery_service.execute_query(find_query, params)
            
            if not open_processes:
                self.logger.debug("Keine offenen Prozesse zum Beenden gefunden", fin=fin)
                return
            
            for process in open_processes:
                prozess_id = process.get('prozess_id')
                # Null-Check für prozess_id
                if not prozess_id:
                    self.logger.warning("Prozess ohne ID gefunden, überspringe", 
                                    fin=fin, process=process)
                    continue
                    
                age_minutes = process.get('age_minutes', 0)
                
                if age_minutes >= 120:  # 2 Stunden alt - UPDATE sollte funktionieren
                    # Versuche direktes UPDATE
                    update_query = f"""
                    UPDATE `{self.bigquery_service.dataset_ref}.fahrzeug_prozesse`
                    SET 
                        ende_timestamp = CURRENT_DATETIME(),
                        status = 'BEENDET',
                        aktualisiert_am = CURRENT_DATETIME(),
                        notizen = CONCAT(IFNULL(notizen, ''), ' | Auto-beendet: Start von {neuer_prozess_typ}')
                    WHERE prozess_id = '{prozess_id}'
                    AND fin = '{fin}'
                    AND ende_timestamp IS NULL
                    """
                    
                    try:
                        await self.bigquery_service.execute_query(update_query)
                        self.logger.info("✅ Prozess direkt beendet", 
                                    prozess_id=prozess_id,
                                    age_minutes=age_minutes)
                    except Exception as e:
                        if "streaming buffer" in str(e).lower():
                            # Streaming Buffer Problem - in Queue
                            self.logger.info("⏱️ Streaming Buffer - plane Cleanup", 
                                        prozess_id=prozess_id)
                            await self._schedule_process_cleanup(fin, prozess_id)
                        else:
                            # Anderer Fehler
                            self.logger.error("❌ UPDATE fehlgeschlagen", 
                                            prozess_id=prozess_id, 
                                            error=str(e))
                else:
                    # Prozess zu jung - direkt in Queue
                    wait_minutes = 125 - age_minutes  # 5 Minuten Puffer
                    scheduled_time = datetime.now() + timedelta(minutes=wait_minutes)
                    
                    self.logger.info("⏱️ Prozess zu jung - plane Cleanup", 
                                prozess_id=prozess_id,
                                age_minutes=age_minutes,
                                wait_minutes=wait_minutes)
                    
                    await self._schedule_process_cleanup(
                        fin, 
                        prozess_id,
                        scheduled_for=scheduled_time
                    )
                    
        except Exception as e:
            self.logger.warning("⚠️ Fehler beim Prozess-Cleanup", 
                            error=str(e), fin=fin)
            # Nicht abbrechen - neuer Prozess soll trotzdem erstellt werden

    async def _schedule_process_cleanup(
        self, 
        fin: str, 
        prozess_id: str,
        scheduled_for: Optional[datetime] = None
    ):
        """
        Plant einen Prozess-Cleanup in der Queue.
        
        Args:
            fin: Fahrzeug-FIN
            prozess_id: ID des zu beendenden Prozesses
            scheduled_for: Wann soll der Cleanup laufen (default: in 125 Minuten)
        """
        try:
            import uuid
            
            if not scheduled_for:
                scheduled_for = datetime.now() + timedelta(minutes=125)
            
            cleanup_entry = {
                'queue_id': str(uuid.uuid4()),
                'fin': fin,
                'prozess_id': prozess_id,  # NEU: Direkt als Feld
                'cleanup_type': 'PROZESS_WECHSEL',
                'scheduled_for': scheduled_for.isoformat(),
                'processed': False,
                'created_at': datetime.now().isoformat(),
                'zusatz_daten': json.dumps({
                    'reason': 'Prozesswechsel - alter Prozess beenden',
                    'scheduled_at': datetime.now().isoformat()
                })
            }
            
            success = await self.bigquery_service.insert_cleanup_queue(cleanup_entry)
            
            if success:
                self.logger.info("📋 Cleanup geplant", 
                            prozess_id=prozess_id,
                            scheduled_for=scheduled_for.isoformat())
            else:
                self.logger.error("❌ Cleanup-Planung fehlgeschlagen", 
                                prozess_id=prozess_id)
                
        except Exception as e:
            self.logger.error("❌ Fehler bei Cleanup-Planung", 
                            error=str(e),
                            prozess_id=prozess_id)

    async def get_vehicle_process_history(
        self, 
        fin: str, 
        limit: int = 50
    ) -> List[FahrzeugProzessResponse]:
        """
        Holt die komplette Prozess-Historie eines Fahrzeugs.
        """
        try:
            # Fahrzeug prüfen
            if not await self.bigquery_service.get_fahrzeug_by_fin(fin):
                raise ValueError(f"Fahrzeug {fin} nicht gefunden")
            
            # Prozesse aus BigQuery holen
            prozesse = await self.bigquery_service.get_prozesse_by_fin(fin, limit)
            
            # In Response-Objekte konvertieren
            result = []
            for prozess in prozesse:
                # SLA-Daten anreichern
                prozess = await self._calculate_sla_data(prozess)
                result.append(FahrzeugProzessResponse(**prozess))
            
            self.logger.info("✅ Prozess-Historie abgerufen", 
                        fin=fin, 
                        count=len(result))
            
            return result
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Abrufen der Prozess-Historie", 
                            error=str(e))
            raise

    async def update_vehicle_process(
        self,
        fin: str,
        prozess_id: str,
        prozess_update: FahrzeugProzessRequest
    ) -> Optional[FahrzeugProzessResponse]:
        """
        Aktualisiert einen bestehenden Prozess.
        
        Erstellt einen neuen Prozess-Eintrag mit aktualisiertem Status
        (für Audit-Trail).
        """
        try:
            # Aktuellen Prozess holen
            current = await self.bigquery_service.get_prozess_by_id(prozess_id)
            if not current:
                return None
            
            # Neue Prozess-ID für Update generieren
            new_prozess_id = self._generate_process_id(
                fin, 
                prozess_update.prozess_typ,
                suffix="update"
            )
            
            # Update-Daten vorbereiten
            prozess_dict = prozess_update.model_dump(exclude_none=True)
            prozess_dict['prozess_id'] = new_prozess_id
            prozess_dict['fin'] = fin
            prozess_dict['parent_prozess_id'] = prozess_id  # Referenz zum Original
            
            # Zeitstempel
            now = datetime.now()
            prozess_dict['aktualisiert_am'] = now
            prozess_dict['erstellt_am'] = current.get('erstellt_am', now)
            
            # SLA neu berechnen
            prozess_dict = await self._calculate_sla_data(prozess_dict)
            
            # Speichern
            success = await self.bigquery_service.create_fahrzeug_prozess(prozess_dict)
            
            if success:
                return FahrzeugProzessResponse(**prozess_dict)
            
            return None
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Update des Prozesses", 
                            error=str(e))
            raise

    async def complete_vehicle_process(
        self,
        fin: str,
        prozess_id: str,
        abschluss_notiz: Optional[str] = None
    ) -> bool:
        """
        Schließt einen Prozess ab.
        """
        try:
            # Prozess holen für korrekten Typ
            current = await self.bigquery_service.get_prozess_by_id(prozess_id)
            if not current:
                return False
                
            # Type Hint für Pylance
            from typing import cast
            update_data: FahrzeugProzessRequest = cast(
                FahrzeugProzessRequest,
                {
                    "prozess_typ": current.get('prozess_typ', ProzessTyp.VERKAUF),
                    "status": "Abgeschlossen",
                    "notizen": abschluss_notiz or "Prozess abgeschlossen"
                }
            )
            
            # Prozess holen für korrekten Typ
            current = await self.bigquery_service.get_prozess_by_id(prozess_id)
            if current:
                update_data.prozess_typ = current['prozess_typ']
            
            updated = await self.update_vehicle_process(fin, prozess_id, update_data)
            
            return updated is not None
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Abschließen des Prozesses", 
                            error=str(e))
            raise

   
    async def complete_vehicle_sale(self, fin: str, verkaufsdaten: Optional[Dict[str, Any]] = None) -> bool:
        """
        Schließt den Verkaufsprozess und alle anderen offenen Prozesse ab.
        Erstellt einen temporären Abschluss-Record der später aktualisiert wird.
        
        Args:
            fin: Fahrzeug-FIN
            verkaufsdaten: Optional - Verkaufsinformationen (Preis, Käufer, etc.)
            
        Returns:
            True wenn erfolgreich
        """
        try:
            # 1. Erstelle einen "Verkauft" Status-Eintrag
            verkauft_prozess = {
                'prozess_id': self._generate_process_id(fin, 'Verkauf', 'abgeschlossen'),
                'fin': fin,
                'prozess_typ': 'Verkauf',
                'status': 'VERKAUFT',
                'bearbeiter': verkaufsdaten.get('verkaufsberater') if verkaufsdaten else None,
                'start_timestamp': datetime.now(),
                'ende_timestamp': datetime.now(),
                'notizen': f"Fahrzeug verkauft. VK: {verkaufsdaten.get('verkaufspreis')}€" if verkaufsdaten else "Fahrzeug verkauft",
                'datenquelle': 'api_verkaufsabschluss',
                'zusatz_daten': json.dumps(verkaufsdaten) if verkaufsdaten else None,
                'erstellt_am': datetime.now(),
                'aktualisiert_am': datetime.now()
            }
            
            # Speichere Verkaufsabschluss
            await self.bigquery_service.create_fahrzeug_prozess(verkauft_prozess)
            
            # 2. Markiere Fahrzeug als inaktiv
            await self.bigquery_service.execute_query(f"""
                UPDATE `{self.bigquery_service.dataset_ref}.fahrzeuge_stamm`
                SET 
                    aktiv = FALSE,
                    updated_at = CURRENT_TIMESTAMP()
                WHERE fin = '{fin}'
            """)
            
            # 3. Erstelle einen Cleanup-Task für später
            await self._schedule_final_cleanup(fin, datetime.now())
            
            self.logger.info("✅ Fahrzeug verkauft und zur Bereinigung vorgemerkt", fin=fin)
            return True
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Verkaufsabschluss", fin=fin, error=str(e))
            return False
    
    async def _schedule_final_cleanup(self, fin: str, verkaufszeitpunkt: datetime):
        """
        Plant die finale Bereinigung nach Ablauf der Streaming Buffer Zeit.
        """
        cleanup_entry = {
            'queue_id': str(uuid.uuid4()),
            'fin': fin,
            'cleanup_type': 'VERKAUFSABSCHLUSS',
            'scheduled_for': (verkaufszeitpunkt + timedelta(hours=2)).isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        # Nutze die vorhandene Methode statt direktem SQL
        success = await self.bigquery_service.insert_cleanup_queue(cleanup_entry)
        
        if not success:
            self.logger.warning(f"⚠️ Cleanup-Task konnte nicht geplant werden für {fin}")



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
        """
        Berechnet SLA-relevante Felder.
        Berücksichtigt individuelle Deadlines wenn vorhanden.
        """
        
        # Kopiere das Original-Dict, um keine Felder zu verlieren!
        prozess_data.copy()  

        # DEBUG
        self.logger.info("🔍 DEBUG - _calculate_sla_data Start",
                        has_deadline='individuelle_deadline' in prozess_data,
                        deadline_value=prozess_data.get('individuelle_deadline'))
        

        # Prüfe auf individuelle Deadline
        if prozess_data.get('individuelle_deadline'):
            # Individuelle Deadline hat Vorrang
            if isinstance(prozess_data['individuelle_deadline'], str):
                deadline = datetime.fromisoformat(prozess_data['individuelle_deadline'].replace('Z', '+00:00'))
            else:
                deadline = prozess_data['individuelle_deadline']
            
            # WICHTIG: Entferne Timezone-Info für Konsistenz
            deadline_naive = deadline.replace(tzinfo=None) if deadline.tzinfo else deadline
            
            start_time = prozess_data.get('start_timestamp') or prozess_data.get('erstellt_am') or datetime.now()
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            # WICHTIG: Entferne auch hier Timezone-Info
            start_time_naive = start_time.replace(tzinfo=None) if hasattr(start_time, 'tzinfo') and start_time.tzinfo else start_time
            
            # Berechne SLA-Stunden aus individueller Deadline (beide naive)
            sla_stunden = (deadline_naive - start_time_naive).total_seconds() / 3600
            
            prozess_data['sla_deadline_datum'] = deadline_naive.date()
            prozess_data['tage_bis_sla_deadline'] = (deadline_naive.date() - date.today()).days
            prozess_data['sla_tage'] = max(1, int(sla_stunden // 24))
            prozess_data['individuelle_deadline_gesetzt'] = True
            prozess_data['individuelle_deadline'] = deadline_naive.isoformat() 
            
            self.logger.info("📅 Individuelle Deadline gesetzt",
                            fin=prozess_data.get('fin'),
                            deadline=deadline_naive.isoformat(),
                            tage_bis_deadline=prozess_data['tage_bis_sla_deadline'])
            
            return prozess_data
        
        # Standard SLA-Berechnung (wie bisher)
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
        
        if prozess_typ_enum.value not in ProcessConfig.PROCESS_CONFIG:
            return prozess_data

        config = ProcessConfig.PROCESS_CONFIG[prozess_typ_enum.value]
        sla_stunden = config['sla_stunden']
        
        # Standard SLA-Deadline berechnen
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
        prozess_data['individuelle_deadline_gesetzt'] = False
        
        return prozess_data
    
    def _normalize_bearbeiter_name(self, bearbeiter: Optional[str]) -> Optional[str]:
        """Normalisiert Bearbeiternamen."""
        if not bearbeiter:
            return None
        
        # Nutze zentrale Mappings
        return CentralMappings.normalize_bearbeiter(bearbeiter)
    
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
        # BEENDETE Prozesse sind NIE kritisch
        if fahrzeug.status in ['BEENDET', 'VERKAUFT']:
            return False
            
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
