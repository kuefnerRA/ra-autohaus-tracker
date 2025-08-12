import logging
import os
import uuid
import json
import re
from datetime import date, datetime
from typing import Any, Dict, Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator

# BigQuery direkt importieren
try:
    from google.cloud import bigquery
    BIGQUERY_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ BigQuery verfügbar")
except ImportError:
    BIGQUERY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ BigQuery nicht verfügbar")

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="RA Autohaus Tracker API",
    description="Multi-Source Fahrzeugprozess-Tracking für Reinhardt Automobile",
    version="1.0.0",
)

# BigQuery Client (falls verfügbar)
if BIGQUERY_AVAILABLE:
    try:
        bq_client = bigquery.Client(project="ra-autohaus-tracker")
        logger.info("BigQuery Client initialisiert")
    except Exception as e:
        logger.error(f"BigQuery Client Fehler: {e}")
        bq_client = None
else:
    bq_client = None

# In-Memory Fallback
vehicles_db = {}
processes_db = {}

# === ORIGINAL MODELS ===

class VehicleCreate(BaseModel):
    fin: str = Field(..., min_length=17, max_length=17)
    marke: str
    modell: str
    antriebsart: str
    farbe: str
    baujahr: Optional[int] = None

class ProcessCreate(BaseModel):
    fin: str = Field(..., min_length=17, max_length=17)
    prozess_typ: str
    bearbeiter: Optional[str] = None
    prioritaet: Optional[int] = Field(5, ge=1, le=10)
    anlieferung_datum: Optional[date] = None
    notizen: Optional[str] = None

class ProcessUpdate(BaseModel):
    status: str
    bearbeiter: Optional[str] = None
    notizen: Optional[str] = None

# === FLOWERS INTEGRATION MODELS ===

class FlowersWebhookData(BaseModel):
    """Webhook-Daten von Flowers Software"""
    fahrzeug_id: str
    fin: Optional[str] = None
    prozess: str
    status: str
    bearbeiter: Optional[str] = None
    timestamp: Optional[datetime] = None
    zusatz_daten: Optional[Dict[str, Any]] = {}
    
    @validator('prozess')
    def validate_prozess(cls, v):
        """Flowers-Begriffe auf 6 Hauptprozesse mappen"""
        mapping = {
            "transport": "Anlieferung",
            "anlieferung": "Anlieferung",
            "gwa": "Aufbereitung", 
            "aufbereitung": "Aufbereitung",
            "garage": "Werkstatt",
            "werkstatt": "Werkstatt",
            "fotoshooting": "Foto",
            "foto": "Foto",
            "ankauf": "Einkauf",
            "einkauf": "Einkauf",
            "verkauf": "Verkauf"
        }
        return mapping.get(v.lower(), v)

class FlowersEmailData(BaseModel):
    """E-Mail-Daten von Flowers"""
    betreff: str
    inhalt: str
    absender: str
    empfangen_am: datetime
    
class ZapierWebhookData(BaseModel):
    """Zapier Webhook-Format"""
    trigger_typ: str = "flowers_update"
    fahrzeug_fin: str = Field(..., min_length=17, max_length=17)
    prozess_name: str
    neuer_status: str
    bearbeiter_name: Optional[str] = None
    notizen: Optional[str] = None
    original_timestamp: Optional[str] = None

# === FLOWERS E-MAIL PARSER ===

