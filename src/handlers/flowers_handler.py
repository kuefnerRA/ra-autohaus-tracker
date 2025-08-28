# src/handlers/flowers_handler.py
import re
import uuid
import logging
from datetime import datetime, date
from typing import Dict, Optional, Any, List, Union
from email.mime.text import MIMEText
import json

logger = logging.getLogger(__name__)


class FlowersHandler:
    """Handler für alle Flowers-Datenquellen: E-Mail, Webhook, Zapier"""
    
    def __init__(self, bigquery_service=None):
        self.bigquery_service = bigquery_service
        
        # Prozesstyp-Mapping - 6 Hauptprozesse mit festen Schlüsselbegriffen
        self.process_mapping = {
            # 6 Standard-Hauptprozesse (bestehend)
            'einkauf': 'Einkauf',
            'anlieferung': 'Anlieferung', 
            'aufbereitung': 'Aufbereitung',
            'foto': 'Foto',
            'werkstatt': 'Werkstatt',
            'verkauf': 'Verkauf',
            
            # Flowers-Legacy-Begriffe hinzufügen
            'gwa': 'Aufbereitung',           
            'garage': 'Werkstatt',          
            'fotoshooting': 'Foto',         
            'transport': 'Anlieferung',     
            'ankauf': 'Einkauf',
            '(0) Start Fahrzeugaufbereitung' : 'Aufbereitung',
            '(4.0) Werkstattplanung' : 'Werkstatt',
            '(1) DA Fahrzeuganlage' : 'Einkauf'       #  
        }
        
        # E-Mail-Patterns für Flowers
        self.email_patterns = {
            # Alte Patterns (behalten für bestehende E-Mail-Formate)
            'prozess_gestartet': r'Fahrzeug\s+(\w{17})\s+-\s+(\w+)\s+gestartet\s+von\s+(.+?)(?:\n|$)',
            'prozess_abgeschlossen': r'Fahrzeug\s+(\w{17})\s+-\s+(\w+)\s+abgeschlossen\s+von\s+(.+?)(?:\n|$)',
            'warteschlange': r'Fahrzeug\s+(\w{17})\s+wartet\s+auf\s+(\w+)\s+-\s+Priorität\s+(\d+)',
            'transport_info': r'Transport:\s+FIN\s+(\w{17})\s+von\s+(.+?)\s+nach\s+(.+?)\s+am\s+(\d{2}\.\d{2}\.\d{4})',
            'aufbereitung_info': r'Aufbereitung:\s+(\w{17})\s+-\s+(.+?)\s+zugewiesen\s+an\s+(.+?)\s+am\s+(\d{2}\.\d{2}\.\d{4})',
            'werkstatt_info': r'GWA:\s+(\w{17})\s+-\s+(.+?)\s+zugewiesen\s+an\s+(.+?)\s+am\s+(\d{2}\.\d{2}\.\d{4})',
            'foto_info': r'Foto:\s+(\w{17})\s+-\s+(\w+)\s+Qualität\s+durch\s+(.+)',
            'status_update': r'Status:\s+(\w{17})\s+(\w+)\s+->\s+(\w+)\s+durch\s+(.+)',
            
            # NEUE PATTERNS für einfache E-Mail-Formate (Ihre Test-E-Mails)
            'simple_process_started': r'([A-Za-z0-9_\-\s]+)\s+(gestartet|started).*?FIN:\s*([A-Z0-9]{15,17})',
            'simple_process_completed': r'([A-Za-z0-9_\-\s]+)\s+(abgeschlossen|completed|fertig).*?FIN:\s*([A-Z0-9]{15,17})',
            'simple_process_paused': r'([A-Za-z0-9_\-\s]+)\s+(pausiert|paused|gestoppt).*?FIN:\s*([A-Z0-9]{15,17})',
            'simple_process_queued': r'([A-Za-z0-9_\-\s]+)\s+(warteschlange|queued|eingeplant).*?FIN:\s*([A-Z0-9]{15,17})',
            
            # Erweiterte Patterns mit Bearbeiter-Information (falls verfügbar)
            'simple_process_started_with_worker': r'([A-Za-z0-9_\-\s]+)\s+(gestartet|started).*?FIN:\s*([A-Z0-9]{15,17}).*?Bearbeiter:\s*([^\n\r]+)',
            'simple_process_completed_with_worker': r'([A-Za-z0-9_\-\s]+)\s+(abgeschlossen|completed|fertig).*?FIN:\s*([A-Z0-9]{15,17}).*?Bearbeiter:\s*([^\n\r]+)',
        }


    def normalize_prozess_typ(self, prozess_input: str) -> str:
        """Normalisiert Prozesstyp auf 6 Hauptprozesse (zentrale Methode)"""
        normalized = self.process_mapping.get(prozess_input.lower(), prozess_input)
        logger.debug(f"Prozess-Mapping: '{prozess_input}' → '{normalized}'")
        return normalized
    
    async def parse_flowers_email(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parst Flowers E-Mail und extrahiert Fahrzeug- und Prozessdaten"""
        try:
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            sender = email_data.get('sender', 'flowers@system')
            
            logger.info(f"📧 Parsing Flowers email: {subject}")
            
            actions = []
            email_content = f"{subject}\n{body}"
            
            for pattern_name, pattern in self.email_patterns.items():
                matches = re.finditer(pattern, email_content, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    action = self._create_action_from_match(pattern_name, match, sender)
                    if action:
                        actions.append(action)
            
            logger.info(f"✅ Extracted {len(actions)} actions from email")
            return actions
            
        except Exception as e:
            logger.error(f"❌ Email parsing failed: {e}")
            return []

    def _create_action_from_match(self, pattern_name: str, match: re.Match, sender: str) -> Optional[Dict[str, Any]]:
        """Erstellt Aktionen basierend auf E-Mail-Pattern-Matches"""
        try:
            # BESTEHENDE PATTERN-BEHANDLUNG (nicht ändern)
            if pattern_name == 'prozess_gestartet':
                fin, prozess_typ, bearbeiter = match.groups()
                normalized_typ = self.process_mapping.get(prozess_typ.lower())
                if not normalized_typ:
                    logger.warning(f"Unbekannter Prozesstyp: {prozess_typ}")
                    return None

                return {
                    "action": "start_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": normalized_typ,
                        "bearbeiter": bearbeiter.strip(),
                        "status": "gestartet",
                        "datenquelle": "flowers_email"
                    }
                }

            elif pattern_name == 'prozess_abgeschlossen':
                fin, prozess_typ, bearbeiter = match.groups()
                normalized_typ = self.process_mapping.get(prozess_typ.lower())
                if not normalized_typ:
                    return None

                return {
                    "action": "complete_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": normalized_typ,
                        "bearbeiter": bearbeiter.strip(),
                        "status": "abgeschlossen",
                        "datenquelle": "flowers_email"
                    }
                }

            elif pattern_name == 'warteschlange':
                fin, prozess_typ, prioritaet = match.groups()
                normalized_typ = self.process_mapping.get(prozess_typ.lower())
                if not normalized_typ:
                    return None

                return {
                    "action": "queue_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": normalized_typ,
                        "prioritaet": int(prioritaet),
                        "status": "warteschlange",
                        "datenquelle": "flowers_email"
                    }
                }
                
            # NEUE PATTERN-BEHANDLUNG für einfache E-Mail-Formate
            elif pattern_name == 'simple_process_started':
                prozess_typ_raw, status, fin = match.groups()
                prozess_typ = prozess_typ_raw.strip()
                
                # Prozesstyp normalisieren über bestehende Methode
                normalized_typ = self.normalize_prozess_typ(prozess_typ)
                
                return {
                    "action": "start_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": normalized_typ,
                        "status": "gestartet",
                        "datenquelle": "flowers_email",
                        "notizen": f"Einfaches E-Mail-Format: {prozess_typ} {status}"
                    }
                }
                
            elif pattern_name == 'simple_process_completed':
                prozess_typ_raw, status, fin = match.groups()
                prozess_typ = prozess_typ_raw.strip()
                
                normalized_typ = self.normalize_prozess_typ(prozess_typ)
                
                return {
                    "action": "complete_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": normalized_typ,
                        "status": "abgeschlossen",
                        "datenquelle": "flowers_email",
                        "notizen": f"Einfaches E-Mail-Format: {prozess_typ} {status}"
                    }
                }
                
            elif pattern_name == 'simple_process_paused':
                prozess_typ_raw, status, fin = match.groups()
                prozess_typ = prozess_typ_raw.strip()
                
                normalized_typ = self.normalize_prozess_typ(prozess_typ)
                
                return {
                    "action": "pause_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": normalized_typ,
                        "status": "pausiert",
                        "datenquelle": "flowers_email",
                        "notizen": f"Einfaches E-Mail-Format: {prozess_typ} {status}"
                    }
                }
                
            elif pattern_name == 'simple_process_queued':
                prozess_typ_raw, status, fin = match.groups()
                prozess_typ = prozess_typ_raw.strip()
                
                normalized_typ = self.normalize_prozess_typ(prozess_typ)
                
                return {
                    "action": "queue_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": normalized_typ,
                        "status": "warteschlange",
                        "datenquelle": "flowers_email",
                        "prioritaet": 5,  # Standard-Priorität
                        "notizen": f"Einfaches E-Mail-Format: {prozess_typ} {status}"
                    }
                }
                
            elif pattern_name == 'simple_process_started_with_worker':
                prozess_typ_raw, status, fin, bearbeiter = match.groups()
                prozess_typ = prozess_typ_raw.strip()
                
                normalized_typ = self.normalize_prozess_typ(prozess_typ)
                
                return {
                    "action": "start_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": normalized_typ,
                        "bearbeiter": bearbeiter.strip(),
                        "status": "gestartet",
                        "datenquelle": "flowers_email",
                        "notizen": f"Einfaches E-Mail-Format mit Bearbeiter: {prozess_typ} {status}"
                    }
                }
                
            elif pattern_name == 'simple_process_completed_with_worker':
                prozess_typ_raw, status, fin, bearbeiter = match.groups()
                prozess_typ = prozess_typ_raw.strip()
                
                normalized_typ = self.normalize_prozess_typ(prozess_typ)
                
                return {
                    "action": "complete_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": normalized_typ,
                        "bearbeiter": bearbeiter.strip(),
                        "status": "abgeschlossen",
                        "datenquelle": "flowers_email",
                        "notizen": f"Einfaches E-Mail-Format mit Bearbeiter: {prozess_typ} {status}"
                    }
                }

            # Weitere bestehende Pattern-Behandlungen (transport_info, aufbereitung_info, etc.)
            # ... (bestehender Code bleibt unverändert)

            else:
                logger.warning(f"Unbekanntes Pattern: {pattern_name}")
                return None

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Action für Pattern {pattern_name}: {e}")
            return None

    async def process_webhook_data(self, webhook_data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Verarbeitet Webhook-Daten von Flowers"""
        try:
            logger.info(f"🔗 Processing {source} webhook data")
            
            fin = webhook_data.get('fin')
            prozess_typ_raw = webhook_data.get('prozess_typ')
            action = webhook_data.get('action', 'start_process')
            
            if not fin:
                return {"status": "error", "message": "FIN ist erforderlich", "source": source}
            
            if not prozess_typ_raw:
                return {"status": "error", "message": "prozess_typ ist erforderlich", "source": source}
            
            # Prozesstyp normalisieren
            prozess_typ = self.process_mapping.get(prozess_typ_raw.lower())
            if not prozess_typ:
                return {
                    "status": "error", 
                    "message": f"Unbekannter prozess_typ: {prozess_typ_raw}. Erlaubt: {list(self.process_mapping.keys())}", 
                    "source": source
                }
            
            # Action ausführen
            if action == 'start_process':
                result = await self._start_process_from_webhook(fin, prozess_typ, webhook_data, source)
            elif action == 'update_status':
                result = await self._update_status_from_webhook(fin, prozess_typ, webhook_data, source)
            else:
                result = {"status": "error", "message": f"Unbekannte Action: {action}", "source": source}
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Webhook processing failed: {e}")
            return {"status": "error", "message": str(e), "source": source}

    async def _start_process_from_webhook(self, fin: str, prozess_typ: str, data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Startet Prozess aus Webhook-Daten (korrigierte Typ-Annotations)"""
        try:
            prozess_id = str(uuid.uuid4())
            
            process_data = {
                "prozess_id": prozess_id,
                "fin": fin,
                "prozess_typ": prozess_typ,
                "status": data.get('status', 'gestartet'),
                "bearbeiter": data.get('bearbeiter'),
                "prioritaet": data.get('prioritaet', 5),
                "anlieferung_datum": data.get('anlieferung_datum'),
                "start_timestamp": datetime.now(),
                "notizen": data.get('notizen', f"Erstellt via {source}"),
                "datenquelle": source
            }
            
            if self.bigquery_service:
                success = await self.bigquery_service.create_process(process_data)
                if success:
                    return {
                        "status": "success",
                        "message": f"Prozess {prozess_typ} für {fin} gestartet",
                        "prozess_id": prozess_id,
                        "source": source
                    }
            
            return {"status": "error", "message": "BigQuery-Speicherung fehlgeschlagen", "source": source}
            
        except Exception as e:
            logger.error(f"❌ Start process failed: {e}")
            return {"status": "error", "message": str(e), "source": source}

    async def _update_status_from_webhook(self, fin: str, prozess_typ: str, data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Status-Update aus Webhook (Placeholder)"""
        return {
            "status": "success", 
            "message": f"Status-Update für {fin} ({prozess_typ}) verarbeitet",
            "source": source
        }
    
    @staticmethod
    def extract_fin_from_text(text: str) -> Optional[str]:
        """Zentrale FIN-Extraktion für alle Handler"""
        import re
        
        # Erst versuchen mit "FIN:" Label (bevorzugt für neue E-Mail-Formate)
        fin_pattern_labeled = re.compile(r'FIN:\s*([A-Z0-9]{15,17})', re.IGNORECASE)
        match = fin_pattern_labeled.search(text)
        if match:
            return match.group(1)
        
        # Fallback: Nackte 17-stellige FIN (für alte E-Mail-Formate)
        fin_pattern_naked = re.compile(r'\b([A-HJ-NPR-Z0-9]{17})\b')
        match = fin_pattern_naked.search(text.upper())
        if match:
            return match.group(1)
        
        return None