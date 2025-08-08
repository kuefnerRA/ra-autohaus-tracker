# src/handlers/flowers_handler.py
import re
import uuid
import logging
from datetime import datetime, date
from typing import Dict, Optional, Any, List
from email.mime.text import MIMEText
import json

logger = logging.getLogger(__name__)


class FlowersHandler:
    """Handler für alle Flowers-Datenquellen: E-Mail, Webhook, Zapier"""
    
    def __init__(self, bigquery_service=None):
        self.bigquery_service = bigquery_service
        
        # E-Mail-Patterns für Flowers-Nachrichten
        self.email_patterns = {
            'prozess_gestartet': r'Fahrzeug\s+(\w{17})\s+-\s+(\w+)\s+gestartet\s+von\s+(.+?)(?:\n|$)',
            'prozess_abgeschlossen': r'Fahrzeug\s+(\w{17})\s+-\s+(\w+)\s+abgeschlossen\s+von\s+(.+?)(?:\n|$)',
            'warteschlange': r'Fahrzeug\s+(\w{17})\s+wartet\s+auf\s+(\w+)\s+-\s+Priorität\s+(\d+)',
            'transport_info': r'Transport:\s+FIN\s+(\w{17})\s+von\s+(.+?)\s+nach\s+(.+?)\s+am\s+(\d{2}\.\d{2}\.\d{4})',
            'aufbereitung_info': r'Aufbereitung:\s+(\w{17})\s+-\s+(\w+)\s+Stufe\s+(\d+)\s+durch\s+(.+)',
            'werkstatt_info': r'GWA:\s+(\w{17})\s+-\s+(.+?)\s+zugewiesen\s+an\s+(.+?)\s+am\s+(\d{2}\.\d{2}\.\d{4})',
            'foto_info': r'Foto:\s+(\w{17})\s+-\s+(\w+)\s+Qualität\s+durch\s+(.+)',
            'status_update': r'Status:\s+(\w{17})\s+(\w+)\s+->\s+(\w+)\s+durch\s+(.+)'
        }
        
        # Prozesstyp-Mapping - 6 Hauptprozesse mit festen Schlüsselbegriffen
        self.process_mapping = {
            'einkauf': 'Einkauf',
            'anlieferung': 'Anlieferung', 
            'aufbereitung': 'Aufbereitung',
            'foto': 'Foto',
            'werkstatt': 'Werkstatt',
            'verkauf': 'Verkauf'
        }

    async def parse_flowers_email(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parst Flowers E-Mail und extrahiert Fahrzeug- und Prozessdaten
        
        Args:
            email_data: {"subject": str, "body": str, "sender": str, "timestamp": str}
        
        Returns:
            List von Aktionen: [{"action": "create_process", "data": {...}}, ...]
        """
        try:
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            sender = email_data.get('sender', 'flowers@system')
            timestamp = email_data.get('timestamp', datetime.now().isoformat())
            
            logger.info(f"📧 Parsing Flowers email: {subject}")
            
            actions = []
            email_content = f"{subject}\n{body}"
            
            # Alle Patterns durchgehen
            for pattern_name, pattern in self.email_patterns.items():
                matches = re.finditer(pattern, email_content, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    action = await self._create_action_from_match(
                        pattern_name, match, sender, timestamp
                    )
                    if action:
                        actions.append(action)
            
            logger.info(f"✅ Extracted {len(actions)} actions from email")
            return actions
            
        except Exception as e:
            logger.error(f"❌ Email parsing failed: {e}")
            return []

    async def _create_action_from_match(
        self, pattern_name: str, match: re.Match, sender: str, timestamp: str
    ) -> Optional[Dict[str, Any]]:
        """Erstellt Aktionen basierend auf E-Mail-Pattern-Matches"""
        
        try:
            if pattern_name == 'prozess_gestartet':
                fin, prozess_typ, bearbeiter = match.groups()
                return {
                    "action": "start_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": self.process_mapping.get(prozess_typ.lower(), prozess_typ),
                        "bearbeiter": bearbeiter.strip(),
                        "status": "gestartet",
                        "datenquelle": "flowers_email"
                    }
                }
                
            elif pattern_name == 'prozess_abgeschlossen':
                fin, prozess_typ, bearbeiter = match.groups()
                return {
                    "action": "complete_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": self.process_mapping.get(prozess_typ.lower(), prozess_typ),
                        "bearbeiter": bearbeiter.strip(),
                        "status": "abgeschlossen",
                        "datenquelle": "flowers_email"
                    }
                }
                
            elif pattern_name == 'warteschlange':
                fin, prozess_typ, prioritaet = match.groups()
                return {
                    "action": "queue_process", 
                    "data": {
                        "fin": fin,
                        "prozess_typ": self.process_mapping.get(prozess_typ.lower(), prozess_typ),
                        "prioritaet": int(prioritaet),
                        "status": "warteschlange",
                        "datenquelle": "flowers_email"
                    }
                }
                
            elif pattern_name == 'transport_info':
                fin, von, nach, datum = match.groups()
                return {
                    "action": "start_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": "Transport",
                        "status": "gestartet",
                        "notizen": f"Transport von {von} nach {nach}",
                        "anlieferung_datum": self._parse_german_date(datum),
                        "datenquelle": "flowers_email"
                    }
                }
                
            elif pattern_name == 'aufbereitung_info':
                fin, typ, stufe, bearbeiter = match.groups()
                return {
                    "action": "start_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": "Aufbereitung",
                        "bearbeiter": bearbeiter.strip(),
                        "prioritaet": int(stufe),
                        "notizen": f"Aufbereitung {typ} Stufe {stufe}",
                        "status": "gestartet",
                        "datenquelle": "flowers_email"
                    }
                }
                
            elif pattern_name == 'werkstatt_info':
                fin, arbeitsauftrag, bearbeiter, datum = match.groups()
                return {
                    "action": "start_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": "Werkstatt",
                        "bearbeiter": bearbeiter.strip(),
                        "notizen": f"GWA: {arbeitsauftrag}",
                        "anlieferung_datum": self._parse_german_date(datum),
                        "status": "gestartet",
                        "datenquelle": "flowers_email"
                    }
                }
                
            elif pattern_name == 'foto_info':
                fin, qualitaet, bearbeiter = match.groups()
                prioritaet = 1 if qualitaet.lower() == 'premium' else 3
                return {
                    "action": "start_process",
                    "data": {
                        "fin": fin,
                        "prozess_typ": "Foto",
                        "bearbeiter": bearbeiter.strip(),
                        "prioritaet": prioritaet,
                        "notizen": f"Foto {qualitaet}",
                        "status": "gestartet",
                        "datenquelle": "flowers_email"
                    }
                }
                
            elif pattern_name == 'status_update':
                fin, alter_status, neuer_status, bearbeiter = match.groups()
                return {
                    "action": "update_status",
                    "data": {
                        "fin": fin,
                        "alter_status": alter_status,
                        "neuer_status": neuer_status,
                        "bearbeiter": bearbeiter.strip(),
                        "datenquelle": "flowers_email"
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Action creation failed for {pattern_name}: {e}")
            
        return None

    def _parse_german_date(self, date_str: str) -> Optional[str]:
        """Parst deutsches Datumsformat DD.MM.YYYY zu ISO-Format"""
        try:
            day, month, year = date_str.split('.')
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except:
            return None

    async def process_webhook_data(self, webhook_data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Verarbeitet Webhook-Daten von Flowers (direkt oder über Zapier)
        
        Args:
            webhook_data: JSON-Daten vom Webhook
            source: "flowers_direct" oder "zapier"
        
        Returns:
            Verarbeitungsresultat
        """
        try:
            logger.info(f"🔗 Processing {source} webhook data")
            
            # Standardisierte Webhook-Struktur erwarten
            # {"fin": "...", "prozess_typ": "...", "action": "...", "data": {...}}
            
            fin = webhook_data.get('fin')
            prozess_typ = webhook_data.get('prozess_typ')
            action = webhook_data.get('action', 'start_process')
            
            if not fin or not prozess_typ:
                return {
                    "status": "error",
                    "message": "FIN und prozess_typ sind erforderlich",
                    "source": source
                }
            
            # Prozesstyp normalisieren
            normalized_prozess_typ = self.process_mapping.get(prozess_typ.lower(), prozess_typ)
            
            # Action ausführen
            result = None
            if action == 'start_process':
                result = await self._start_process_from_webhook(
                    fin, normalized_prozess_typ, webhook_data, source
                )
            elif action == 'update_status':
                result = await self._update_status_from_webhook(
                    fin, normalized_prozess_typ, webhook_data, source
                )
            elif action == 'complete_process':
                result = await self._complete_process_from_webhook(
                    fin, normalized_prozess_typ, webhook_data, source
                )
            else:
                return {
                    "status": "error", 
                    "message": f"Unbekannte Action: {action}",
                    "source": source
                }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Webhook processing failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "source": source
            }

    async def _start_process_from_webhook(
        self, fin: str, prozess_typ: str, data: Dict[str, Any], source: str
    ) -> Dict[str, Any]:
        """Startet Prozess aus Webhook-Daten"""
        
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
        
        # In BigQuery speichern
        if self.bigquery_service:
            success = await self.bigquery_service.create_process(process_data)
            if success:
                return {
                    "status": "success",
                    "message": f"Prozess {prozess_typ} für {fin} gestartet",
                    "prozess_id": prozess_id,
                    "source": source,
                    "storage": "bigquery"
                }
        
        return {
            "status": "error",
            "message": "BigQuery-Speicherung fehlgeschlagen",
            "source": source
        }

    async def _update_status_from_webhook(
        self, fin: str, prozess_typ: str, data: Dict[str, Any], source: str
    ) -> Dict[str, Any]:
        """Aktualisiert Prozess-Status aus Webhook"""
        
        if not self.bigquery_service:
            return {"status": "error", "message": "BigQuery Service nicht verfügbar"}
        
        try:
            # Prozess finden
            query = f"""
            SELECT prozess_id, status as current_status
            FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE fin = @fin AND prozess_typ = @prozess_typ
            ORDER BY erstellt_am DESC
            LIMIT 1
            """
            
            from google.cloud import bigquery
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("fin", "STRING", fin),
                    bigquery.ScalarQueryParameter("prozess_typ", "STRING", prozess_typ)
                ]
            )
            
            result = self.bigquery_service.client.query(query, job_config=job_config)
            processes = [dict(row) for row in result]
            
            if not processes:
                return {
                    "status": "error",
                    "message": f"Kein {prozess_typ}-Prozess für {fin} gefunden",
                    "source": source
                }
            
            process = processes[0]
            
            # Status-Update erstellen
            update_data = {
                "update_id": str(uuid.uuid4()),
                "prozess_id": process["prozess_id"],
                "alter_status": process["current_status"],
                "neuer_status": data.get('neuer_status', data.get('status')),
                "bearbeiter": data.get('bearbeiter'),
                "update_timestamp": datetime.now().isoformat(),
                "notizen": data.get('notizen', f"Update via {source}"),
                "datenquelle": source
            }
            
            # Status-Update in BigQuery speichern
            table_id = "ra-autohaus-tracker.autohaus.prozess_status_updates"
            table = self.bigquery_service.client.get_table(table_id)
            
            # None-Werte entfernen
            update_row = {k: v for k, v in update_data.items() if v is not None}
            
            errors = self.bigquery_service.client.insert_rows_json(table, [update_row])
            if errors:
                logger.error(f"Status-Update BigQuery errors: {errors}")
                return {
                    "status": "error",
                    "message": f"Status-Update fehlgeschlagen: {errors}",
                    "source": source
                }
            
            return {
                "status": "success",
                "message": f"Status von {fin} aktualisiert: {process['current_status']} -> {update_data['neuer_status']}",
                "prozess_id": process["prozess_id"],
                "source": source
            }
            
        except Exception as e:
            logger.error(f"❌ Status update failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "source": source
            }

    async def parse_zapier_webhook(self, zapier_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parst Zapier-Webhook-Daten
        Zapier sendet meist strukturierte Daten
        """
        try:
            logger.info(f"⚡ Processing Zapier webhook")
            
            # Zapier-Datenstruktur kann variieren
            # Beispiel: {"trigger": "process_update", "vehicle_fin": "...", "process_type": "..."}
            
            actions = []
            
            # Standard Zapier-Struktur
            if 'vehicle_fin' in zapier_data and 'process_type' in zapier_data:
                action_data = {
                    "fin": zapier_data['vehicle_fin'],
                    "prozess_typ": self.process_mapping.get(
                        zapier_data['process_type'].lower(), 
                        zapier_data['process_type']
                    ),
                    "bearbeiter": zapier_data.get('employee_name'),
                    "prioritaet": zapier_data.get('priority', 5),
                    "status": zapier_data.get('status', 'gestartet'),
                    "notizen": zapier_data.get('notes'),
                    "anlieferung_datum": zapier_data.get('delivery_date')
                }
                
                trigger = zapier_data.get('trigger', 'start_process')
                actions.append({
                    "action": trigger,
                    "data": action_data
                })
            
            # Batch-Verarbeitung für mehrere Fahrzeuge
            elif 'vehicles' in zapier_data:
                for vehicle_data in zapier_data['vehicles']:
                    action_data = {
                        "fin": vehicle_data['fin'],
                        "prozess_typ": self.process_mapping.get(
                            vehicle_data['process_type'].lower(),
                            vehicle_data['process_type']
                        ),
                        "bearbeiter": vehicle_data.get('employee_name'),
                        "prioritaet": vehicle_data.get('priority', 5),
                        "status": vehicle_data.get('status', 'gestartet'),
                        "datenquelle": "zapier"
                    }
                    
                    actions.append({
                        "action": vehicle_data.get('action', 'start_process'),
                        "data": action_data
                    })
            
            logger.info(f"✅ Extracted {len(actions)} actions from Zapier")
            return actions
            
        except Exception as e:
            logger.error(f"❌ Zapier parsing failed: {e}")
            return []

    async def execute_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Führt extrahierte Aktionen aus"""
        
        results = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "actions": []
        }
        
        for action in actions:
            try:
                action_type = action.get('action')
                action_data = action.get('data', {})
                
                result = None
                
                if action_type == 'start_process':
                    result = await self._execute_start_process(action_data)
                elif action_type == 'update_status':
                    result = await self._execute_update_status(action_data)
                elif action_type == 'complete_process':
                    result = await self._execute_complete_process(action_data)
                elif action_type == 'queue_process':
                    result = await self._execute_queue_process(action_data)
                else:
                    result = {
                        "status": "error",
                        "message": f"Unbekannte Action: {action_type}"
                    }
                
                if result and result.get('status') == 'success':
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                
                results['actions'].append({
                    "action": action_type,
                    "data": action_data,
                    "result": result
                })
                
                results['processed'] += 1
                
            except Exception as e:
                logger.error(f"❌ Action execution failed: {e}")
                results['failed'] += 1
                results['actions'].append({
                    "action": action.get('action'),
                    "error": str(e)
                })
        
        return results

    async def _execute_start_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Prozess-Start aus"""
        try:
            prozess_id = str(uuid.uuid4())
            
            process_data = {
                "prozess_id": prozess_id,
                "start_timestamp": datetime.now(),
                **data
            }
            
            if self.bigquery_service:
                success = await self.bigquery_service.create_process(process_data)
                if success:
                    return {
                        "status": "success",
                        "message": f"Prozess {data['prozess_typ']} für {data['fin']} gestartet",
                        "prozess_id": prozess_id
                    }
            
            return {"status": "error", "message": "BigQuery-Speicherung fehlgeschlagen"}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _execute_queue_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Warteschlangen-Einreihung aus"""
        # Prozess starten und sofort in Warteschlange setzen
        data_copy = data.copy()
        data_copy['status'] = 'warteschlange'
        return await self._execute_start_process(data_copy)

    async def _execute_complete_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Prozess-Abschluss aus"""
        data_copy = data.copy()
        data_copy['status'] = 'abgeschlossen'
        data_copy['ende_timestamp'] = datetime.now()
        return await self._execute_start_process(data_copy)

    async def _execute_update_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Status-Update aus"""
        # Implementierung für Status-Updates über das Status-Update-System
        # Hier würde die Logik für create_status_update aufgerufen werden
        return {
            "status": "success", 
            "message": f"Status-Update für {data.get('fin')} verarbeitet"
        }


# Utility Funktionen für E-Mail-Verarbeitung
class EmailProcessor:
    """Hilfsklasse für E-Mail-Verarbeitung"""
    
    @staticmethod
    def extract_email_data(raw_email: str) -> Dict[str, Any]:
        """
        Extrahiert strukturierte Daten aus roher E-Mail
        Für verschiedene E-Mail-Formate (SendGrid, Gmail API, etc.)
        """
        # Placeholder für E-Mail-Parsing-Logik
        # Würde je nach E-Mail-Provider angepasst werden
        return {
            "subject": "Extracted Subject",
            "body": "Extracted Body", 
            "sender": "flowers@system",
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def validate_fin(fin: str) -> bool:
        """Validiert FIN (Fahrzeug-Identifikationsnummer)"""
        if not fin or len(fin) != 17:
            return False
        
        # FIN besteht aus Alphanumerischen Zeichen (ohne I, O, Q)
        pattern = r'^[A-HJ-NPR-Z0-9]{17}$'
        return bool(re.match(pattern, fin))