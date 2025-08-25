# src/handlers/email_handler.py

import imaplib
import email
import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import os
from email.header import decode_header
from bs4 import BeautifulSoup

from .flowers_handler import FlowersHandler

logger = logging.getLogger(__name__)

@dataclass
class ParsedEmail:
    """Geparste E-Mail-Daten von Flowers"""
    fin: str
    prozess_name: str
    status: str
    bearbeiter: Optional[str] = None
    marke: Optional[str] = None
    farbe: Optional[str] = None
    original_subject: str = ""
    timestamp: datetime = None

class EmailHandler:
    """Handler für Flowers E-Mail-Integration"""
    
    def __init__(self):
        self.flowers_handler = FlowersHandler()
        
        # E-Mail-Konfiguration aus Umgebungsvariablen
        self.imap_server = os.getenv('EMAIL_IMAP_SERVER', 'outlook.office365.com')
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.flowers_sender = os.getenv('FLOWERS_SENDER_EMAIL', 'flowers@')  # Teilstring für Absender-Filter
        
        # Regex-Muster für E-Mail-Parsing
        self.patterns = {
            'fin': re.compile(r'FIN:\s*([A-Z0-9]{15,17})', re.IGNORECASE),
            'marke': re.compile(r'Marke:\s*([^\n\r]+)', re.IGNORECASE),
            'farbe': re.compile(r'Farbe:\s*([^\n\r]+)', re.IGNORECASE),
            'bearbeiter': re.compile(r'Bearbeiter:\s*([^\n\r]+)', re.IGNORECASE),
        }
        
        # Mapping für Betreffzeilen-Parsing
        self.subject_pattern = re.compile(r'^([A-Za-z0-9_\-\s]+)\s+([A-Za-z0-9_\-\s]+)$')
        
    def connect_to_email(self) -> imaplib.IMAP4_SSL:
        """Verbindung zum E-Mail-Server herstellen"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_password)
            mail.select('inbox')
            logger.info(f"E-Mail-Verbindung zu {self.imap_server} erfolgreich")
            return mail
        except Exception as e:
            logger.error(f"E-Mail-Verbindung fehlgeschlagen: {e}")
            raise
    
    def parse_subject(self, subject: str) -> Tuple[str, str]:
        """Betreffzeile parsen: 'GWA gestartet' → ('GWA', 'gestartet')"""
        try:
            # Betreff dekodieren falls notwendig
            decoded_subject = ""
            for part, encoding in decode_header(subject):
                if isinstance(part, bytes):
                    decoded_subject += part.decode(encoding or 'utf-8')
                else:
                    decoded_subject += part
            
            # Prozess und Status extrahieren
            match = self.subject_pattern.match(decoded_subject.strip())
            if match:
                prozess = match.group(1).strip()
                status = match.group(2).strip()
                
                # Prozess-Normalisierung durch FlowersHandler
                normalized_prozess = self.flowers_handler.normalize_prozess_typ(prozess)
                
                return normalized_prozess, status
            else:
                logger.warning(f"Betreff konnte nicht geparst werden: {decoded_subject}")
                return "", ""
                
        except Exception as e:
            logger.error(f"Fehler beim Parsen des Betreffs '{subject}': {e}")
            return "", ""
    
    def parse_email_body(self, body: str) -> Dict[str, str]:
        """E-Mail-Body nach Flowers-Feldern durchsuchen"""
        parsed_data = {}
        
        # HTML entfernen falls vorhanden
        if '<html>' in body.lower() or '<body>' in body.lower():
            soup = BeautifulSoup(body, 'html.parser')
            body = soup.get_text()
        
        # Alle definierten Patterns anwenden
        for field_name, pattern in self.patterns.items():
            match = pattern.search(body)
            if match:
                value = match.group(1).strip()
                if value:  # Nur nicht-leere Werte speichern
                    parsed_data[field_name] = value
        
        return parsed_data
    
    def parse_flowers_email(self, msg) -> Optional[ParsedEmail]:
        """Komplette Flowers E-Mail parsen"""
        try:
            # Betreff extrahieren
            subject = msg['subject']
            if not subject:
                return None
            
            # Absender prüfen (optional, falls Filterung gewünscht)
            sender = msg['from']
            # if self.flowers_sender and self.flowers_sender not in sender.lower():
            #     return None  # Nicht von Flowers
            
            # Datum extrahieren
            email_date = email.utils.parsedate_tz(msg['date'])
            timestamp = datetime.fromtimestamp(email.utils.mktime_tz(email_date)) if email_date else datetime.now()
            
            # Betreff parsen
            prozess_name, status = self.parse_subject(subject)
            if not prozess_name or not status:
                logger.warning(f"Ungültiger Betreff: {subject}")
                return None
            
            # Body extrahieren
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Body parsen
            body_data = self.parse_email_body(body)
            
            # FIN ist Pflichtfeld
            if 'fin' not in body_data:
                logger.warning(f"Keine FIN in E-Mail gefunden: {subject}")
                return None
            
            # ParsedEmail-Objekt erstellen
            parsed_email = ParsedEmail(
                fin=body_data['fin'],
                prozess_name=prozess_name,
                status=status,
                bearbeiter=body_data.get('bearbeiter'),
                marke=body_data.get('marke'),
                farbe=body_data.get('farbe'),
                original_subject=subject,
                timestamp=timestamp
            )
            
            logger.info(f"E-Mail erfolgreich geparst: {parsed_email.fin} - {parsed_email.prozess_name} - {parsed_email.status}")
            return parsed_email
            
        except Exception as e:
            logger.error(f"Fehler beim Parsen der E-Mail: {e}")
            return None
    
    def process_unread_emails(self) -> List[ParsedEmail]:
        """Ungelesene E-Mails abrufen und verarbeiten"""
        processed_emails = []
        
        try:
            mail = self.connect_to_email()
            
            # Nach ungelesenen E-Mails suchen
            status, messages = mail.search(None, 'UNSEEN')
            
            if status != 'OK':
                logger.error("Fehler beim Suchen nach E-Mails")
                return processed_emails
            
            email_ids = messages[0].split()
            logger.info(f"{len(email_ids)} ungelesene E-Mails gefunden")
            
            for email_id in email_ids:
                try:
                    # E-Mail abrufen
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    # E-Mail-Objekt erstellen
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # E-Mail parsen
                    parsed_email = self.parse_flowers_email(msg)
                    
                    if parsed_email:
                        processed_emails.append(parsed_email)
                        
                        # E-Mail als gelesen markieren
                        mail.store(email_id, '+FLAGS', '\\Seen')
                        
                except Exception as e:
                    logger.error(f"Fehler beim Verarbeiten der E-Mail {email_id}: {e}")
                    continue
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten der E-Mails: {e}")
        
        return processed_emails
    
    def save_to_bigquery(self, parsed_emails: List[ParsedEmail]) -> bool:
        """Geparste E-Mails in BigQuery speichern"""
        try:
            for parsed_email in parsed_emails:
                # Conversion zu Zapier-ähnlichem Format für bestehende Logik
                webhook_data = {
                    'fahrzeug_fin': parsed_email.fin,
                    'prozess_name': parsed_email.prozess_name,
                    'neuer_status': parsed_email.status,
                    'bearbeiter_name': parsed_email.bearbeiter or '',
                    'timestamp': parsed_email.timestamp.isoformat(),
                    'quelle': 'email',
                    'original_subject': parsed_email.original_subject
                }
                
                # Zusätzliche Fahrzeugdaten falls vorhanden
                fahrzeug_data = {}
                if parsed_email.marke:
                    fahrzeug_data['marke'] = parsed_email.marke
                if parsed_email.farbe:
                    fahrzeug_data['farbe'] = parsed_email.farbe
                
                # Bestehende FlowersHandler-Logik nutzen
                result = self.flowers_handler.process_status_update(
                    webhook_data, 
                    fahrzeug_additional_data=fahrzeug_data
                )
                
                if not result:
                    logger.error(f"Fehler beim Speichern der E-Mail für FIN {parsed_email.fin}")
                    return False
                    
            logger.info(f"{len(parsed_emails)} E-Mails erfolgreich in BigQuery gespeichert")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern in BigQuery: {e}")
            return False

# Zusätzliche Hilfsfunktionen für FastAPI-Integration

def process_flowers_emails() -> Dict[str, any]:
    """Hauptfunktion für E-Mail-Verarbeitung (für Scheduler)"""
    try:
        email_handler = EmailHandler()
        
        # E-Mails abrufen und parsen
        parsed_emails = email_handler.process_unread_emails()
        
        if not parsed_emails:
            return {
                'success': True,
                'message': 'Keine neuen E-Mails gefunden',
                'processed_count': 0
            }
        
        # In BigQuery speichern
        success = email_handler.save_to_bigquery(parsed_emails)
        
        return {
            'success': success,
            'message': f'{len(parsed_emails)} E-Mails verarbeitet',
            'processed_count': len(parsed_emails),
            'emails': [
                {
                    'fin': email.fin,
                    'prozess': email.prozess_name,
                    'status': email.status,
                    'bearbeiter': email.bearbeiter
                }
                for email in parsed_emails
            ]
        }
        
    except Exception as e:
        logger.error(f"Fehler bei E-Mail-Verarbeitung: {e}")
        return {
            'success': False,
            'message': f'Fehler: {str(e)}',
            'processed_count': 0
        }