# src/services/process_service.py
import uuid
import json
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional
from google.cloud import bigquery

# Absolute Imports
from src.models.integration import UnifiedProcessData, IntegrationResponse
from src.handlers.flowers_handler import FlowersHandler

logger = logging.getLogger(__name__)

# Bearbeiter-Mapping (aus main.py extrahiert)
BEARBEITER_MAPPING = {
    "Thomas K.": "Thomas Küfner",
    "Max R.": "Maximilian Reinhardt", 
    "Hans M.": "Hans Müller",
    "Anna K.": "Anna Klein", 
    "Thomas W.": "Thomas Weber",
    "Stefan B.": "Stefan Becker",
    "Mike S.": "Michael Schmidt",
    "Jürgen": "Jürgen Hoffmann",
    "Klaus": "Klaus Neumann",
    "Sandra": "Sandra Richter",
    "Alex": "Alexander König",
}


class ProcessService:
    """ZENTRALE Geschäftslogik für alle Prozess-Operationen"""
    
    def __init__(self, bq_client: bigquery.Client):
        self.bq_client = bq_client
        self.flowers_handler = FlowersHandler()
    
    def resolve_bearbeiter(self, bearbeiter_input: Optional[str]) -> Optional[str]:
        """Bearbeiter-Namen normalisieren"""
        if not bearbeiter_input:
            return None
        
        # Direkte Zuordnung
        if bearbeiter_input in BEARBEITER_MAPPING:
            return BEARBEITER_MAPPING[bearbeiter_input]
        
        # Fuzzy-Matching
        input_lower = bearbeiter_input.lower()
        for flowers_key, full_name in BEARBEITER_MAPPING.items():
            if input_lower in flowers_key.lower() or flowers_key.lower() in input_lower:
                return full_name
        
        return bearbeiter_input
    
    async def check_vehicle_exists(self, fin: str) -> bool:
        """Prüft ob Fahrzeug in BigQuery existiert"""
        try:
            query = """
            SELECT COUNT(*) as count 
            FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
            WHERE fin = @fin AND aktiv = TRUE
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("fin", "STRING", fin)]
            )
            result = self.bq_client.query(query, job_config=job_config)
            return list(result)[0]["count"] > 0
            
        except Exception as e:
            logger.error(f"Vehicle check failed: {e}")
            return False
    
    async def create_vehicle_if_needed(self, data: UnifiedProcessData) -> bool:
        """Erstellt Fahrzeug automatisch falls notwendig"""
        try:
            # Nur erstellen wenn Fahrzeugdaten vorhanden sind
            if not data.marke and not data.farbe:
                return False
                
            vehicle_data = {
                "fin": data.fin,
                "marke": data.marke or "Unbekannt",
                "modell": data.modell or "Unbekannt",
                "antriebsart": data.antriebsart or "Unbekannt", 
                "farbe": data.farbe or "Unbekannt",
                "baujahr": data.baujahr,
                "datum_erstzulassung": data.datum_erstzulassung,
                "kw_leistung": data.kw_leistung,
                "km_stand": data.km_stand,
                "anzahl_fahrzeugschluessel": data.anzahl_fahrzeugschluessel,
                "bereifungsart": data.bereifungsart or "Unbekannt",
                "anzahl_vorhalter": data.anzahl_vorhalter,
                "ek_netto": data.ek_netto,
                "besteuerungsart": data.besteuerungsart or "Unbekannt",
                "erstellt_aus_email": True,
                "datenquelle_fahrzeug": data.datenquelle
            }
            
            return await self._save_vehicle_to_bigquery(vehicle_data)
            
        except Exception as e:
            logger.error(f"Auto vehicle creation failed: {e}")
            return False
    
    async def process_unified_data(self, data: UnifiedProcessData) -> IntegrationResponse:
        """ZENTRALE Methode für alle Datenquellen - konsistent für E-Mail, Zapier, Webhook"""
        warnings = []
        
        try:
            # 1. Prozess-Normalisierung
            normalized_prozess = self.flowers_handler.normalize_prozess_typ(data.prozess_typ)
            if normalized_prozess != data.prozess_typ:
                logger.info(f"Prozess normalisiert: '{data.prozess_typ}' -> '{normalized_prozess}'")
            
            # 2. Bearbeiter-Mapping
            mapped_bearbeiter = self.resolve_bearbeiter(data.bearbeiter)
            if mapped_bearbeiter != data.bearbeiter:
                logger.info(f"Bearbeiter gemappt: '{data.bearbeiter}' -> '{mapped_bearbeiter}'")
            
            # 3. Fahrzeug-Existenz prüfen
            vehicle_exists = await self.check_vehicle_exists(data.fin)
            vehicle_created = False
            
            if not vehicle_exists:
                vehicle_created = await self.create_vehicle_if_needed(data)
                if vehicle_created:
                    logger.info(f"Fahrzeug automatisch erstellt: {data.fin}")
                else:
                    warnings.append(f"Fahrzeug {data.fin} existiert nicht im System")
            
            # 4. Prozess-Daten erstellen
            prozess_id = str(uuid.uuid4())
            
            process_data = {
                "prozess_id": prozess_id,
                "fin": data.fin,
                "prozess_typ": normalized_prozess,
                "status": data.status,
                "bearbeiter": mapped_bearbeiter,
                "prioritaet": data.prioritaet,
                "start_timestamp": data.external_timestamp or datetime.now(),
                "datenquelle": data.datenquelle,
                "notizen": data.notizen
            }
            
            # Status-spezifische Timestamps
            if data.status.lower() == "abgeschlossen":
                process_data["ende_timestamp"] = data.external_timestamp or datetime.now()
            
            # Zusatzdaten als JSON
            if data.zusatz_daten:
                zusatz_json = json.dumps(data.zusatz_daten, default=str)
                process_data["notizen"] = f"{data.notizen or ''} | Zusatzdaten: {zusatz_json}"
            
            # 5. In BigQuery speichern
            success = await self._save_process_to_bigquery(process_data)
            
            if success:
                return IntegrationResponse(
                    success=True,
                    message="Prozess erfolgreich verarbeitet",
                    fin=data.fin,
                    prozess_typ=normalized_prozess,
                    status=data.status,
                    prozess_id=prozess_id,
                    vehicle_created=vehicle_created,
                    bearbeiter_mapped=f"{data.bearbeiter} -> {mapped_bearbeiter}" if mapped_bearbeiter != data.bearbeiter else None,
                    warnings=warnings,
                    datenquelle=data.datenquelle
                )
            else:
                return IntegrationResponse(
                    success=False,
                    message="BigQuery-Speicherung fehlgeschlagen",
                    fin=data.fin,
                    prozess_typ=normalized_prozess,
                    status=data.status,
                    warnings=warnings,
                    datenquelle=data.datenquelle
                )
                
        except Exception as e:
            logger.error(f"Process unified data failed: {e}")
            return IntegrationResponse(
                success=False,
                message=f"Verarbeitungsfehler: {str(e)}",
                fin=data.fin,
                prozess_typ=data.prozess_typ,
                status=data.status,
                datenquelle=data.datenquelle
            )
    
    async def _save_vehicle_to_bigquery(self, vehicle_data: Dict[str, Any]) -> bool:
        """Fahrzeug in BigQuery speichern"""
        try:
            table_id = "ra-autohaus-tracker.autohaus.fahrzeuge_stamm"
            table = self.bq_client.get_table(table_id)

            # DateTime-Konvertierung
            row = {}
            for key, value in vehicle_data.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif isinstance(value, date):
                    row[key] = value.isoformat()
                elif value is not None:
                    row[key] = value

            if "ersterfassung_datum" not in row:
                row["ersterfassung_datum"] = datetime.now().isoformat()
            
            row["aktiv"] = True

            errors = self.bq_client.insert_rows_json(table, [row])
            if errors:
                logger.error(f"BigQuery vehicle errors: {errors}")
                return False

            logger.info(f"Vehicle saved to BigQuery: {vehicle_data['fin']}")
            return True

        except Exception as e:
            logger.error(f"Vehicle save error: {e}")
            return False

    async def _save_process_to_bigquery(self, process_data: Dict[str, Any]) -> bool:
        """Prozess in BigQuery speichern"""
        try:
            table_id = "ra-autohaus-tracker.autohaus.fahrzeug_prozesse"
            table = self.bq_client.get_table(table_id)

            # DateTime-Konvertierung
            row = {}
            for key, value in process_data.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif isinstance(value, date):
                    row[key] = value.isoformat()
                elif value is not None:
                    row[key] = value

            if "erstellt_am" not in row:
                row["erstellt_am"] = datetime.now().isoformat()

            errors = self.bq_client.insert_rows_json(table, [row])
            if errors:
                logger.error(f"BigQuery process errors: {errors}")
                return False

            logger.info(f"Process saved to BigQuery: {process_data['prozess_id']}")
            return True

        except Exception as e:
            logger.error(f"Process save error: {e}")
            return False