class FlowersEmailParser:
    """Intelligenter Parser für Flowers Software E-Mails"""
    
    @staticmethod
    def extract_fin_from_text(text: str) -> Optional[str]:
        """FIN aus Text extrahieren (17-stellig)"""
        fin_pattern = r'\b[A-HJ-NPR-Z0-9]{17}\b'
        matches = re.findall(fin_pattern, text.upper())
        return matches[0] if matches else None
    
    @staticmethod
    def extract_process_info(betreff: str, inhalt: str) -> Dict[str, Any]:
        """Prozess-Informationen aus E-Mail intelligent extrahieren"""
        
        # Prozess-Typ-Erkennung (auf 6 Hauptprozesse normalisiert)
        prozess_patterns = {
            "Einkauf": ["einkauf", "ankauf", "beschaffung", "akquisition"],
            "Anlieferung": ["anlieferung", "transport", "lieferung", "eingang"],
            "Aufbereitung": ["aufbereitung", "gwa", "reinigung", "vorbereitung"],
            "Foto": ["foto", "fotoshooting", "bilder", "aufnahme"],
            "Werkstatt": ["werkstatt", "garage", "reparatur", "service", "wartung"],
            "Verkauf": ["verkauf", "vertrieb", "verkaufsbereit", "präsentation"]
        }
        
        text_combined = f"{betreff} {inhalt}".lower()
        prozess_typ = None
        
        for prozess, keywords in prozess_patterns.items():
            if any(keyword in text_combined for keyword in keywords):
                prozess_typ = prozess
                break
        
        # Status-Erkennung
        status_patterns = {
            "abgeschlossen": ["fertig", "erledigt", "komplett", "beendet", "abgeschlossen", "done"],
            "in_bearbeitung": ["bearbeitung", "begonnen", "started", "in arbeit", "läuft"],
            "warteschlange": ["warteschlange", "queue", "warten", "eingeplant", "terminiert"],
            "problem": ["problem", "fehler", "issue", "defekt", "störung"],
            "pausiert": ["pausiert", "unterbrochen", "gestoppt", "paused"]
        }
        
        status = "gestartet"  # Default
        for status_key, keywords in status_patterns.items():
            if any(keyword in text_combined for keyword in keywords):
                status = status_key
                break
        
        # Bearbeiter extrahieren
        bearbeiter_pattern = r'(?:bearbeiter|mitarbeiter|techniker|mechaniker)[\s:]*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)'
        bearbeiter_match = re.search(bearbeiter_pattern, inhalt, re.IGNORECASE)
        bearbeiter = bearbeiter_match.group(1).strip() if bearbeiter_match else None
        
        # Priorität extrahieren
        prioritaet_pattern = r'(?:priorität|priority)[\s:]*([1-9]|10)'
        prioritaet_match = re.search(prioritaet_pattern, text_combined, re.IGNORECASE)
        prioritaet = int(prioritaet_match.group(1)) if prioritaet_match else 5
        
        return {
            "prozess_typ": prozess_typ,
            "status": status,
            "bearbeiter": bearbeiter,
            "prioritaet": prioritaet
        }

# === BEARBEITER-MAPPING ===

BEARBEITER_MAPPING = {
    # Flowers Kurznamen -> Vollständige Namen
    "Thomas K.": "Thomas Küfner",
    "Max R.": "Maximilian Reinhardt",
    "Hans M.": "Hans Müller",
    "Anna K.": "Anna Klein", 
    "Thomas W.": "Thomas Weber",
    "Stefan B.": "Stefan Becker",
    "Mike S.": "Michael Schmidt",
    # Werkstatt-Team
    "Jürgen": "Jürgen Hoffmann",
    "Klaus": "Klaus Neumann",
    # Foto-Team  
    "Sandra": "Sandra Richter",
    "Alex": "Alexander König",
}

def resolve_bearbeiter(flowers_bearbeiter: Optional[str]) -> Optional[str]:
    """Bearbeiter-Namen von Flowers auf Vollnamen mappen"""
    if not flowers_bearbeiter:
        return None
    
    # Direkte Zuordnung
    if flowers_bearbeiter in BEARBEITER_MAPPING:
        return BEARBEITER_MAPPING[flowers_bearbeiter]
    
    # Fuzzy-Matching
    flowers_lower = flowers_bearbeiter.lower()
    for flowers_key, full_name in BEARBEITER_MAPPING.items():
        if flowers_lower in flowers_key.lower() or flowers_key.lower() in flowers_lower:
            return full_name
    
    return flowers_bearbeiter

# === ORIGINAL BIGQUERY FUNKTIONEN ===

async def save_vehicle_to_bigquery(vehicle_data: dict) -> bool:
    """Fahrzeug in BigQuery speichern"""
    if not bq_client:
        logger.warning("BigQuery Client nicht verfügbar")
        return False

    try:
        table_id = "ra-autohaus-tracker.autohaus.fahrzeuge_stamm"
        table = bq_client.get_table(table_id)

        now_iso = datetime.now().isoformat()

        row = {
            "fin": vehicle_data["fin"],
            "marke": vehicle_data["marke"],
            "modell": vehicle_data["modell"],
            "antriebsart": vehicle_data["antriebsart"],
            "farbe": vehicle_data["farbe"],
            "baujahr": vehicle_data.get("baujahr"),
            "ersterfassung_datum": now_iso,
            "aktiv": True,
        }

        row = {k: v for k, v in row.items() if v is not None}

        errors = bq_client.insert_rows_json(table, [row])
        if errors:
            logger.error(f"BigQuery errors: {errors}")
            return False

        logger.info(f"✅ Vehicle saved to BigQuery: {vehicle_data['fin']}")
        return True

    except Exception as e:
        logger.error(f"❌ BigQuery save error: {e}")
        return False

