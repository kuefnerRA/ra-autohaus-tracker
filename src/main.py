import importlib
import sys
import logging
import os
import uuid
import json
import re
import imaplib
import email.message 
import email.utils

from email.header import decode_header
from email import message_from_bytes
from email.message import Message

from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from datetime import date, datetime
from typing import Any, Dict, Optional, List, Tuple

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field, validator

# .env Datei laden
from dotenv import load_dotenv
load_dotenv()

from src.handlers.flowers_handler import FlowersHandler

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

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

# Handler-Instanz erstellen (NACH bq_client)
if BIGQUERY_AVAILABLE and bq_client:
    flowers_handler = FlowersHandler(bigquery_service=None)  # Vorerst None
else:
    flowers_handler = FlowersHandler(bigquery_service=None)


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
    
    from pydantic import field_validator

    @field_validator('prozess')
    @classmethod
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
        # Erst versuchen mit "FIN:" Label
        fin_pattern_labeled = r'FIN:\s*([A-Z0-9]{15,17})'
        matches = re.findall(fin_pattern_labeled, text.upper(), re.IGNORECASE)
        if matches:
            return matches[0]
        
        # Fallback: Nackte FIN ohne Label
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
    
    @staticmethod
    def extract_vehicle_data(email_content: str) -> Dict[str, Any]:
        """Extrahiert Fahrzeugdaten aus E-Mail-Inhalt"""
        vehicle_data = {}
        
        # Marke extrahieren
        marke_pattern = re.compile(r'Marke:\s*([^\n\r]+)', re.IGNORECASE)
        marke_match = marke_pattern.search(email_content)
        if marke_match:
            vehicle_data['marke'] = marke_match.group(1).strip()
        
        # Farbe extrahieren  
        farbe_pattern = re.compile(r'Farbe:\s*([^\n\r]+)', re.IGNORECASE)
        farbe_match = farbe_pattern.search(email_content)
        if farbe_match:
            vehicle_data['farbe'] = farbe_match.group(1).strip()
        
        # Modell extrahieren (optional)
        modell_pattern = re.compile(r'Modell:\s*([^\n\r]+)', re.IGNORECASE)
        modell_match = modell_pattern.search(email_content)
        if modell_match:
            vehicle_data['modell'] = modell_match.group(1).strip()
        
        # Baujahr extrahieren (optional)
        baujahr_pattern = re.compile(r'Baujahr:\s*(\d{4})', re.IGNORECASE)
        baujahr_match = baujahr_pattern.search(email_content)
        if baujahr_match:
            vehicle_data['baujahr'] = int(baujahr_match.group(1))
        
        datum_erstzulassung_pattern = re.compile(r'(?:Datum\s*Erstzulassung|Erstzulassung):\s*(\d{2}\.\d{2}\.\d{4})', re.IGNORECASE)
        datum_match = datum_erstzulassung_pattern.search(email_content)
        if datum_match:
            try:
                vehicle_data['datum_erstzulassung'] = datetime.strptime(datum_match.group(1), '%d.%m.%Y').date()
            except ValueError:
                pass
        
        antriebsart_pattern = re.compile(r'Antriebsart:\s*([^\n\r]+)', re.IGNORECASE)
        antriebsart_match = antriebsart_pattern.search(email_content)
        if antriebsart_match:
            vehicle_data['antriebsart'] = antriebsart_match.group(1).strip()
        
        kw_leistung_pattern = re.compile(r'(?:KW-Leistung|KW|Leistung):\s*(\d+)', re.IGNORECASE)
        kw_match = kw_leistung_pattern.search(email_content)
        if kw_match:
            vehicle_data['kw_leistung'] = int(kw_match.group(1))
        
        km_stand_pattern = re.compile(r'(?:KM-Stand|KM|Kilometerstand):\s*([\d.]+)', re.IGNORECASE)
        km_match = km_stand_pattern.search(email_content)
        if km_match:
            km_value = km_match.group(1).replace('.', '')
            vehicle_data['km_stand'] = int(km_value)
        
        schluessel_pattern = re.compile(r'(?:Anzahl\s*Fahrzeugschlüssel|Schlüssel):\s*(\d+)', re.IGNORECASE)
        schluessel_match = schluessel_pattern.search(email_content)
        if schluessel_match:
            vehicle_data['anzahl_fahrzeugschluessel'] = int(schluessel_match.group(1))
        
        bereifung_pattern = re.compile(r'Bereifungsart:\s*([^\n\r]+)', re.IGNORECASE)
        bereifung_match = bereifung_pattern.search(email_content)
        if bereifung_match:
            vehicle_data['bereifungsart'] = bereifung_match.group(1).strip()
        
        vorhalter_pattern = re.compile(r'(?:Anzahl\s*Vorhalter|Vorhalter):\s*(\d+)', re.IGNORECASE)
        vorhalter_match = vorhalter_pattern.search(email_content)
        if vorhalter_match:
            vehicle_data['anzahl_vorhalter'] = int(vorhalter_match.group(1))
        
        ek_pattern = re.compile(r'(?:EK\s*netto|EK):\s*([\d.,]+)', re.IGNORECASE)
        ek_match = ek_pattern.search(email_content)
        if ek_match:
            ek_value = ek_match.group(1).replace('.', '').replace(',', '.')
            vehicle_data['ek_netto'] = float(ek_value)
        
        besteuerung_pattern = re.compile(r'Besteuerungsart:\s*([^\n\r]+)', re.IGNORECASE)
        besteuerung_match = besteuerung_pattern.search(email_content)
        if besteuerung_match:
            vehicle_data['besteuerungsart'] = besteuerung_match.group(1).strip()

        return vehicle_data

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

        datum_erstzulassung = vehicle_data.get("datum_erstzulassung")
        datum_erstzulassung_iso = datum_erstzulassung.isoformat() if datum_erstzulassung else None


        row = {
            "fin": vehicle_data["fin"],
            "marke": vehicle_data["marke"],
            "modell": vehicle_data.get("modell", "Unbekannt"),
            "antriebsart": vehicle_data.get("antriebsart", "Unbekannt"),
            "farbe": vehicle_data.get("farbe", "Unbekannt"),
            "baujahr": vehicle_data.get("baujahr"),
            "ersterfassung_datum": now_iso,
            "aktiv": True,
            "erstellt_aus_email": vehicle_data.get("erstellt_aus_email", False),
            "datenquelle_fahrzeug": vehicle_data.get("datenquelle_fahrzeug", "api"),
            "datum_erstzulassung": datum_erstzulassung_iso,
            "kw_leistung": vehicle_data.get("kw_leistung"),
            "km_stand": vehicle_data.get("km_stand"),
            "anzahl_fahrzeugschluessel": vehicle_data.get("anzahl_fahrzeugschluessel"),
            "bereifungsart": vehicle_data.get("bereifungsart", "Unbekannt"),
            "anzahl_vorhalter": vehicle_data.get("anzahl_vorhalter"),
            "ek_netto": vehicle_data.get("ek_netto"),
            "besteuerungsart": vehicle_data.get("besteuerungsart", "Unbekannt")
        }

        row = {k: v for k, v in row.items() if v is not None}

        errors = bq_client.insert_rows_json(table, [row])
        if errors:
            logger.error(f"BigQuery errors: {errors}")
            return False

        logger.info(f"Vehicle saved to BigQuery: {vehicle_data['fin']}")
        return True

    except Exception as e:
        logger.error(f"BigQuery save error: {e}")
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
    external_timestamp: Optional[datetime] = None,
    # NEUE PARAMETER für Fahrzeugdaten
    marke: Optional[str] = None,
    farbe: Optional[str] = None,
    modell: Optional[str] = None,
    baujahr: Optional[int] = None,
    datum_erstzulassung: Optional[date] = None,
    antriebsart: Optional[str] = None,
    kw_leistung: Optional[int] = None,
    km_stand: Optional[int] = None,
    anzahl_fahrzeugschluessel: Optional[int] = None,
    bereifungsart: Optional[str] = None,
    anzahl_vorhalter: Optional[int] = None,
    ek_netto: Optional[float] = None,
    besteuerungsart: Optional[str] = None
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
        
        if not vehicle_exists and (marke or farbe):
            logger.info(f"Erstelle Fahrzeug automatisch: {fin}")
            
            # Fahrzeugdaten aus E-Mail-Informationen ableiten
            vehicle_data = {
                "fin": fin,
                "marke": marke or "Unbekannt",
                "modell": modell or "Unbekannt", 
                "antriebsart": antriebsart or "Unbekannt",
                "farbe": farbe or "Unbekannt",
                "baujahr": baujahr,
                # NEUE Felder hinzufügen
                "datum_erstzulassung": datum_erstzulassung,
                "kw_leistung": kw_leistung,
                "km_stand": km_stand,
                "anzahl_fahrzeugschluessel": anzahl_fahrzeugschluessel,
                "bereifungsart": bereifungsart or "Unbekannt",
                "anzahl_vorhalter": anzahl_vorhalter,
                "ek_netto": ek_netto,
                "besteuerungsart": besteuerungsart or "Unbekannt",
                "erstellt_aus_email": True,
                "datenquelle_fahrzeug": datenquelle
            }
            
            # Fahrzeug in BigQuery erstellen
            vehicle_created = await save_vehicle_to_bigquery(vehicle_data)
            
            if vehicle_created:
                logger.info(f"Fahrzeug automatisch erstellt: {fin} ({marke})")
                vehicle_exists = True
            else:
                logger.warning(f"Automatische Fahrzeug-Erstellung fehlgeschlagen: {fin}")
        
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
            "fahrzeug_automatisch_erstellt": not vehicle_exists and (marke or farbe),  # NEUE ZEILE
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

        # HIER Handler verwenden statt direkter Wert
        normalized_prozess = flowers_handler.normalize_prozess_typ(data.prozess)


        if not fin:
            raise HTTPException(status_code=400, detail="FIN konnte nicht ermittelt werden")
        
        # Daten verarbeiten
        result = await process_flowers_data(
            fin=fin,
            prozess_typ=normalized_prozess,
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
                "prozess": normalized_prozess,
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
        fahrzeug_daten = parser.extract_vehicle_data(email_data.inhalt)
        
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
            notizen=f"E-Mail: {email_data.betreff}",
            # Bestehende Parameter
            marke=fahrzeug_daten.get("marke"),
            farbe=fahrzeug_daten.get("farbe"),
            modell=fahrzeug_daten.get("modell"),
            baujahr=fahrzeug_daten.get("baujahr"),
            # NEUE Parameter hinzufügen
            datum_erstzulassung=fahrzeug_daten.get("datum_erstzulassung"),
            antriebsart=fahrzeug_daten.get("antriebsart"),
            kw_leistung=fahrzeug_daten.get("kw_leistung"),
            km_stand=fahrzeug_daten.get("km_stand"),
            anzahl_fahrzeugschluessel=fahrzeug_daten.get("anzahl_fahrzeugschluessel"),
            bereifungsart=fahrzeug_daten.get("bereifungsart"),
            anzahl_vorhalter=fahrzeug_daten.get("anzahl_vorhalter"),
            ek_netto=fahrzeug_daten.get("ek_netto"),
            besteuerungsart=fahrzeug_daten.get("besteuerungsart")
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
        
        # HIER Handler verwenden statt direkter Wert
        normalized_prozess = flowers_handler.normalize_prozess_typ(data.prozess_name)

        result = await process_flowers_data(
            fin=data.fahrzeug_fin,
            prozess_typ=normalized_prozess,
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
                "prozess": normalized_prozess,
                "status": data.neuer_status
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"❌ Zapier Webhook Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/integration/zapier/debug")
async def zapier_debug_webhook(request: Request):
    """Debug-Endpoint für Zapier JSON-Format"""
    try:
        body = await request.body()
        json_data = await request.json()
        
        logger.info(f"Zapier Debug - Raw Body: {body}")
        logger.info(f"Zapier Debug - JSON: {json_data}")
        
        return {
            "status": "debug_success",
            "received_data": json_data,
            "data_type": type(json_data).__name__
        }
    except Exception as e:
        logger.error(f"Zapier Debug Error: {e}")
        return {"status": "debug_error", "error": str(e)}
    
@app.post("/integration/zapier/flexible")
async def zapier_flexible_webhook(request: Request, background_tasks: BackgroundTasks):
    """Flexibler Zapier Webhook der jedes JSON akzeptiert"""
    try:
        json_data = await request.json()
        logger.info(f"Flexible Zapier Webhook: {json_data}")
        
        # FIN extrahieren (verschiedene mögliche Feldnamen)
        fin = (json_data.get('fahrzeug_fin') or 
               json_data.get('fin') or 
               json_data.get('vehicle_fin') or 
               json_data.get('FIN'))
        
        # Prozess extrahieren
        prozess = (json_data.get('prozess_name') or 
                  json_data.get('prozess') or 
                  json_data.get('process_name'))
        
        # Status extrahieren  
        status = (json_data.get('neuer_status') or 
                 json_data.get('status') or 
                 json_data.get('new_status'))
        
        logger.info(f"🔍 Extracted values: fin='{fin}', prozess='{prozess}', status='{status}'")
        
        if not fin or not prozess or not status:
            missing_fields = []
            if not fin: missing_fields.append("fin")
            if not prozess: missing_fields.append("prozess")
            if not status: missing_fields.append("status")
            
            logger.warning(f"🚫 Missing required fields: {missing_fields}")
            return {
                "status": "error",
                "message": "Required fields missing",
                "missing_fields": missing_fields,
                "received_fields": list(json_data.keys())
            }
        
        logger.info(f"✅ All fields found, processing...")
        
        # Normalisierte Verarbeitung
        normalized_prozess = flowers_handler.normalize_prozess_typ(prozess)
        
        result = await process_flowers_data(
            fin=fin,
            prozess_typ=normalized_prozess,
            status=status,
            bearbeiter=json_data.get('bearbeiter_name') or json_data.get('bearbeiter'),
            datenquelle="zapier_flexible"
        )
        
        if result["success"]:
            await save_process_to_bigquery(result["process_data"])
            
        return {
            "status": "success",
            "fin": fin,
            "prozess": normalized_prozess,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Flexible Zapier Webhook Error: {e}")
        return {"status": "error", "message": str(e)}



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

    # Nach den bestehenden Klassen hinzufügen:

class FlowersEmailProcessor:
    """Erweiterte E-Mail-Verarbeitung für Flowers Integration"""
    
    def __init__(self):
        # E-Mail-Konfiguration aus Umgebungsvariablen
        self.imap_server = os.getenv('EMAIL_IMAP_SERVER', 'outlook.office365.com')
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.flowers_sender = os.getenv('FLOWERS_SENDER_EMAIL', '')
        
        # Regex-Muster für erweiterte E-Mail-Parsing
        self.fin_pattern = re.compile(r'FIN:\s*([A-Z0-9]{15,17})', re.IGNORECASE)
        self.marke_pattern = re.compile(r'Marke:\s*([^\n\r]+)', re.IGNORECASE)
        self.farbe_pattern = re.compile(r'Farbe:\s*([^\n\r]+)', re.IGNORECASE)
        self.bearbeiter_pattern = re.compile(r'Bearbeiter:\s*([^\n\r]+)', re.IGNORECASE)
        
        # Betreff-Parsing: "GWA gestartet" → ('GWA', 'gestartet')
        self.subject_pattern = re.compile(r'^([A-Za-z0-9_\-\s]+)\s+([A-Za-z0-9_\-\s]+)$')
    
    def connect_to_email(self):
        """Verbindung zum E-Mail-Server herstellen"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(str(self.email_user), str(self.email_password))
            mail.select('inbox')
            logger.info(f"E-Mail-Verbindung zu {self.imap_server} erfolgreich")
            return mail
        except Exception as e:
            logger.error(f"E-Mail-Verbindung fehlgeschlagen: {e}")
            raise
    
    def parse_subject_enhanced(self, subject: str): 
        """Erweiterte Betreffzeilen-Analyse: 'GWA gestartet' → ('Aufbereitung', 'gestartet')"""
        try:
            # Betreff dekodieren
            decoded_subject = ""
            for part, encoding in decode_header(subject):
                if isinstance(part, bytes):
                    decoded_subject += part.decode(encoding or 'utf-8')
                elif isinstance(part, str):
                    decoded_subject += part
                else:
                    decoded_subject += str(part)
            
            # Prozess und Status extrahieren
            match = self.subject_pattern.match(decoded_subject.strip())
            if match:
                raw_prozess = match.group(1).strip()
                status = match.group(2).strip()
                
                # Flowers-Handler für Prozess-Normalisierung nutzen
                normalized_prozess = flowers_handler.normalize_prozess_typ(raw_prozess)
                
                return normalized_prozess, status
            else:
                logger.warning(f"Betreff konnte nicht geparst werden: {decoded_subject}")
                return "", ""
                
        except Exception as e:
            logger.error(f"Fehler beim Parsen des Betreffs '{subject}': {e}")
            return "", ""
    
    def parse_email_body_enhanced(self, body: str) -> Dict[str, str]:
        """Erweiterte Body-Analyse mit allen Flowers-Feldern"""
        parsed_data = {}
        
        # HTML entfernen falls vorhanden
        if '<html>' in body.lower() or '<body>' in body.lower():
            soup = BeautifulSoup(body, 'html.parser')
            body = soup.get_text()
        
        # FIN extrahieren
        fin_match = self.fin_pattern.search(body)
        if fin_match:
            parsed_data['fin'] = fin_match.group(1).strip()
        
        # Marke extrahieren
        marke_match = self.marke_pattern.search(body)
        if marke_match:
            parsed_data['marke'] = marke_match.group(1).strip()
        
        # Farbe extrahieren
        farbe_match = self.farbe_pattern.search(body)
        if farbe_match:
            parsed_data['farbe'] = farbe_match.group(1).strip()
        
        # Bearbeiter extrahieren (falls vorhanden)
        bearbeiter_match = self.bearbeiter_pattern.search(body)
        if bearbeiter_match:
            parsed_data['bearbeiter'] = bearbeiter_match.group(1).strip()
        
        return parsed_data
    
    def process_unread_emails(self) -> List[Dict[str, Any]]:
        """Ungelesene E-Mails verarbeiten und parsen"""
        processed_emails = []
        
        try:
            mail = self.connect_to_email()
            
            # Nach ungelesenen E-Mails suchen
            status, messages = mail.search(None, 'UNSEEN')
            
            if status != 'OK' or not messages or messages[0] is None:
                logger.error("Fehler beim Suchen nach E-Mails")
                return processed_emails
            
            ids_raw = messages[0].decode() if isinstance(messages[0], (bytes, bytearray)) else (messages[0] or "")
            email_ids = ids_raw.split()
            logger.info(f"{len(email_ids)} ungelesene E-Mails gefunden")
            
            for email_id in email_ids:
                try:
                    # E-Mail abrufen
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK' or not msg_data:
                        continue

                    # Robust extrahieren, ohne gefährliche Indexe/Längen auf untypisierten Objekten
                    raw_email: Optional[bytes] = None

                    first_part = msg_data[0]
                    # IMAP liefert normalerweise eine Tuple-Struktur (header, bytes)
                    if isinstance(first_part, (tuple, list)):
                        if len(first_part) >= 2 and isinstance(first_part[1], (bytes, bytearray)):
                            raw_email = bytes(first_part[1])
                    elif isinstance(first_part, (bytes, bytearray)):
                        # manche Server-Implementierungen liefern direkt bytes
                        raw_email = bytes(first_part)

                    if raw_email is None:
                        logger.warning("Kein RAW E-Mail-Body gefunden – übersprungen")
                        continue


                    
                    # HIER DEBUG-ZEILE HINZUFÜGEN:
                
                    subject = msg['subject'] or ""
                    sender = msg['from'] or ""
                    logger.info(f"🔍 DEBUG: E-Mail Details - Betreff: '{subject}', Absender: '{sender}'")     
                    logger.info(f"🔍 DEBUG: E-Mail Details - Betreff: '{subject}', Absender: '{sender}'")

                    # NEUE DEBUG-ZEILEN HINZUFÜGEN:
                    logger.info(f"🔍 DEBUG: Flowers sender filter: '{self.flowers_sender}'")

                    # Absender-Filter prüfen
                    if self.flowers_sender and self.flowers_sender not in sender.lower():
                        logger.info(f"🔍 DEBUG: E-Mail übersprungen - Absender-Filter")
                        continue

                    # Betreff parsen
                    prozess_name, status_value = self.parse_subject_enhanced(subject)
                    logger.info(f"🔍 DEBUG: Betreff geparst - Prozess: '{prozess_name}', Status: '{status_value}'")

                    if not prozess_name:
                        logger.info(f"🔍 DEBUG: E-Mail übersprungen - Ungültiger Betreff")
                        continue            

                    # E-Mail-Objekt erstellen
                    from email import message_from_bytes
                    from email.message import Message

                    raw_email: Optional[bytes] = None

                    if msg_data and isinstance(msg_data[0], (tuple, list)):
                        first = msg_data[0]
                        if len(first) > 1 and isinstance(first[1], (bytes, bytearray)):
                            raw_email = bytes(first[1])
                    elif msg_data and isinstance(msg_data[0], (bytes, bytearray)):
                        # manche IMAP-Implementierungen liefern direkt bytes
                        raw_email = bytes(msg_data[0])

                    if raw_email is None:
                        logger.warning("Kein RAW E-Mail-Body gefunden – übersprungen")
                        continue

                    msg: Message = message_from_bytes(raw_email)
                    
                    # Basic-Informationen extrahieren
                    subject = msg['subject'] or ""
                    sender = msg['from'] or ""
                    
                    # Absender-Filter (optional)
                    if self.flowers_sender and self.flowers_sender not in sender.lower():
                        continue  # Nicht von Flowers
                    
                    # Betreff parsen
                    prozess_name, status_value = self.parse_subject_enhanced(subject)
                    
                    if not prozess_name:
                        logger.warning(f"Ungültiger Betreff übersprungen: {subject}")
                        continue
                    
                    # Body extrahieren
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                payload = part.get_payload(decode=True)
                                if isinstance(payload, (bytes, bytearray)):
                                    body = payload.decode('utf-8', errors='ignore')
                                elif isinstance(payload, str):
                                    body = payload
                                else:
                                    body = ""
                                break
                    else:
                        payload = msg.get_payload(decode=True)
                        if isinstance(payload, (bytes, bytearray)):
                            body = payload.decode('utf-8', errors='ignore')
                        elif isinstance(payload, str):
                            body = payload
                        else:
                            body = ""
                    
                    # Body parsen
                    body_data = self.parse_email_body_enhanced(body)
                    
                    # FIN ist Pflichtfeld
                    if 'fin' not in body_data:
                        logger.warning(f"Keine FIN in E-Mail gefunden: {subject}")
                        continue
                    
                    # Timestamp extrahieren
                    email_date = email.utils.parsedate_tz(msg['date'])
                    timestamp = datetime.fromtimestamp(email.utils.mktime_tz(email_date)) if email_date else datetime.now()
                    
                    # FlowersEmailData-kompatible Struktur erstellen
                    processed_email = {
                        'betreff': subject,
                        'inhalt': body,
                        'absender': sender,
                        'empfangen_am': timestamp,
                        # Erweiterte Daten
                        'fin': body_data['fin'],
                        'prozess_name': prozess_name,
                        'status': status_value,
                        'bearbeiter': body_data.get('bearbeiter'),
                        'marke': body_data.get('marke'),
                        'farbe': body_data.get('farbe')
                    }
                    
                    processed_emails.append(processed_email)
                    
                    # E-Mail als gelesen markieren
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    
                    logger.info(f"E-Mail verarbeitet: {body_data['fin']} - {prozess_name} - {status_value}")
                    
                except Exception as e:
                    logger.error(f"Fehler beim Verarbeiten der E-Mail {email_id}: {e}")
                    continue
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"Fehler beim E-Mail-Abruf: {e}")
        
        return processed_emails

# Globale Instanz erstellen
email_processor = FlowersEmailProcessor()

# Scheduler für automatische E-Mail-Verarbeitung
scheduler = AsyncIOScheduler()

async def scheduled_email_processing():
    """Scheduled Task für automatische E-Mail-Verarbeitung"""
    try:
        processed_emails = email_processor.process_unread_emails()
        
        if not processed_emails:
            logger.info("Keine neuen Flowers E-Mails gefunden")
            return
        
        # Jede E-Mail über bestehenden Endpoint verarbeiten
        for email_data in processed_emails:
            try:
                # FlowersEmailData-Objekt erstellen
                flowers_email = FlowersEmailData(
                    betreff=email_data['betreff'],
                    inhalt=email_data['inhalt'],
                    absender=email_data['absender'],
                    empfangen_am=email_data['empfangen_am']
                )
                
                # Über bestehenden Endpoint verarbeiten
                result = await flowers_email_integration(flowers_email, BackgroundTasks())
                logger.info(f"E-Mail automatisch verarbeitet: {email_data['fin']} - {result}")
                
            except Exception as e:
                logger.error(f"Fehler bei automatischer E-Mail-Verarbeitung für {email_data.get('fin', 'unknown')}: {e}")
        
        logger.info(f"🔄 Scheduled E-Mail-Verarbeitung abgeschlossen: {len(processed_emails)} E-Mails")
        
    except Exception as e:
        logger.error(f"Fehler bei scheduled E-Mail-Verarbeitung: {e}")

# Startup/Shutdown Events ergänzen (nach den bestehenden @app.on_event hinzufügen)
from contextlib import asynccontextmanager

# Debug: Vereinfachte Lifespan-Implementation
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - vereinfacht ohne E-Mail-Scheduler
    logger.info("App startup")
    yield
    # Shutdown
    logger.info("App shutdown")

# === NEUE E-MAIL ENDPOINTS ===

@app.post("/integration/email/process-inbox")
async def process_inbox_manual():
    """
    Manuelle E-Mail-Verarbeitung aus Posteingang
    
    Verarbeitet alle ungelesenen Flowers-E-Mails
    """
    try:
        processed_emails = email_processor.process_unread_emails()
        
        if not processed_emails:
            return {
                "status": "success",
                "message": "Keine neuen E-Mails gefunden",
                "processed_count": 0
            }
        
        successful_count = 0
        errors = []
        
        # Jede E-Mail über bestehenden flowers_email_integration verarbeiten
        for email_data in processed_emails:
            try:
                flowers_email = FlowersEmailData(
                    betreff=email_data['betreff'],
                    inhalt=email_data['inhalt'], 
                    absender=email_data['absender'],
                    empfangen_am=email_data['empfangen_am']
                )
                
                result = await flowers_email_integration(flowers_email, BackgroundTasks())
                successful_count += 1
                
            except Exception as e:
                errors.append({
                    'fin': email_data.get('fin', 'unknown'),
                    'error': str(e)
                })
        
        return {
            "status": "success" if successful_count > 0 else "partial_error",
            "message": f"{successful_count} E-Mails erfolgreich verarbeitet",
            "processed_count": successful_count,
            "total_found": len(processed_emails),
            "errors": errors,
            "processed_emails": [
                {
                    'fin': email.get('fin'),
                    'prozess': email.get('prozess_name'),
                    'status': email.get('status'),
                    'bearbeiter': email.get('bearbeiter')
                }
                for email in processed_emails
            ]
        }
        
    except Exception as e:
        logger.error(f"Fehler bei manueller Posteingang-Verarbeitung: {e}")
        return {
            "status": "error",
            "message": f"Fehler beim Verarbeiten des Posteingangs: {str(e)}",
            "processed_count": 0
        }

@app.get("/integration/email/connection-test")
async def test_email_connection():
    """
    E-Mail-Verbindung testen
    """
    try:
        mail = email_processor.connect_to_email()
        
        # Posteingang-Info abrufen
        status, message_count = mail.select('inbox')
        total_messages = 0
        if status == 'OK' and message_count and message_count[0] is not None:
            total_messages = int((message_count[0].decode() or "0"))

        status, unread_messages = mail.search(None, 'UNSEEN')
        unread_count = 0
        if status == 'OK' and unread_messages and unread_messages[0]:
            unread_ids = (unread_messages[0].decode() or "").split()
            unread_count = len(unread_ids)
        
        mail.close()
        mail.logout()
        
        return {
            "status": "success",
            "connection": "OK",
            "server": email_processor.imap_server,
            "user": email_processor.email_user,
            "total_messages": total_messages,
            "unread_messages": unread_count,
            "scheduler_running": scheduler.running
        }
        
    except Exception as e:
        return {
            "status": "error",
            "connection": "FEHLER",
            "error_message": str(e),
            "server": email_processor.imap_server,
            "user": email_processor.email_user
        }

@app.post("/integration/email/test-parsing")
async def test_email_parsing_new(test_data: dict):
    """
    E-Mail-Parsing mit Ihrem Format testen
    
    Erwartet: {
        "subject": "GWA gestartet", 
        "body": "FIN: WAUZZZ8K3FA17TEST\\nMarke: Jeep\\nFarbe: Arablau Kristalleffekt"
    }
    """
    try:
        subject = test_data.get('subject', '')
        body = test_data.get('body', '')
        
        # Betreff parsen
        prozess_name, status = email_processor.parse_subject_enhanced(subject)
        
        # Body parsen
        body_data = email_processor.parse_email_body_enhanced(body)
        
        # Bearbeiter-Mapping testen
        mapped_bearbeiter = resolve_bearbeiter(body_data.get('bearbeiter'))
        
        return {
            "status": "success",
            "original_subject": subject,
            "original_body": body,
            "parsed_result": {
                "prozess_name": prozess_name,
                "status": status,
                "fin": body_data.get('fin'),
                "marke": body_data.get('marke'),
                "farbe": body_data.get('farbe'),
                "bearbeiter": body_data.get('bearbeiter'),
                "mapped_bearbeiter": mapped_bearbeiter
            },
            "ready_for_processing": bool(prozess_name and body_data.get('fin'))
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Parsing-Fehler: {str(e)}"
        }

# Debug-Endpoint für Scheduler-Status
@app.get("/integration/email/scheduler-status")
async def get_scheduler_status():
    """E-Mail-Scheduler Status abrufen"""
    try:
        return {
            "scheduler_running": scheduler.running,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in scheduler.get_jobs()
            ],
            "email_config": {
                "server": email_processor.imap_server,
                "user": email_processor.email_user,
                "credentials_available": bool(email_processor.email_user and email_processor.email_password)
            }
        }
    except Exception as e:
        return {"error": str(e)}

