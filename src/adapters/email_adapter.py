# src/adapters/email_adapter.py
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Absolute Imports
from src.models.integration import EmailInput, UnifiedProcessData

logger = logging.getLogger(__name__)


class EmailAdapter:
    """Konvertiert E-Mail-Daten zu einheitlichem Format"""
    
    def __init__(self):
        # Regex-Patterns für E-Mail-Parsing
        self.patterns = {
            'fin': re.compile(r'FIN:\s*([A-Z0-9]{15,17})', re.IGNORECASE),
            'marke': re.compile(r'Marke:\s*([^\n\r]+)', re.IGNORECASE),
            'farbe': re.compile(r'Farbe:\s*([^\n\r]+)', re.IGNORECASE),
            'bearbeiter': re.compile(r'Bearbeiter:\s*([^\n\r]+)', re.IGNORECASE),
            'modell': re.compile(r'Modell:\s*([^\n\r]+)', re.IGNORECASE),
            'prioritaet': re.compile(r'Priorität:\s*([1-9]|10)', re.IGNORECASE)
        }
        
        # Betreff-Pattern: "GWA gestartet" -> ('GWA', 'gestartet')
        self.subject_pattern = re.compile(
            r'^([A-Za-z0-9_\-\s]+)\s+(gestartet|abgeschlossen|pausiert|warteschlange|fertig|completed)$', 
            re.IGNORECASE
        )
    
    def parse_email_subject(self, subject: str) -> Tuple[Optional[str], Optional[str]]:
        """Betreff parsen: 'GWA gestartet' -> ('GWA', 'gestartet')"""
        match = self.subject_pattern.match(subject.strip())
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None, None
    
    def parse_email_body(self, body: str) -> Dict[str, Any]:
        """E-Mail-Body nach Flowers-Feldern durchsuchen"""
        parsed_data = {}
        
        # HTML entfernen falls vorhanden
        if '<html>' in body.lower():
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(body, 'html.parser')
                body = soup.get_text()
            except ImportError:
                # BeautifulSoup nicht verfügbar - einfaches HTML-Tag-Entfernen
                import re
                body = re.sub(r'<[^>]+>', '', body)
        
        # Alle Patterns anwenden
        for field_name, pattern in self.patterns.items():
            match = pattern.search(body)
            if match:
                value = match.group(1).strip()
                if value:
                    if field_name == 'prioritaet':
                        parsed_data[field_name] = int(value)
                    else:
                        parsed_data[field_name] = value
        
        return parsed_data
    
    def convert_to_unified(self, email_data: Dict[str, Any]) -> UnifiedProcessData:
        """E-Mail-Daten → UnifiedProcessData"""
        
        subject = email_data.get('betreff', '')
        body = email_data.get('inhalt', '')
        
        # Betreff und Body parsen
        prozess_raw, status_raw = self.parse_email_subject(subject)
        body_data = self.parse_email_body(body)
        
        # Validierung
        fin = body_data.get('fin')
        if not fin:
            raise ValueError("Keine FIN in E-Mail gefunden")
        
        if not prozess_raw:
            raise ValueError(f"Prozess-Typ konnte nicht aus Betreff extrahiert werden: {subject}")
        
        if not status_raw:
            raise ValueError(f"Status konnte nicht aus Betreff extrahiert werden: {subject}")
        
        return UnifiedProcessData(
            fin=fin,
            prozess_typ=prozess_raw,
            status=status_raw,
            bearbeiter=body_data.get('bearbeiter'),
            prioritaet=body_data.get('prioritaet', 5),
            notizen=f"E-Mail: {subject}",
            datenquelle="email",
            external_timestamp=email_data.get('empfangen_am'),
            
            # Fahrzeugdaten aus E-Mail
            marke=body_data.get('marke'),
            farbe=body_data.get('farbe'),
            modell=body_data.get('modell')
        )