async def save_process_to_bigquery(process_data: dict) -> bool:
    """Prozess in BigQuery speichern"""
    if not bq_client:
        return False

    try:
        table_id = "ra-autohaus-tracker.autohaus.fahrzeug_prozesse"
        table = bq_client.get_table(table_id)

        # DateTime-Objekte zu ISO Strings konvertieren
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

        logger.info(f"Inserting process into BigQuery: {row}")

        errors = bq_client.insert_rows_json(table, [row])
        if errors:
            logger.error(f"BigQuery process errors: {errors}")
            return False

        logger.info(f"✅ Process saved to BigQuery: {process_data['prozess_id']}")
        return True

    except Exception as e:
        logger.error(f"❌ BigQuery process save error: {e}")
        return False

async def update_process_in_bigquery(prozess_id: str, update_data: Dict[str, Any]) -> bool:
    """Prozess in BigQuery aktualisieren"""
    if not bq_client:
        return False

    try:
        # Update Query bauen
        set_clauses = []
        query_params = [
            bigquery.ScalarQueryParameter("prozess_id", "STRING", prozess_id)
        ]

        for key, value in update_data.items():
            if value is not None and key not in ["prozess_id"]:
                set_clauses.append(f"{key} = @{key}")

                # Parameter-Typ bestimmen
                if isinstance(value, str):
                    param_type = "STRING"
                elif isinstance(value, int):
                    param_type = "INT64"
                elif isinstance(value, datetime):
                    param_type = "DATETIME"
                    value = value.isoformat()
                else:
                    param_type = "STRING"
                    value = str(value)

                query_params.append(
                    bigquery.ScalarQueryParameter(key, param_type, value)
                )

        if not set_clauses:
            logger.warning("Keine Update-Daten provided")
            return False

        # Aktualisierungs-Timestamp hinzufügen
        set_clauses.append("aktualisiert_am = CURRENT_DATETIME()")

        query = f"""
        UPDATE `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
        SET {', '.join(set_clauses)}
        WHERE prozess_id = @prozess_id
        """

        logger.info(f"Update query: {query}")
        logger.info(f"Parameters: {query_params}")

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        query_job = bq_client.query(query, job_config=job_config)
        query_job.result()

        # Prüfen ob Zeilen betroffen waren
        if query_job.num_dml_affected_rows == 0:
            logger.warning(f"Keine Zeilen aktualisiert für prozess_id: {prozess_id}")
            return False

        logger.info(
            f"✅ Prozess in BigQuery aktualisiert: {prozess_id} ({query_job.num_dml_affected_rows} Zeilen)"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Prozess-Update Fehler: {e}")
        return False

async def create_status_update(
    prozess_id: str,
    alter_status: str,
    neuer_status: str,
    bearbeiter: Optional[str] = None,
    notizen: Optional[str] = None,
) -> bool:
    """Status-Update in separate Tabelle speichern"""
    if not bq_client:
        return False

    try:
        table_id = "ra-autohaus-tracker.autohaus.prozess_status_updates"
        table = bq_client.get_table(table_id)

        update_row = {
            "update_id": str(uuid.uuid4()),
            "prozess_id": prozess_id,
            "alter_status": alter_status,
            "neuer_status": neuer_status,
            "bearbeiter": bearbeiter,
            "update_timestamp": datetime.now().isoformat(),
            "notizen": notizen,
            "datenquelle": "api",
        }

        # None-Werte entfernen
        update_row = {k: v for k, v in update_row.items() if v is not None}

        errors = bq_client.insert_rows_json(table, [update_row])

        if errors:
            logger.error(f"Status-Update BigQuery errors: {errors}")
            return False

        logger.info(f"✅ Status-Update gespeichert: {prozess_id} -> {neuer_status}")
        return True

    except Exception as e:
        logger.error(f"❌ Status-Update Fehler: {e}")
        return False

# === FLOWERS INTEGRATION FUNCTIONS ===

async def process_flowers_data(
    fin: str,
    prozess_typ: str, 
    status: str,
    bearbeiter: Optional[str] = None,
    prioritaet: int = 5,
    datenquelle: str = "flowers",
    notizen: Optional[str] = None,
    zusatz_daten: Optional[Dict] = None,
    external_timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """Zentrale Verarbeitung von Flowers-Daten"""
    try:
        # 1. Bearbeiter-Mapping anwenden
        mapped_bearbeiter = resolve_bearbeiter(bearbeiter)
        
        # 2. Fahrzeug-Existenz prüfen
        vehicle_exists = False
        if bq_client:
            try:
                check_query = """
                SELECT COUNT(*) as count FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
                WHERE fin = @fin AND aktiv = TRUE
                """
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ScalarQueryParameter("fin", "STRING", fin)]
                )
                result = bq_client.query(check_query, job_config=job_config)
                vehicle_exists = list(result)[0]["count"] > 0
            except Exception as e:
                logger.warning(f"Fahrzeug-Check Fehler: {e}")
        
        if not vehicle_exists:
            logger.warning(f"⚠️ Fahrzeug {fin} nicht im System - lege Prozess trotzdem an")
        
        # 3. Prozess-Daten strukturieren
        prozess_id = str(uuid.uuid4())
        
        process_data = {
            "prozess_id": prozess_id,
            "fin": fin,
            "prozess_typ": prozess_typ,
            "status": status,
            "bearbeiter": mapped_bearbeiter,
            "prioritaet": prioritaet,
            "start_timestamp": external_timestamp or datetime.now(),
            "datenquelle": datenquelle,
            "notizen": notizen
        }
        
        # Status-spezifische Timestamps
        if status == "abgeschlossen":
            process_data["ende_timestamp"] = external_timestamp or datetime.now()
        
        # 4. Zusatzdaten als JSON speichern
        if zusatz_daten:
            zusatz_json = json.dumps(zusatz_daten, default=str)
            process_data["notizen"] = f"{notizen or ''} | Zusatzdaten: {zusatz_json}"
        
        return {
            "success": True,
            "process_data": process_data,
            "fahrzeug_existiert": vehicle_exists,
            "bearbeiter_gemappt": f"{bearbeiter} -> {mapped_bearbeiter}" if bearbeiter != mapped_bearbeiter else None
        }
        
    except Exception as e:
        logger.error(f"❌ Flowers-Datenverarbeitung Fehler: {e}")
        return {"success": False, "error": str(e)}

