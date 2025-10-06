# src/services/process_service.py
"""
ProcessService - Zentrale Geschäftslogik für Fahrzeugprozesse
Reinhardt Automobile GmbH - RA Autohaus Tracker

Unified Data Processing für alle Eingangswege:
- Zapier Integration
- E-Mail Parser (Flowers)
- Direct API Calls
- Background Task Processing
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import re
import structlog

from src.services.bigquery_service import BigQueryService
from src.services.vehicle_service import VehicleService
from src.models.integration import (
    FahrzeugStammCreate, FahrzeugProzessCreate, 
    ProzessTyp, Datenquelle
)
from decimal import Decimal
from src.core.mappings import CentralMappings

logger = structlog.get_logger(__name__)

class ProcessingSource(Enum):
    """Datenquelle für eingehende Prozess-Updates"""
    ZAPIER = "zapier"
    EMAIL = "email"  
    API = "api"
    FLOWERS = "flowers"
    MANUAL = "manual"

class ProcessService:
    """
    Zentrale Business Logic für Fahrzeugprozess-Verwaltung.
    
    Funktionen:
    - Unified Data Processing aus verschiedenen Quellen
    - Datenvalidierung und -normalisierung
    - SLA-Berechnung und -Monitoring
    - Background Task Processing
    - Integration mit BigQuery über VehicleService
    """
    
    def __init__(
        self, 
        vehicle_service: VehicleService,
        bigquery_service: BigQueryService
    ):
        self.vehicle_service = vehicle_service
        self.bigquery_service = bigquery_service
        self.logger = logger

        self.mappings = CentralMappings
        
        # SLA-Definitionen in Stunden
        self.sla_hours = {
            ProzessTyp.EINKAUF: 48,      # 2 Tage
            ProzessTyp.ANLIEFERUNG: 24,  # 1 Tag
            ProzessTyp.AUFBEREITUNG: 72, # 3 Tage  
            ProzessTyp.FOTO: 24,         # 1 Tag
            ProzessTyp.WERKSTATT: 120,   # 5 Tage
            ProzessTyp.VERKAUF: 168,     # 7 Tage
        }
    
    # ===============================
    # Unified Data Processing
    # ===============================
    
    async def process_unified_data(
        self,
        data: Dict[str, Any],
        source: ProcessingSource,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Zentrale Methode für einheitliche Datenverarbeitung.
        
        Args:
            data: Rohdaten aus verschiedenen Quellen
            source: Quelle der Daten (Zapier, E-Mail, etc.)
            metadata: Zusätzliche Metadaten (Headers, Zeitstempel, etc.)
            
        Returns:
            Verarbeitungsresultat mit Status und Details
        """
        processing_id = f"proc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{source.value}"
        
        logger.info("🔄 Unified Data Processing gestartet",
                   processing_id=processing_id,
                   source=source.value,
                   data_keys=list(data.keys()))
        
        try:
            # 1. Daten normalisieren
            normalized_data = await self._normalize_input_data(data, source)
            
            # 2. Geschäftsregeln validieren
            validation_result = await self._validate_business_rules(normalized_data)
            if not validation_result["valid"]:
                raise ValueError(f"Validierung fehlgeschlagen: {validation_result['errors']}")
            
            # 3. Fahrzeug und Prozess verarbeiten
            result = await self._process_vehicle_and_process(
                normalized_data, source, processing_id
            )
        
            # 4. SLA-Status berechnen (nur wenn gültiger prozess_typ vorhanden)
            sla_data = {}
            prozess_typ = normalized_data.get("prozess_typ")
            if prozess_typ and isinstance(prozess_typ, ProzessTyp):
                sla_data = self._calculate_sla_data(
                    prozess_typ,
                    normalized_data.get("start_timestamp", datetime.now())
                )
                result.update(sla_data)
            # 5. Success Response
            logger.info("✅ Unified Processing erfolgreich",
                       processing_id=processing_id,
                       fin=normalized_data.get("fin"),
                       prozess_typ=str(normalized_data.get("prozess_typ")))
            
            return {
                "success": True,
                "processing_id": processing_id,
                "source": source.value,
                "result": result,
                "sla_data": sla_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("❌ Unified Processing fehlgeschlagen",
                        processing_id=processing_id,
                        source=source.value,
                        error=str(e),
                        exc_info=True)
            
            return {
                "success": False,
                "processing_id": processing_id,
                "source": source.value,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # ===============================
    # Zapier Integration
    # ===============================
    
    async def process_zapier_webhook(
        self,
        webhook_data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Verarbeitet Zapier Webhook-Daten.
        
        Expected Zapier Payload:
        {
            "fahrzeug_fin": "WVWZZZ1JZ8W123456",
            "prozess_name": "gwa",  # wird zu "Aufbereitung"
            "neuer_status": "In Bearbeitung", 
            "bearbeiter_name": "Thomas K.",  # wird zu "Thomas Küfner"
            "prioritaet": "3",
            "notizen": "Von Zapier automatisch verarbeitet"
        }
        """
        logger.info("📨 Zapier Webhook verarbeitung",
                   keys=list(webhook_data.keys()) if webhook_data else [])
        
        # Zapier-spezifische Feld-Mappings
        zapier_mapped = {
            "fin": webhook_data.get("fahrzeug_fin"),
            "prozess_typ": webhook_data.get("prozess_name"),
            "status": webhook_data.get("neuer_status"),
            "bearbeiter": webhook_data.get("bearbeiter_name"),
            "prioritaet": webhook_data.get("prioritaet"),
            "notizen": webhook_data.get("notizen", "Automatisch von Zapier verarbeitet"),
            "zusatz_daten": {
                "zapier_timestamp": webhook_data.get("timestamp"),
                "zapier_trigger": webhook_data.get("trigger_type"),
                "original_payload": webhook_data
            }
        }
        
        return await self.process_unified_data(
            zapier_mapped,
            ProcessingSource.ZAPIER,
            metadata={"headers": headers}
        )
    
    # ===============================
    # E-Mail Processing (Flowers)
    # ===============================
    
    async def process_email_data(
        self,
        email_content: str,
        subject: str,
        sender: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parst E-Mail-Inhalte und extrahiert Fahrzeugprozess-Informationen.
        
        Für Flowers E-Mails mit strukturierten Informationen.
        """
        logger.info("📧 E-Mail Processing gestartet",
                   sender=sender,
                   subject=subject[:100])
        
        try:
            # E-Mail-Inhalt parsen
            parsed_data = await self._parse_email_content(
                email_content, subject, sender
            )
            
            if not parsed_data:
                raise ValueError("Keine relevanten Fahrzeugdaten in E-Mail gefunden")
            
            return await self.process_unified_data(
                parsed_data,
                ProcessingSource.EMAIL,
                metadata={
                    "email_subject": subject,
                    "email_sender": sender,
                    "email_metadata": metadata
                }
            )
            
        except Exception as e:
            logger.error("❌ E-Mail Processing fehlgeschlagen",
                        sender=sender,
                        error=str(e))
            raise
    
    # ===============================
    # Internal Processing Methods
    # ===============================
    async def _normalize_input_data(
        self,
        data: Dict[str, Any],
        source: ProcessingSource
    ) -> Dict[str, Any]:
        """Normalisiert Eingabedaten mit zentralen Mappings."""
        
        normalized = {}
        
        # FIN normalisieren
        fin = data.get("fin") or data.get("fahrzeug_fin") or data.get("vin")
        if fin:
            normalized["fin"] = str(fin).upper().replace("-", "").replace(" ", "")
        
        # Prozesstyp mit zentralen Mappings normalisieren
        prozess_raw = data.get("prozess_typ") or data.get("prozess_name") or data.get("process_type")
        if prozess_raw:
            prozess_normalized = self.mappings.normalize_prozess_typ(prozess_raw)
            # Zu ProzessTyp Enum konvertieren wenn möglich
            try:
                normalized["prozess_typ"] = ProzessTyp(prozess_normalized)
            except ValueError:
                normalized["prozess_typ"] = prozess_raw  # Fallback
        
        # Bearbeiter mit zentralen Mappings normalisieren
        bearbeiter_raw = data.get("bearbeiter") or data.get("bearbeiter_name")
        if bearbeiter_raw:
            normalized["bearbeiter"] = self.mappings.normalize_bearbeiter(bearbeiter_raw)
        
        # Status mit zentralen Mappings normalisieren
        status_raw = data.get("status") or data.get("neuer_status")
        if status_raw:
            normalized["status"] = self.mappings.normalize_status(status_raw)
        
        # Rest bleibt gleich...
        # Priorität konvertieren
        if data.get("prioritaet"):
            try:
                normalized["prioritaet"] = int(data["prioritaet"])
            except (ValueError, TypeError):
                normalized["prioritaet"] = 5  # Default
        
        # Zeitstempel
        normalized["start_timestamp"] = datetime.now()
        
        # In _normalize_input_data, nach Zeile ~290 hinzufügen:

        # Individuelle Deadline verarbeiten
        if data.get("individuelle_deadline"):
            try:
                # Verschiedene Datumsformate unterstützen
                deadline_raw = data["individuelle_deadline"]
                if isinstance(deadline_raw, str):
                    # ISO-Format oder deutsches Format
                    if "T" in deadline_raw:
                        normalized["individuelle_deadline"] = datetime.fromisoformat(deadline_raw)
                    else:
                        # Deutsches Format DD.MM.YYYY
                        from datetime import datetime as dt
                        normalized["individuelle_deadline"] = dt.strptime(deadline_raw, "%d.%m.%Y")
                elif isinstance(deadline_raw, datetime):
                    normalized["individuelle_deadline"] = deadline_raw
            except Exception as e:
                self.logger.warning(f"Konnte individuelle Deadline nicht parsen: {e}")

        # Datenquelle setzen
        source_mapping = {
            ProcessingSource.ZAPIER: Datenquelle.ZAPIER,
            ProcessingSource.EMAIL: Datenquelle.EMAIL,
            ProcessingSource.API: Datenquelle.API,
            ProcessingSource.MANUAL: Datenquelle.MANUAL
        }
        normalized["datenquelle"] = source_mapping.get(source, Datenquelle.API)
        
        # Zusätzliche Daten
        normalized["notizen"] = data.get("notizen", "")
        normalized["zusatz_daten"] = data.get("zusatz_daten", {})
        
        self.logger.info("🔧 Daten mit zentralen Mappings normalisiert",
                    source=source.value,
                    original_keys=list(data.keys()),
                    normalized_keys=list(normalized.keys()))
        
        return normalized
    
    async def _validate_business_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validiert Geschäftsregeln für Fahrzeugprozesse."""
        
        errors = []
        warnings = []
        
        # FIN erforderlich
        if not data.get("fin"):
            errors.append("FIN ist erforderlich")
        elif len(data["fin"]) != 17:
            errors.append("FIN muss 17 Zeichen haben")
        
        # Prozesstyp MUSS gültig sein
        if data.get("prozess_typ"):
            if not isinstance(data["prozess_typ"], ProzessTyp):
                # Versuche zu konvertieren
                try:
                    ProzessTyp(data["prozess_typ"])
                except ValueError:
                    errors.append(f"Ungültiger Prozesstyp: {data['prozess_typ']}")
        else:
            errors.append("Prozesstyp ist erforderlich")
        
        # Status erforderlich
        if not data.get("status"):
            errors.append("Status ist erforderlich")
        
        # Priorität im gültigen Bereich
        if data.get("prioritaet") and not (1 <= data["prioritaet"] <= 10):
            warnings.append("Priorität sollte zwischen 1 und 10 liegen")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def _process_vehicle_and_process(
        self,
        data: Dict[str, Any],
        source: ProcessingSource,
        processing_id: str
    ) -> Dict[str, Any]:
        """Verarbeitet Fahrzeug- und Prozessdaten."""
        
        fin = data["fin"]
        
        # 1. Prüfen ob Fahrzeug existiert
        existing_vehicle = await self.vehicle_service.get_vehicle_details(fin)
        
        if not existing_vehicle:
            logger.info("🆕 Neues Fahrzeug wird erstellt", fin=fin)
            
            # Minimale Fahrzeugdaten aus Zapier/Email
            from src.models.integration import (
                FahrzeugStammCreate, 
                Antriebsart, 
                Bereifungsart, 
                Besteuerungsart
            )
            from datetime import date

            fahrzeug_data = FahrzeugStammCreate(
                fin=fin,
                marke=data.get("marke", "Unbekannt"),
                modell=data.get("modell", "Unbekannt"),
                antriebsart=Antriebsart.BENZIN,
                farbe="Unbekannt",
                baujahr=datetime.now().year,
                datum_erstzulassung=date.today(),  # <- Hinzugefügt
                kw_leistung=1,
                km_stand=0,
                anzahl_fahrzeugschluessel=0,
                bereifungsart=Bereifungsart.SOMMER,
                anzahl_vorhalter=0,
                ek_netto=Decimal("0"),
                besteuerungsart=Besteuerungsart.REGEL,
                erstellt_aus_email=False,
                datenquelle_fahrzeug=data.get("datenquelle", Datenquelle.API)
            )
            
            # Fahrzeug erstellen (ohne Prozess, der kommt gleich)
            await self.vehicle_service.create_complete_vehicle(
                fahrzeug_data=fahrzeug_data,
                prozess_data=None
            )
        
        # 2. Prozess-Update verarbeiten
        process_result = await self._update_vehicle_process(data, processing_id)
        
        return {
            "vehicle_exists": existing_vehicle is not None,
            "process_updated": process_result["success"],
            "fin": fin,
            "prozess_typ": str(data.get("prozess_typ")),
            "status": data.get("status")
        }
    
    async def _update_vehicle_process(
        self,
        data: Dict[str, Any],
        processing_id: str
    ) -> Dict[str, Any]:
        """Aktualisiert Fahrzeugprozess in BigQuery."""
        
        try:
            # Prozess-Daten vorbereiten
            from src.models.integration import FahrzeugProzessCreate
            
            # pyright: ignore[reportCallIssue]
            prozess_data = FahrzeugProzessCreate(
                prozess_id=data.get("prozess_id"),  # Externe ID durchreichen!
                fin=data["fin"],
                prozess_typ=data["prozess_typ"],
                status=data.get("status", "WARTESCHLANGE"),
                bearbeiter=data.get("bearbeiter"),
                prioritaet=str(data.get("prioritaet", 5)),
                anlieferung_datum=None,  # Optional
                start_timestamp=data.get("start_timestamp"),  # Falls vorhanden
                ende_timestamp=None,  # Optional
                sla_tage=None,  # Wird später berechnet
                datenquelle=data.get("datenquelle", Datenquelle.API),
                notizen=data.get("notizen", ""),
                zusatz_daten=data.get("zusatz_daten", {})
            )
            
            # Prozess über VehicleService erstellen
            created_process = await self.vehicle_service.create_vehicle_process(
                fin=data["fin"],
                prozess_data=prozess_data
            )
            
            logger.info("📝 Prozess erfolgreich erstellt",
                    fin=data.get("fin"),
                    prozess_id=created_process.prozess_id,
                    prozess_typ=created_process.prozess_typ,
                    status=data.get("status"),
                    processing_id=processing_id)
            
            return {"success": True, "processing_id": processing_id, "prozess_id": created_process.prozess_id}
            
        except Exception as e:
            logger.error("❌ Fehler beim Prozess-Update",
                        error=str(e),
                        fin=data.get("fin"))
            return {"success": False, "processing_id": processing_id, "error": str(e)}
    
    def _calculate_sla_data(
        self,
        prozess_typ: ProzessTyp,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Berechnet SLA-Status für einen Prozess."""
        
        if not prozess_typ or prozess_typ not in self.sla_hours:
            return {
                "sla_hours": None,
                "sla_deadline": None,
                "hours_remaining": None,
                "is_critical": False
            }
        
        sla_hours = self.sla_hours[prozess_typ]
        deadline = start_time + timedelta(hours=sla_hours)
        hours_remaining = (deadline - datetime.now()).total_seconds() / 3600
        
        return {
            "sla_hours": sla_hours,
            "sla_deadline": deadline.isoformat(),
            "hours_remaining": round(hours_remaining, 1),
            "is_critical": hours_remaining <= 0,
            "is_warning": 0 < hours_remaining <= (sla_hours * 0.2)  # 20% der SLA-Zeit
        }
    
    async def _parse_email_content(
        self,
        content: str,
        subject: str,
        sender: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parst E-Mail-Inhalte mit zentralen Mappings.
        """
        
        # FIN-Pattern (17 alphanumerische Zeichen)
        fin_pattern = r'\b[A-Z0-9]{17}\b'

        # WICHTIG: Suche FIN in BEIDEN - Subject UND Content
        combined_text = f"{subject} {content}".upper()

        fin_matches = re.findall(fin_pattern, content.upper())
        
        if not fin_matches:
            return None
        
        # Kombiniere Subject und Content für Analyse
        full_text = f"{subject} {content}"
        
        # Keywords für Prozesstyp-Erkennung
        prozess_keywords = {
            'verkauf': ['verkauf', 'verkaufsbereit', 'verkäufer', 'vk'],
            'foto': ['foto', 'fotografiert', 'bilder', 'fotos'],
            'werkstatt': ['werkstatt', 'reparatur', 'service', 'inspektion'],
            'aufbereitung': ['aufbereitung', 'gwa', 'reinigung', 'politur'],
            'anlieferung': ['anlieferung', 'angekommen', 'eingetroffen'],
            'einkauf': ['einkauf', 'angekauft', 'erworben', 'gekauft']
        }
        
        detected_prozess = 'aufbereitung'  # Default
        for prozess_typ, keywords in prozess_keywords.items():
            if any(keyword in full_text.lower() for keyword in keywords):
                detected_prozess = prozess_typ
                break
        
        # Keywords für Status-Erkennung
        status_keywords = {
            'beendet': ['fertig', 'abgeschlossen', 'beendet', 'erledigt'],
            'aktiv': ['läuft', 'in bearbeitung', 'aktiv', 'arbeite'],
            'warteschlange': ['wartet', 'wartend', 'bereit für', 'angemeldet']
        }
        
        detected_status = 'warteschlange'  # Default
        for status, keywords in status_keywords.items():
            if any(keyword in full_text.lower() for keyword in keywords):
                detected_status = status
                break
        
        # Bearbeiter aus Sender extrahieren
        bearbeiter_raw = sender.split('@')[0].replace('.', ' ').title() if '@' in sender else 'System'
        
        extracted_data = {
            "fin": fin_matches[0],
            "prozess_typ": detected_prozess,
            "status": detected_status,
            "bearbeiter": bearbeiter_raw,
            "notizen": f"Email von {sender}: {subject}",
            "zusatz_daten": {
                "email_sender": sender,
                "email_subject": subject,
                "detected_prozess": detected_prozess,
                "detected_status": detected_status,
                "fin_found_in": "subject" if fin_matches[0] in subject.upper() else "content"
            }
        }
        
        self.logger.info("📧 Email geparst",
                        fin=fin_matches[0],
                        fin_source="subject" if fin_matches[0] in subject.upper() else "content",
                        prozess=detected_prozess,
                        status=detected_status)
        
        return extracted_data
    
    # ===============================
    # Health Check
    # ===============================
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check für ProcessService."""
        
        try:
            # VehicleService Health Check
            vehicle_health = await self.vehicle_service.health_check()
            
            # BigQuery Health Check  
            bigquery_health = await self.bigquery_service.health_check()
            
            overall_healthy = (
                vehicle_health.get("status") == "healthy" and
                bigquery_health.get("status") == "healthy"
            )
            
            return {
                "status": "healthy" if overall_healthy else "degraded",
                "service": "ProcessService",
                "dependencies": {
                    "vehicle_service": vehicle_health,
                    "bigquery_service": bigquery_health
                },
                "capabilities": {
                    "unified_processing": True,
                    "zapier_integration": True,
                    "email_processing": True,
                    "sla_calculation": True,
                    "process_mappings": len(self.mappings.PROZESS_MAPPINGS),  # <- GEÄNDERT
                    "status_mappings": len(self.mappings.STATUS_MAPPINGS),   # <- NEU
                    "bearbeiter_mappings": len(self.mappings.BEARBEITER_MAPPINGS)  # <- GEÄNDERT
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "ProcessService", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }