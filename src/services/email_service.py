"""
Email Service - Email-Parsing und Fahrzeug-Verarbeitung
Reinhardt Automobile GmbH - RA Autohaus Tracker
"""

import re
import imaplib
import email
from email.header import decode_header
from datetime import date
from typing import Dict, Optional, Any, Tuple
from decimal import Decimal
import structlog

from src.models.integration import (
    Antriebsart, Bereifungsart, Besteuerungsart,
    Datenquelle
)
from src.core.mappings import CentralMappings

logger = structlog.get_logger(__name__)

class EmailParser:
    """
    Parser für strukturierte Fahrzeug-Emails von Flowers und manuellen Quellen.
    """
    
    # Regex-Patterns für deutsche Formate
    PATTERNS = {
        'fin': r'(?:FIN|Referenz)[:\s]+([A-Z0-9]{17})',
        'marke': r'Marke[:\s]+(.+?)(?:\n|$)',
        'modell': r'Modell[:\s]+(.+?)(?:\n|$)',
        'datum_erstzulassung': r'Datum Erstzulassung[:\s]+(\d{1,2}\.\d{1,2}\.\d{4})',
        'antriebsart': r'Antriebsart[:\s]+(.+?)(?:\n|$)',
        'kw_leistung': r'KW-Leistung[:\s]+(\d+)',
        'km_stand': r'KM-Stand[:\s]+([\d\.]+)',
        'anzahl_fahrzeugschluessel': r'Anzahl Fahrzeugschlüssel[:\s]+(\d+)',
        'bereifungsart': r'Bereifungsart[:\s]+(.+?)(?:\n|$)',
        'anzahl_vorhalter': r'Anzahl Vorhalter[:\s]+(\d+)',
        'ek_netto': r'EK netto[:\s]+([\d\.,]+)',
        'besteuerungsart': r'Besteuerungsart[:\s]+(.+?)(?:\n|$)',
        'bearbeiter': r'^Bearbeiter[:\s]+(.+?)(?:\n|$)',
        'farbe': r'Farbe[:\s]+(.+?)(?:\n|$)',
        'baujahr': r'Baujahr[:\s]+(\d{4})',
    }
    
    # Mapping für Antriebsarten
    ANTRIEB_MAPPING = {
        'benzin': Antriebsart.BENZIN,
        'diesel': Antriebsart.DIESEL,
        'elektro': Antriebsart.ELEKTRO,
        'hybrid': Antriebsart.HYBRID,
        'plugin': Antriebsart.PLUGIN_HYBRID,
        'plug-in': Antriebsart.PLUGIN_HYBRID,
        'erdgas': Antriebsart.ERDGAS,
        'autogas': Antriebsart.AUTOGAS,
    }
    
    # Mapping für Bereifung
    BEREIFUNG_MAPPING = {
        'sommer': Bereifungsart.SOMMER,
        'winter': Bereifungsart.WINTER,
        'ganzjahr': Bereifungsart.GANZJAHR,
        'allwetter': Bereifungsart.GANZJAHR,
    }
    
    # Mapping für Besteuerung
    BESTEUERUNG_MAPPING = {
        'regel': Besteuerungsart.REGEL,
        'differenz': Besteuerungsart.DIFFERENZ,
        'export': Besteuerungsart.EXPORT,
    }
    
    def __init__(self):
        self.logger = logger.bind(service="EmailParser")
    
    def parse_subject_for_process(self, subject: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrahiert Prozesstyp und Status aus Email-Betreff.
        Rückgabe als String (nicht Enum) für Flexibilität.
        """
        subject_lower = subject.lower().strip()
        
        if "änderung bearbeiter" in subject_lower:
            return "Bearbeiterwechsel", "AKTIV"
    
        # Nutze zentrale Mappings für Keywords
        for keyword, prozess_typ in CentralMappings.PROZESS_MAPPINGS.items():
            if keyword in subject_lower:
                # Status aus Rest des Betreffs
                rest = subject_lower.replace(keyword, '').strip()
                status = CentralMappings.normalize_status(rest) if rest else "WARTESCHLANGE"
                return prozess_typ, status
        
        return None, None
    
    def parse_email_content(self, subject: str, body: str) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Extrahiert Fahrzeug- und Prozessdaten aus Email.
        
        Returns:
            Tuple[fahrzeug_dict, prozess_dict] oder (None, None) bei Fehler
        """
        try:


            # Text normalisieren
            body = body.replace('\r\n', '\n').replace('\r', '\n')

            # NEU: Body von Signaturen und Trennlinien bereinigen
            body = re.sub(r'[-]{10,}.*', '', body, flags=re.DOTALL)  # Entfernt alles nach ----------
            body = re.sub(r'Sent via.*', '', body, flags=re.DOTALL)  # Entfernt "Sent via" Signaturen

            
            # FIN extrahieren (Pflichtfeld)
            fin_match = re.search(self.PATTERNS['fin'], f"{subject}\n{body}", re.IGNORECASE)
            if not fin_match:
                self.logger.warning("⚠️ Keine FIN in Email gefunden")
                return None, None
            
            fin = fin_match.group(1).upper()
            
            # Fahrzeugdaten sammeln
            fahrzeug_data = {
                'fin': fin,
                'datenquelle_fahrzeug': Datenquelle.EMAIL,
                'erstellt_aus_email': True
            }
            
            # Alle Felder extrahieren
            for field, pattern in self.PATTERNS.items():
                if field == 'fin':
                    continue
                    
                match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    
                    if field == 'datum_erstzulassung':
                        # Deutsches Datum (DD.MM.YYYY) zu date
                        day, month, year = value.split('.')
                        fahrzeug_data['datum_erstzulassung'] = date(int(year), int(month), int(day))
                    
                    elif field == 'baujahr':
                        fahrzeug_data['baujahr'] = int(value)
                    
                    elif field == 'kw_leistung':
                        fahrzeug_data['kw_leistung'] = int(value)
                    
                    elif field == 'km_stand':
                        # Deutsche Zahlenformatierung (25.000 -> 25000)
                        km_clean = value.replace('.', '').replace(',', '.')
                        fahrzeug_data['km_stand'] = int(float(km_clean))
                    
                    elif field == 'anzahl_fahrzeugschluessel':
                        fahrzeug_data['anzahl_fahrzeugschluessel'] = int(value)
                    
                    elif field == 'anzahl_vorhalter':
                        fahrzeug_data['anzahl_vorhalter'] = int(value)
                    
                    elif field == 'ek_netto':
                        # Deutsche Währungsformatierung (28.500,00 -> 28500.00)
                        ek_clean = value.replace('.', '').replace(',', '.')
                        fahrzeug_data['ek_netto'] = Decimal(ek_clean)
                    
                    elif field == 'antriebsart':
                        antrieb = self._map_value(value, self.ANTRIEB_MAPPING)
                        if antrieb:
                            fahrzeug_data['antriebsart'] = antrieb
                    
                    elif field == 'bereifungsart':
                        bereifung = self._map_value(value, self.BEREIFUNG_MAPPING)
                        if bereifung:
                            fahrzeug_data['bereifungsart'] = bereifung
                    
                    elif field == 'besteuerungsart':
                        besteuerung = self._map_value(value, self.BESTEUERUNG_MAPPING)
                        if besteuerung:
                            fahrzeug_data['besteuerungsart'] = besteuerung
                    
                    elif field == 'bearbeiter':
                        # Bearbeiter für später speichern (für Prozess)
                        bearbeiter = value
                    
                    else:
                        fahrzeug_data[field] = value
            
            # Prozess aus Betreff extrahieren
            prozess_data = None
            prozess_typ, status = self.parse_subject_for_process(subject)
            
            if prozess_typ:
                prozess_data = {
                    'prozess_typ': prozess_typ,
                    'status': status or "Eingegangen via Email",
                    'bearbeiter': bearbeiter if 'bearbeiter' in locals() else None,
                    'datenquelle': Datenquelle.EMAIL,
                    'notizen': f"Automatisch erstellt aus Email: {subject}"
                }
            
            self.logger.info("✅ Email erfolgreich geparsed", 
                           fin=fin,
                           has_prozess=prozess_data is not None)
            
            return fahrzeug_data, prozess_data
            
        except Exception as e:
            self.logger.error("❌ Fehler beim Email-Parsing", error=str(e))
            return None, None
    
    def _map_value(self, value: str, mapping: Dict[str, Any]) -> Optional[Any]:
        """Mappt Textwerte zu Enums."""
        value_lower = value.lower()
        for key, enum_val in mapping.items():
            if key in value_lower:
                return enum_val
        return None


class EmailService:
    """
    Service für Email-Integration mit IMAP.
    """
    
    def __init__(self, 
                 imap_server: str,
                 email_address: str,
                 password: str,
                 processed_folder: str = "Verarbeitet",
                 error_folder: str = "Fehler",
                 ignored_folder: str = "Ignoriert"):
        """
        Initialisiert Email-Service.
        
        Args:
            imap_server: IMAP-Server (z.B. "imap.gmail.com")
            email_address: Email-Adresse
            password: Passwort oder App-spezifisches Passwort
            processed_folder: Ordner für verarbeitete Emails
            error_folder: Ordner für fehlerhafte Emails
        """
        self.imap_server = imap_server
        self.email_address = email_address
        self.password = password
        self.processed_folder = processed_folder
        self.error_folder = error_folder
        self.ignored_folder = ignored_folder
        self.parser = EmailParser()
        self.logger = logger.bind(service="EmailService")
    
    async def process_unread_emails(self, 
                               vehicle_service,
                               folder: str = "INBOX") -> Dict[str, Any]:
        """
        Verarbeitet alle ungelesenen Emails im angegebenen Ordner.
        
        Args:
            vehicle_service: VehicleService Instanz für Fahrzeug-Operationen
            folder: IMAP-Ordner zum Verarbeiten
        """
        from src.models.integration import FahrzeugStammCreate, FahrzeugProzessCreate
        
        results = {
            'processed': 0,
            'fahrzeuge_created': 0,
            'fahrzeuge_updated': 0,
            'prozesse_created': 0,
            'errors': []
        }
        
        try:
            # IMAP-Verbindung
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.password)
            
            # Ordner erstellen falls nicht vorhanden
            self._ensure_folders_exist(mail)
            
            mail.select(folder)
            
            # Ungelesene Emails suchen
            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK':
                raise Exception("Fehler beim Abrufen der Emails")
            
            email_ids = messages[0].split()
            
            for email_id in email_ids:
                email_processed_successfully = False  # Flag für erfolgreiche Verarbeitung
                
                try:
                    # Email abrufen
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK' or not msg_data or not msg_data[0]:
                        continue

                    # msg_data[0] ist ein Tuple (response_part, data)
                    raw_email = msg_data[0][1]
                    if not isinstance(raw_email, bytes):
                        continue
                    
                    # Email parsen
                    msg = email.message_from_bytes(raw_email)
                    subject = self._decode_header(msg['Subject'])
                    body = self._extract_body(msg)
                    
                    # Fahrzeugdaten extrahieren
                    fahrzeug_dict, prozess_dict = self.parser.parse_email_content(subject, body)
                    
                    if not fahrzeug_dict:
                        mail.store(email_id, '+FLAGS', '\\Seen')
                        self._move_email(mail, email_id, self.ignored_folder)
                        self.logger.debug(f"Email ohne FIN in 'Ignoriert' verschoben: {subject[:50]}")
                        continue

                    if fahrzeug_dict:
                        # Prüfen ob Fahrzeug existiert
                        existing = await vehicle_service.get_vehicle_details(fahrzeug_dict['fin'])
                        
                        if existing:
                            # UPDATE existierendes Fahrzeug
                            self.logger.info("📄 Fahrzeug existiert - starte Update", 
                                            fin=fahrzeug_dict['fin'])
                            
                            # Bereite Update-Daten vor (nur geänderte Felder)
                            update_data = {}
                            for field, new_value in fahrzeug_dict.items():
                                if field in ['fin', 'created_at', 'erstellt_aus_email']:
                                    continue  # Diese Felder nie updaten
                                
                                # Prüfe ob Feld im existierenden Fahrzeug leer ist oder sich unterscheidet
                                existing_value = existing.__dict__.get(field) if hasattr(existing, '__dict__') else None
                                
                                if new_value is not None and new_value != existing_value:
                                    update_data[field] = new_value
                            
                            if update_data:
                                # Update durchführen
                                update_result = await vehicle_service.update_vehicle(
                                    fin=fahrzeug_dict['fin'],
                                    update_data=update_data,
                                    create_update_process=True
                                )
                                
                                if update_result['changes_made']:
                                    results['fahrzeuge_updated'] += 1
                                    email_processed_successfully = True
                                    self.logger.info("✅ Fahrzeug aktualisiert", 
                                                fin=fahrzeug_dict['fin'],
                                                fields_updated=update_result['fields_updated'])
                                else:
                                    # Keine Änderungen, aber trotzdem erfolgreich verarbeitet
                                    email_processed_successfully = True
                                    self.logger.info("ℹ️ Keine Änderungen notwendig", 
                                                fin=fahrzeug_dict['fin'])
                            else:
                                # Keine neuen Daten, aber trotzdem erfolgreich verarbeitet
                                email_processed_successfully = True
                                self.logger.info("ℹ️ Keine neuen Daten zum Update", 
                                            fin=fahrzeug_dict['fin'])
                            
                            # Prozess erstellen falls vorhanden
                            if prozess_dict and email_processed_successfully:
                                try:
                                    # FIN zum prozess_dict hinzufügen
                                    prozess_dict['fin'] = fahrzeug_dict['fin']
                                    
                                    # FahrzeugProzessCreate statt Request verwenden
                                    from src.models.integration import FahrzeugProzessCreate
                                    prozess_create = FahrzeugProzessCreate(**prozess_dict)
                                    
                                    # Verwende create_vehicle_process statt create_or_update_process
                                    await vehicle_service.create_vehicle_process(
                                        fin=fahrzeug_dict['fin'],
                                        prozess_data=prozess_create
                                    )
                                    results['prozesse_created'] += 1
                                    self.logger.info(f"✅ Prozess erstellt für Update - FIN: {fahrzeug_dict['fin']}")
                                except Exception as e:
                                    self.logger.warning(f"⚠️ Prozess konnte nicht erstellt werden: {str(e)}")
                                    # Email trotzdem als erfolgreich markieren wenn Fahrzeug-Update geklappt hat
                        
                        else:
                            # NEUES Fahrzeug erstellen
                            fahrzeug = FahrzeugStammCreate(**fahrzeug_dict)
                            
                            # Prozess-Daten vorbereiten falls vorhanden
                            prozess_to_create = None
                            if prozess_dict:
                                prozess_to_create = FahrzeugProzessCreate(
                                    fin=fahrzeug_dict['fin'],
                                    **prozess_dict
                                )
                            
                            created = await vehicle_service.create_complete_vehicle(
                                fahrzeug_data=fahrzeug,
                                prozess_data=prozess_to_create
                            )
                            
                            if created:
                                results['fahrzeuge_created'] += 1
                                email_processed_successfully = True
                                if prozess_to_create:
                                    results['prozesse_created'] += 1
                        
                        # Email als verarbeitet markieren wenn erfolgreich
                        if email_processed_successfully:
                            results['processed'] += 1
                            # Email als gelesen markieren
                            mail.store(email_id, '+FLAGS', '\\Seen')
                            # Email in Verarbeitet-Ordner verschieben
                            self._move_email(mail, email_id, self.processed_folder)
                            self.logger.info(f"📧 Email verschoben nach 'Verarbeitet' - FIN: {fahrzeug_dict['fin']}")
                        
                except Exception as e:
                    self.logger.error("❌ Fehler bei Email-Verarbeitung", 
                                    email_id=email_id, 
                                    error=str(e))
                    results['errors'].append(str(e))
                    
                    # Fehlerhafte Email verschieben
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    self._move_email(mail, email_id, self.error_folder)
            
            mail.close()
            mail.logout()
            
            self.logger.info("📧 Email-Verarbeitung abgeschlossen", **results)
            return results
            
        except Exception as e:
            self.logger.error("❌ Fehler bei Email-Service", error=str(e))
            results['errors'].append(str(e))
            return results

    def _ensure_folders_exist(self, mail):
        """Stellt sicher, dass Verarbeitungs-Ordner existieren."""
        for folder in [self.processed_folder, self.error_folder, self.ignored_folder]:
            try:
                mail.create(folder)
            except:
                pass  # Ordner existiert bereits
    
    def _move_email(self, mail, email_id, target_folder):
        """Verschiebt Email in Zielordner."""
        try:
            result = mail.copy(email_id, target_folder)
            if result[0] == 'OK':
                mail.store(email_id, '+FLAGS', '\\Deleted')
                mail.expunge()
        except Exception as e:
            self.logger.warning("⚠️ Email konnte nicht verschoben werden", error=str(e))
    
    def _decode_header(self, header: str) -> str:
        """Dekodiert Email-Header vollständig."""
        if not header:
            return ""
        
        # Dekodiere ALLE Teile des Headers
        decoded_parts = decode_header(header)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                # Dekodiere mit dem angegebenen Encoding
                result.append(part.decode(encoding or 'utf-8', errors='ignore'))
            else:
                # Bereits ein String
                result.append(part)
        
        # Füge alle Teile zusammen
        return ''.join(result)
    
    def _extract_body(self, msg) -> str:
        """Extrahiert Text-Body aus Email."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return body