# === ORIGINAL API ENDPOINTS ===

@app.get("/")
async def root():
    return {
        "message": "RA Autohaus Tracker API",
        "version": "1.0.0",
        "docs": "/docs",
        "bigquery_available": BIGQUERY_AVAILABLE,
        "flowers_integration": True,  # ✅ Zeigt Flowers-Integration an
    }

@app.get("/health")
async def health_check():
    """Health Check mit BigQuery Status"""
    bigquery_status = "healthy" if bq_client else "unavailable"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "services": {
            "api": "healthy",
            "bigquery": bigquery_status,
            "bigquery_available": BIGQUERY_AVAILABLE,
            "flowers_integration": True,
        },
    }

@app.post("/fahrzeuge", status_code=201)
async def create_fahrzeug(fahrzeug: VehicleCreate):
    """Fahrzeug anlegen"""
    try:
        bigquery_success = await save_vehicle_to_bigquery(fahrzeug.dict())

        if not bigquery_success:
            logger.warning("BigQuery speichern fehlgeschlagen, verwende Memory")
            vehicles_db[fahrzeug.fin] = {
                **fahrzeug.dict(),
                "erstellt_am": datetime.now().isoformat(),
            }

        return {
            "message": "Fahrzeug erfolgreich angelegt",
            "fin": fahrzeug.fin,
            "storage": "bigquery" if bigquery_success else "memory",
        }

    except Exception as e:
        logger.error(f"Error creating vehicle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fahrzeuge")
async def list_fahrzeuge():
    """Fahrzeuge auflisten"""
    if bq_client:
        try:
            query = """
            SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
            WHERE aktiv = TRUE
            ORDER BY ersterfassung_datum DESC
            LIMIT 50
            """
            result = bq_client.query(query)
            vehicles = [dict(row) for row in result]

            return {
                "fahrzeuge": vehicles,
                "anzahl": len(vehicles),
                "source": "bigquery",
            }
        except Exception as e:
            logger.error(f"BigQuery query error: {e}")

    return {
        "fahrzeuge": list(vehicles_db.values()),
        "anzahl": len(vehicles_db),
        "source": "memory",
    }

