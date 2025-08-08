# flowers_integration.py - Flowers-Integration für main.py (Pylance-kompatibel)

import logging
import json
import uuid
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
from google.cloud import bigquery  # ✅ Direkter Import (wie in main.py)

logger = logging.getLogger(__name__)

# === MODELS FÜR FLOWERS-INTEGRATION ===

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

# === E-MAIL PARSER ===

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
        
        # Status-Erkennung (erweitert)
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
        
        # Bearbeiter extrahieren (deutsche Namen)
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
    "Hans M.": "Hans Müller",
    "Anna K.": "Anna Klein", 
    "Thomas W.": "Thomas Weber",
    "Thomas K.": "Thomas Küfner",  # Du selbst
    "Max R.": "Maximilian Reinhardt",  # Geschäftsführung
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
    
    # Fuzzy-Matching für ähnliche Namen
    flowers_lower = flowers_bearbeiter.lower()
    for flowers_key, full_name in BEARBEITER_MAPPING.items():
        if flowers_lower in flowers_key.lower() or flowers_key.lower() in flowers_lower:
            return full_name
    
    # Fallback: Originalname zurückgeben
    return flowers_bearbeiter

# === ZENTRALE VERARBEITUNGSFUNKTION ===

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
    bq_client=None
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
        
        # 3. Prozess-Daten strukturieren (kompatibel zu deinem Schema)
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
            process_data["notizen"] = f"{notizen or ''} | Zusatzdaten: {json.dumps(zusatz_daten, default=str)}"
        
        return {
            "success": True,
            "process_data": process_data,
            "fahrzeug_existiert": vehicle_exists,
            "bearbeiter_gemappt": f"{bearbeiter} -> {mapped_bearbeiter}" if bearbeiter != mapped_bearbeiter else None
        }
        
    except Exception as e:
        logger.error(f"❌ Flowers-Datenverarbeitung Fehler: {e}")
        return {"success": False, "error": str(e)}

# === FLOWERS-ENDPOINTS ===

def add_flowers_endpoints(app: FastAPI, bq_client, save_process_to_bigquery):
    """Flowers-Endpoints zu bestehender FastAPI-App hinzufügen"""
    
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
                external_timestamp=data.timestamp,
                bq_client=bq_client
            )
            
            if result["success"]:
                # In BigQuery speichern (deine bestehende Funktion nutzen)
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
                notizen=f"E-Mail: {email_data.betreff}",
                bq_client=bq_client
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
                external_timestamp=timestamp,
                bq_client=bq_client
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

    @app.post("/integration/flowers/status-update")
    async def flowers_status_update(
        fin: str,
        prozess_typ: str,
        neuer_status: str,
        bearbeiter: Optional[str] = None,
        notizen: Optional[str] = None
    ):
        """Status-Update über das bestehende Status-Update-System"""
        try:
            # Aktuellen Prozess finden
            if bq_client:
                query = """
                SELECT prozess_id, effektiver_status
                FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status`
                WHERE fin = @fin AND prozess_typ = @prozess_typ
                ORDER BY erstellt_am DESC
                LIMIT 1
                """
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("fin", "STRING", fin),
                        bigquery.ScalarQueryParameter("prozess_typ", "STRING", prozess_typ)
                    ]
                )
                result = bq_client.query(query, job_config=job_config)
                processes = [dict(row) for row in result]
                
                if not processes:
                    raise HTTPException(status_code=404, detail=f"Prozess {prozess_typ} für FIN {fin} nicht gefunden")
                
                prozess_id = processes[0]["prozess_id"]
                alter_status = processes[0]["effektiver_status"]
                
                # Status-Update in deine bestehende Tabelle
                table_id = "ra-autohaus-tracker.autohaus.prozess_status_updates"
                table = bq_client.get_table(table_id)
                
                update_row = {
                    "update_id": str(uuid.uuid4()),
                    "prozess_id": prozess_id,
                    "alter_status": alter_status,
                    "neuer_status": neuer_status,
                    "bearbeiter": resolve_bearbeiter(bearbeiter),
                    "update_timestamp": datetime.now().isoformat(),
                    "notizen": f"Flowers: {notizen}" if notizen else "Flowers Update",
                    "datenquelle": "flowers_status_update"
                }
                
                errors = bq_client.insert_rows_json(table, [update_row])
                if errors:
                    raise HTTPException(status_code=500, detail=f"BigQuery Fehler: {errors}")
                
                return {
                    "message": "Status erfolgreich aktualisiert",
                    "prozess_id": prozess_id,
                    "fin": fin,
                    "alter_status": alter_status,
                    "neuer_status": neuer_status,
                    "bearbeiter": resolve_bearbeiter(bearbeiter)
                }
                
        except Exception as e:
            logger.error(f"❌ Flowers Status-Update Fehler: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/integration/flowers/dashboard")
    async def flowers_integration_dashboard():
        """Flowers-Integration Dashboard"""
        if not bq_client:
            return {"error": "BigQuery nicht verfügbar"}
        
        try:
            # Prozesse nach Datenquelle
            query1 = """
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
            
            sources = [dict(row) for row in bq_client.query(query1)]
            
            return {
                "flowers_quellen": sources,
                "bearbeiter_mapping_count": len(BEARBEITER_MAPPING),
                "unterstützte_prozesse": ["Einkauf", "Anlieferung", "Aufbereitung", "Foto", "Werkstatt", "Verkauf"]
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

    return app

