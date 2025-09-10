"""
Email Service - Email-Parsing und Fahrzeug-Verarbeitung
Reinhardt Automobile GmbH - RA Autohaus Tracker
"""

import re
import imaplib
import email
from email.header import decode_header
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import structlog

from src.models.integration import (
    FahrzeugStammCreate, FahrzeugProzessCreate, FahrzeugProzessRequest,
    ProzessTyp, Antriebsart, Bereifungsart, Besteuerungsart, Datenquelle
)

logger = structlog.get_logger(__name__)

class EmailParser:
    """
    Parser für strukturierte Fahrzeug-Emails von Flowers und manuellen Quellen.
    """
    
    # Regex-Patterns für deutsche Formate
    PATTERNS = {
        'fin': r'FIN[:\s]+([A-Z0-9]{17})',
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
        'bearbeiter': r'Bearbeiter[:\s]+(.+?)(?:\n|$)',
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
    
    def parse_subject_for_process(self, subject: str) -> Tuple[Optional[ProzessTyp], Optional[str]]:
        """
        Extrahiert Prozesstyp und Status aus Email-Betreff.
        
        Beispiel: "Einkauf abgeschlossen" -> (ProzessTyp.EINKAUF, "abgeschlossen")
        """
        subject_lower = subject.lower().strip()
        
        # Prozesstypen suchen
        prozess_mapping = {
            'einkauf': ProzessTyp.EINKAUF,
            'anlieferung': ProzessTyp.ANLIEFERUNG,
            'aufbereitung': ProzessTyp.AUFBEREITUNG,
            'foto': ProzessTyp.FOTO,
            'werkstatt': ProzessTyp.WERKSTATT,
            'verkauf': ProzessTyp.VERKAUF,
        }
        
        for keyword, prozess_typ in prozess_mapping.items():
            if keyword in subject_lower:
                # Status ist alles nach dem Prozesstyp
                status = subject_lower.replace(keyword, '').strip()
                if not status:
                    status = "Eingegangen"
                
                # Status normalisieren (erster Buchstabe groß)
                status = status.capitalize()
                
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
            
            # FIN extrahieren (Pflichtfeld)
            fin_match = re.search(self.PATTERNS['fin'], body, re.IGNORECASE)
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
                 error_folder: str = "Fehler"):
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
        from src.models.integration import FahrzeugStammCreate, FahrzeugProzessRequest
        
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
                    
                    if fahrzeug_dict:
                        # Prüfen ob Fahrzeug existiert
                        existing = await vehicle_service.get_vehicle_details(fahrzeug_dict['fin'])
                        
                        if existing:
                            # Update existierendes Fahrzeug
                            # TODO: Implement update logic
                            results['fahrzeuge_updated'] += 1
                            self.logger.info("ℹ️ Fahrzeug existiert bereits, Update", 
                                          fin=fahrzeug_dict['fin'])
                        else:
                            # Neues Fahrzeug erstellen
                            fahrzeug = FahrzeugStammCreate(**fahrzeug_dict)
                            created = await vehicle_service.create_complete_vehicle(
                                fahrzeug_data=fahrzeug,
                                prozess_data=None  # Prozess separat erstellen
                            )
                            
                            if created:
                                results['fahrzeuge_created'] += 1
                        
                        # Prozess erstellen falls vorhanden
                        if prozess_dict and fahrzeug_dict['fin']:
                            prozess = FahrzeugProzessRequest(**prozess_dict)
                            prozess_created = await vehicle_service.create_vehicle_process(
                                fin=fahrzeug_dict['fin'],
                                prozess_data=FahrzeugProzessCreate(
                                    prozess_id=vehicle_service._generate_process_id(
                                        fahrzeug_dict['fin'], 
                                        prozess_dict['prozess_typ']
                                    ),
                                    fin=fahrzeug_dict['fin'],
                                    **prozess_dict
                                )
                            )
                            
                            if prozess_created:
                                results['prozesse_created'] += 1
                        
                        # Email als gelesen markieren und verschieben
                        mail.store(email_id, '+FLAGS', '\\Seen')
                        self._move_email(mail, email_id, self.processed_folder)
                        
                    results['processed'] += 1
                    
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
        try:
            mail.create(self.processed_folder)
        except:
            pass  # Ordner existiert bereits
        
        try:
            mail.create(self.error_folder)
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
        """Dekodiert Email-Header."""
        if not header:
            return ""
        
        decoded = decode_header(header)[0]
        if isinstance(decoded[0], bytes):
            return decoded[0].decode(decoded[1] or 'utf-8')
        return decoded[0]
    
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