@app.get("/fahrzeuge/{fin}")
async def get_fahrzeug(fin: str):
    """Einzelnes Fahrzeug abrufen"""
    if bq_client:
        try:
            query = """
            SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
            WHERE fin = @fin AND aktiv = TRUE
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("fin", "STRING", fin)]
            )
            result = bq_client.query(query, job_config=job_config)
            vehicles = [dict(row) for row in result]

            if vehicles:
                return vehicles[0]

        except Exception as e:
            logger.error(f"BigQuery query error: {e}")

    if fin in vehicles_db:
        return vehicles_db[fin]

    raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")

@app.post("/prozesse/start", status_code=201)
async def start_prozess(prozess: ProcessCreate):
    """Neuen Prozess starten"""
    try:
        prozess_id = str(uuid.uuid4())

        process_data = {
            "prozess_id": prozess_id,
            **prozess.dict(),
            "status": "gestartet",
            "start_timestamp": datetime.now(),
            "datenquelle": "api",
        }

        bigquery_success = await save_process_to_bigquery(process_data)

        if not bigquery_success:
            logger.warning("BigQuery Process speichern fehlgeschlagen, verwende Memory")
            processes_db[prozess_id] = {
                **process_data,
                "start_timestamp": process_data["start_timestamp"].isoformat(),
            }

        return {
            "message": "Prozess erfolgreich gestartet",
            "prozess_id": prozess_id,
            "fin": prozess.fin,
            "prozess_typ": prozess.prozess_typ,
            "storage": "bigquery" if bigquery_success else "memory",
        }

    except Exception as e:
        logger.error(f"Error starting process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/prozesse/{prozess_id}")
async def update_prozess(prozess_id: str, update: ProcessUpdate):
    """Prozess-Status aktualisieren"""
    try:
        update_data = update.dict(exclude_unset=True)

        # Bei Abschluss End-Timestamp setzen
        if update.status == "abgeschlossen":
            update_data["ende_timestamp"] = datetime.now()

        logger.info(f"Updating process {prozess_id} with data: {update_data}")

        success = await update_process_in_bigquery(prozess_id, update_data)

        if not success:
            # Fallback: In Memory suchen und updaten
            if prozess_id in processes_db:
                processes_db[prozess_id].update(update_data)
                success = True
                storage = "memory"
            else:
                raise HTTPException(
                    status_code=404, detail=f"Prozess {prozess_id} nicht gefunden"
                )
        else:
            storage = "bigquery"

        return {
            "message": "Prozess erfolgreich aktualisiert",
            "prozess_id": prozess_id,
            "status": update.status,
            "storage": storage,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/prozesse/{prozess_id}")
async def get_prozess(prozess_id: str):
    """Einzelnen Prozess abrufen"""
    if bq_client:
        try:
            query = """
            SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE prozess_id = @prozess_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("prozess_id", "STRING", prozess_id)
                ]
            )
            result = bq_client.query(query, job_config=job_config)
            processes = [dict(row) for row in result]

            if processes:
                return processes[0]

        except Exception as e:
            logger.error(f"BigQuery process query error: {e}")

    # Fallback: Memory
    if prozess_id in processes_db:
        return processes_db[prozess_id]

    raise HTTPException(status_code=404, detail="Prozess nicht gefunden")

@app.get("/prozesse")
async def list_prozesse(
    fin: Optional[str] = None, status: Optional[str] = None, limit: int = 50
):
    """Alle Prozesse auflisten"""
    if bq_client:
        try:
            where_clauses = []
            query_params = []

            if fin:
                where_clauses.append("fin = @fin")
                query_params.append(bigquery.ScalarQueryParameter("fin", "STRING", fin))

            if status:
                where_clauses.append("status = @status")
                query_params.append(
                    bigquery.ScalarQueryParameter("status", "STRING", status)
                )

            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

            query = f"""
            SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE {where_clause}
            ORDER BY erstellt_am DESC
            LIMIT {limit}
            """

            job_config = (
                bigquery.QueryJobConfig(query_parameters=query_params)
                if query_params
                else None
            )
            result = bq_client.query(query, job_config=job_config)
            processes = [dict(row) for row in result]

            return {
                "prozesse": processes,
                "anzahl": len(processes),
                "source": "bigquery",
            }

        except Exception as e:
            logger.error(f"BigQuery processes query error: {e}")

    # Memory Fallback
    filtered = list(processes_db.values())
    if fin:
        filtered = [p for p in filtered if p.get("fin") == fin]
    if status:
        filtered = [p for p in filtered if p.get("status") == status]

    return {"prozesse": filtered[:limit], "anzahl": len(filtered), "source": "memory"}

# === FLOWERS INTEGRATION ENDPOINTS ===

@app.post("/integration/flowers/webhook")
async def flowers_webhook(data: FlowersWebhookData, background_tasks: BackgroundTasks):
    """Direkter Webhook von Flowers Software"""
    try:
        logger.info(f"🌻 Flowers Webhook: {data.prozess} für {data.fahrzeug_id}")
        
        # FIN validieren/extrahieren
        fin = data.fin or FlowersEmailParser.extract_fin_from_text(data.fahrzeug_id)
        
        if not fin:
            raise HTTPException(status_code=400, detail="FIN konnte nicht ermittelt werden")
        
        # Daten verarbeiten
        result = await process_flowers_data(
            fin=fin,
            prozess_typ=data.prozess,
            status=data.status,
            bearbeiter=data.bearbeiter,
            datenquelle="flowers_webhook",
            zusatz_daten=data.zusatz_daten,
            external_timestamp=data.timestamp
        )
        
        if result["success"]:
            # In BigQuery speichern
            await save_process_to_bigquery(result["process_data"])
            
            return {
                "message": "Flowers Webhook erfolgreich verarbeitet",
                "fin": fin,
                "prozess": data.prozess,
                "status": data.status,
                "bearbeiter_mapping": result.get("bearbeiter_gemappt"),
                "fahrzeug_im_system": result["fahrzeug_existiert"]
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"❌ Flowers Webhook Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/integration/flowers/email")
async def flowers_email_integration(email_data: FlowersEmailData, background_tasks: BackgroundTasks):
    """E-Mail Integration von Flowers"""
    try:
        logger.info(f"📧 Flowers E-Mail: {email_data.betreff}")
        
        # E-Mail intelligent parsen
        parser = FlowersEmailParser()
        fin = parser.extract_fin_from_text(f"{email_data.betreff} {email_data.inhalt}")
        
        if not fin:
            raise HTTPException(status_code=400, detail="Keine FIN in E-Mail gefunden")
        
        # Prozess-Informationen extrahieren
        prozess_info = parser.extract_process_info(email_data.betreff, email_data.inhalt)
        
        if not prozess_info["prozess_typ"]:
            raise HTTPException(status_code=400, detail="Prozess-Typ konnte nicht ermittelt werden")
        
        # Verarbeitung
        result = await process_flowers_data(
            fin=fin,
            prozess_typ=prozess_info["prozess_typ"],
            status=prozess_info["status"],
            bearbeiter=prozess_info["bearbeiter"],
            prioritaet=prozess_info["prioritaet"],
            datenquelle="flowers_email",
            notizen=f"E-Mail: {email_data.betreff}"
        )
        
        if result["success"]:
            await save_process_to_bigquery(result["process_data"])
            
            return {
                "message": "Flowers E-Mail erfolgreich verarbeitet",
                "fin": fin,
                "erkannter_prozess": prozess_info["prozess_typ"],
                "erkannter_status": prozess_info["status"],
                "bearbeiter": prozess_info["bearbeiter"],
                "prioritaet": prozess_info["prioritaet"]
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"❌ Flowers E-Mail Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/integration/zapier/webhook")
async def zapier_webhook(data: ZapierWebhookData, background_tasks: BackgroundTasks):
    """Zapier Webhook Integration"""
    try:
        logger.info(f"⚡ Zapier Webhook: {data.prozess_name} für {data.fahrzeug_fin}")
        
        # Timestamp verarbeiten
        timestamp = None
        if data.original_timestamp:
            try:
                timestamp = datetime.fromisoformat(data.original_timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
        
        result = await process_flowers_data(
            fin=data.fahrzeug_fin,
            prozess_typ=data.prozess_name,
            status=data.neuer_status,
            bearbeiter=data.bearbeiter_name,
            datenquelle="zapier",
            notizen=data.notizen,
            external_timestamp=timestamp
        )
        
        if result["success"]:
            await save_process_to_bigquery(result["process_data"])
            
            return {
                "message": "Zapier Webhook erfolgreich verarbeitet",
                "fin": data.fahrzeug_fin,
                "prozess": data.prozess_name,
                "status": data.neuer_status
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"❌ Zapier Webhook Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/integration/flowers/dashboard")
async def flowers_integration_dashboard():
    """Flowers-Integration Dashboard"""
    if not bq_client:
        return {"error": "BigQuery nicht verfügbar"}
    
    try:
        # Prozesse nach Datenquelle
        query = """
        SELECT 
            datenquelle,
            COUNT(*) as anzahl_prozesse,
            COUNT(DISTINCT fin) as eindeutige_fahrzeuge,
            MAX(erstellt_am) as letzter_import
        FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
        WHERE datenquelle LIKE '%flowers%' OR datenquelle = 'zapier'
        GROUP BY datenquelle
        ORDER BY letzter_import DESC
        """
        
        sources = [dict(row) for row in bq_client.query(query)]
        
        return {
            "flowers_quellen": sources,
            "bearbeiter_mapping_count": len(BEARBEITER_MAPPING),
            "unterstützte_prozesse": ["Einkauf", "Anlieferung", "Aufbereitung", "Foto", "Werkstatt", "Verkauf"],
            "endpoints": [
                "/integration/flowers/webhook",
                "/integration/flowers/email", 
                "/integration/zapier/webhook"
            ]
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/integration/flowers/bearbeiter")
async def get_bearbeiter_mapping():
    """Bearbeiter-Mapping anzeigen"""
    return {
        "mapping": BEARBEITER_MAPPING,
        "anzahl_mappings": len(BEARBEITER_MAPPING)
    }

@app.post("/integration/flowers/bearbeiter")
async def update_bearbeiter_mapping(flowers_name: str, vollständiger_name: str):
    """Bearbeiter-Mapping hinzufügen/aktualisieren"""
    BEARBEITER_MAPPING[flowers_name] = vollständiger_name
    
    return {
        "message": "Bearbeiter-Mapping aktualisiert",
        "flowers_name": flowers_name,
        "vollständiger_name": vollständiger_name,
        "aktuelles_mapping": BEARBEITER_MAPPING
    }

# === TEST ENDPOINTS ===

@app.post("/test/flowers-webhook-sample")
async def test_flowers_webhook():
    """Test-Webhook mit realistischen Daten"""
    test_data = FlowersWebhookData(
        fahrzeug_id="WBA12345678901234",
        fin="WBA12345678901234",
        prozess="gwa",  # Wird zu "Aufbereitung" gemappt
        status="abgeschlossen",
        bearbeiter="Thomas K.",
        timestamp=datetime.now(),
        zusatz_daten={
            "werkstatt_platz": "Platz 3",
            "arbeitszeit_stunden": 2.5,
            "kosten_eur": 150.00
        }
    )
    
    return await flowers_webhook(test_data, BackgroundTasks())

@app.post("/test/flowers-email-sample")
async def test_flowers_email():
    """Test-E-Mail mit typischen Flowers-Inhalten"""
    test_email = FlowersEmailData(
        betreff="GWA abgeschlossen - BMW WBA12345678901234",
        inhalt="""
        Die Aufbereitung des Fahrzeugs wurde erfolgreich abgeschlossen.
        
        Fahrzeug: BMW 320d (WBA12345678901234)
        Bearbeiter: Thomas Weber
        Dauer: 2,5 Stunden
        
        Das Fahrzeug ist bereit für den Foto-Termin.
        Priorität: 7
        """,
        absender="system@flowers-software.de",
        empfangen_am=datetime.now()
    )
    
    return await flowers_email_integration(test_email, BackgroundTasks())

# === ORIGINAL DASHBOARD ENDPOINTS ===

@app.get("/dashboard/kpis")
async def get_dashboard_kpis():
    """Dashboard KPIs"""
    if bq_client:
        try:
            query = """
            SELECT
              COUNT(DISTINCT fin) as total_vehicles,
              COUNT(*) as total_records
            FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
            WHERE aktiv = TRUE
            """
            result = bq_client.query(query)
            rows = list(result)

            if rows:
                return dict(rows[0])

        except Exception as e:
            logger.error(f"BigQuery KPI error: {e}")

    return {
        "total_vehicles": len(vehicles_db),
        "total_processes": len(processes_db),
        "source": "memory",
    }

@app.get("/dashboard/warteschlangen")
async def get_warteschlangen():
    """Warteschlangen-Übersicht"""
    if bq_client:
        try:
            query = """
            SELECT
              prozess_typ,
              COUNT(*) as anzahl_wartend
            FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE status = 'warteschlange'
            GROUP BY prozess_typ
            ORDER BY anzahl_wartend DESC
            """
            result = bq_client.query(query)
            queues = [dict(row) for row in result]

            return {"warteschlangen": queues, "source": "bigquery"}

        except Exception as e:
            logger.error(f"BigQuery queues error: {e}")

    return {"warteschlangen": [], "source": "memory"}

@app.get("/dashboard/sla-status")
async def get_sla_status():
    """SLA-Status aller aktiven Prozesse"""
    if bq_client:
        try:
            query = """
            SELECT 
                prozess_typ,
                COUNT(*) as total,
                SUM(CASE WHEN sla_status = 'SLA_VERLETZT' THEN 1 ELSE 0 END) as verletzt,
                SUM(CASE WHEN sla_status = 'SLA_RISIKO' THEN 1 ELSE 0 END) as risiko,
                SUM(CASE WHEN sla_status = 'SLA_OK' THEN 1 ELSE 0 END) as ok
            FROM `ra-autohaus-tracker.autohaus.prozesse_sla_einfach`
            WHERE status IN ('gestartet', 'in_bearbeitung', 'warteschlange')
            GROUP BY prozess_typ
            ORDER BY 
                CASE prozess_typ 
                    WHEN 'Einkauf' THEN 1
                    WHEN 'Anlieferung' THEN 2
                    WHEN 'Aufbereitung' THEN 3
                    WHEN 'Foto' THEN 4
                    WHEN 'Werkstatt' THEN 5
                    WHEN 'Verkauf' THEN 6
                END
            """
            result = bq_client.query(query)
            sla_status = [dict(row) for row in result]
            return {
                "sla_overview": sla_status,
                "source": "bigquery"
            }
        except Exception as e:
            return {"error": str(e)}
    return {"sla_overview": [], "source": "bigquery_unavailable"}

@app.get("/dashboard/gwa-warteschlange")
async def get_gwa_warteschlange_api():
    """GWA Warteschlange über API"""
    if bq_client:
        try:
            query = """
            SELECT * FROM `ra-autohaus-tracker.autohaus.gwa_warteschlange`
            ORDER BY standzeit_tage DESC
            """
            result = bq_client.query(query)
            queue = [dict(row) for row in result]

            return {
                "gwa_warteschlange": queue,
                "anzahl": len(queue),
                "source": "bigquery",
            }

        except Exception as e:
            logger.error(f"GWA queue error: {e}")
            return {"error": str(e)}

    return {"gwa_warteschlange": [], "source": "bigquery_unavailable"}

# === ADDITIONAL ENDPOINTS FROM ORIGINAL ===

@app.post("/prozesse/create-with-status", status_code=201)
async def create_prozess_with_status(
    fin: str,
    prozess_typ: str,
    status: str = "gestartet",
    bearbeiter: Optional[str] = None,
    prioritaet: Optional[int] = 5,
    anlieferung_datum: Optional[str] = None,
    notizen: Optional[str] = None,
):
    """Prozess mit beliebigem Status erstellen"""
    try:
        prozess_id = str(uuid.uuid4())

        process_data = {
            "prozess_id": prozess_id,
            "fin": fin,
            "prozess_typ": prozess_typ,
            "status": status,
            "bearbeiter": bearbeiter,
            "prioritaet": prioritaet,
            "anlieferung_datum": anlieferung_datum,
            "start_timestamp": datetime.now(),
            "datenquelle": "api",
            "notizen": notizen,
        }

        bigquery_success = await save_process_to_bigquery(process_data)

        return {
            "message": f"Prozess mit Status '{status}' erstellt",
            "prozess_id": prozess_id,
            "fin": fin,
            "prozess_typ": prozess_typ,
            "status": status,
            "storage": "bigquery" if bigquery_success else "memory",
        }

    except Exception as e:
        logger.error(f"Error creating process with status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/prozesse/{prozess_id}/status")
async def update_prozess_status(prozess_id: str, update: ProcessUpdate):
    """Prozess-Status über Status-Update-Tabelle ändern"""
    try:
        # Aktuellen Status aus View holen
        if bq_client:
            query = """
            SELECT effektiver_status, prozess_typ, fin
            FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status`
            WHERE prozess_id = @prozess_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("prozess_id", "STRING", prozess_id)
                ]
            )
            result = bq_client.query(query, job_config=job_config)
            processes = [dict(row) for row in result]

            if not processes:
                raise HTTPException(status_code=404, detail="Prozess nicht gefunden")

            current_process = processes[0]
            alter_status = current_process["effektiver_status"]

            # Status-Update speichern
            success = await create_status_update(
                prozess_id=prozess_id,
                alter_status=alter_status,
                neuer_status=update.status,
                bearbeiter=update.bearbeiter,
                notizen=update.notizen,
            )

            if not success:
                raise HTTPException(
                    status_code=500, detail="Status-Update fehlgeschlagen"
                )

            return {
                "message": "Status erfolgreich aktualisiert",
                "prozess_id": prozess_id,
                "alter_status": alter_status,
                "neuer_status": update.status,
                "fin": current_process["fin"],
                "prozess_typ": current_process["prozess_typ"],
            }

        else:
            raise HTTPException(status_code=503, detail="BigQuery nicht verfügbar")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating process status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === INFO ENDPOINTS ===

HAUPTPROZESSE = ["Einkauf", "Anlieferung", "Aufbereitung", "Foto", "Werkstatt", "Verkauf"]
SLA_DEFINITIONEN = {
    "Einkauf": 14,
    "Anlieferung": 7, 
    "Aufbereitung": 2,
    "Foto": 3,
    "Werkstatt": 10,
    "Verkauf": 30
}

@app.get("/info/prozesse")
async def get_prozess_info():
    """6 Hauptprozesse mit SLA-Definitionen"""
    return {
        "hauptprozesse": HAUPTPROZESSE,
        "sla_tage": SLA_DEFINITIONEN,
        "flowers_mapping": {
            "transport": "Anlieferung",
            "gwa": "Aufbereitung",
            "garage": "Werkstatt",
            "fotoshooting": "Foto",
            "ankauf": "Einkauf",
            "verkauf": "Verkauf"
        }
    }

# === DEBUG ENDPOINTS ===

@app.get("/debug/bigquery-info")
async def debug_bigquery_info():
    """BigQuery Debug-Informationen"""
    if not bq_client:
        return {"error": "BigQuery Client nicht verfügbar"}

    try:
        info = {"project": bq_client.project, "location": bq_client.location}

        dataset = bq_client.get_dataset("autohaus")
        info["dataset"] = {
            "dataset_id": dataset.dataset_id,
            "location": dataset.location,
        }

        tables = list(bq_client.list_tables("autohaus"))
        info["tables"] = [table.table_id for table in tables]

        return info

    except Exception as e:
        return {"error": f"BigQuery Debug Fehler: {e}"}

@app.get("/debug/clear-memory")
async def clear_memory():
    """Memory-Storage leeren"""
    vehicles_db.clear()
    processes_db.clear()
    return {"message": "Memory-Storage geleert"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)