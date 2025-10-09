"""
Zentrale Mappings für RA Autohaus Tracker
Alle Normalisierungen an einer Stelle
"""

from typing import Dict, Optional

class CentralMappings:
    """Zentrale Mapping-Definitionen für das gesamte System"""
    
    # =====================================
    # PROZESS-TYP MAPPINGS
    # =====================================
    PROZESS_MAPPINGS: Dict[str, str] = {
        # Zapier/Externe Namen -> Interne Namen
        "gwa": "Aufbereitung",
        "garage": "Werkstatt",
        "werkstatt": "Werkstatt",
        "aufbereitung": "Aufbereitung",
        "foto": "Foto",
        "photos": "Foto",
        "fotoshooting": "Foto",
        "verkauf": "Verkauf",
        "sales": "Verkauf",
        "einkauf": "Einkauf",
        "purchase": "Einkauf",
        "anlieferung": "Anlieferung",
        "delivery": "Anlieferung",
        "fahrzeuganlage": "Einkauf",
        "(1) da fahrzeuganlage": "Einkauf",
        "(0) start fahrzeugaufbereitung": "Aufbereitung",
        "(1) aufbereitung in arbeit": "Aufbereitung",
        "(4.0) werkstattplanung": "Werkstatt",
        "aufbereitung in arbeit": "Aufbereitung",
        # Spezielle Prozesstypen
        "bearbeiterwechsel": "Bearbeiterwechsel",
        "bearbeiter-wechsel": "Bearbeiterwechsel", 
        "bearbeiter wechsel": "Bearbeiterwechsel",
        "deadlinewechsel": "Deadlinewechsel",
        "deadline-wechsel": "Deadlinewechsel",
        "deadline wechsel": "Deadlinewechsel",
        "deadline änderung": "Deadlinewechsel",
        "deadline-änderung": "Deadlinewechsel",
        "Gewährleistung": "Gewährleistung",
        "Gewaehrleistung": "Gewährleistung",
        "gewährleistung": "Gewährleistung",
    }
    
    # =====================================
    # STATUS MAPPINGS
    # =====================================
    STATUS_MAPPINGS: Dict[str, str] = {
        # Verschiedene Schreibweisen -> Einheitlicher Status
        # WARTESCHLANGE Varianten
        "gestartet": "WARTESCHLANGE",
        "angelegt": "WARTESCHLANGE",
        "wartend": "WARTESCHLANGE",
        "neu": "WARTESCHLANGE",
        "warteschlange": "WARTESCHLANGE",
        "fwd: gestartet": "WARTESCHLANGE",
        "fwd:  gestartet": "WARTESCHLANGE",
        "Start": "WARTESCHLANGE",
        
        # AKTIV Varianten
        "in bearbeitung": "AKTIV",
        "in_bearbeitung": "AKTIV",
        "laufend": "AKTIV",
        "in arbeit": "AKTIV",
        "bearbeitung": "AKTIV",
        "aktiv": "AKTIV",
        
        # BEENDET Varianten
        "beendet": "BEENDET",
        "abgeschlossen": "BEENDET",
        "fertig": "BEENDET",
        "erledigt": "BEENDET",
        "komplett": "BEENDET",
        "verkauft": "BEENDET",
        
        # EMAIL-Status
        "e-mail empfangen": "WARTESCHLANGE",
        "email empfangen": "WARTESCHLANGE",
        
        # Sonstige
        "test": "WARTESCHLANGE",
    }
    
    # =====================================
    # BEARBEITER MAPPINGS
    # =====================================
    BEARBEITER_MAPPINGS: Dict[str, str] = {
        "Thomas K.": "Thomas Küfner",
        "Max R.": "Maximilian Reinhardt",
        "Thomas": "Thomas Küfner",
        "Max": "Maximilian Reinhardt",
        "T. Küfner": "Thomas Küfner",
        "M. Reinhardt": "Maximilian Reinhardt",
        "Hans M.": "Hans Müller",
        "Anna K.": "Anna Klein",
    }
    
    # =====================================
    # NORMALISIERUNGS-METHODEN
    # =====================================
    
    @classmethod
    def normalize_prozess_typ(cls, prozess_raw: Optional[str]) -> str:
        """Normalisiert Prozesstyp zu einheitlichem Format"""
        if not prozess_raw:
            return "Aufbereitung"  # Default
        
        prozess_lower = str(prozess_raw).lower().strip()
        return cls.PROZESS_MAPPINGS.get(prozess_lower, prozess_raw)
    
    @classmethod
    def normalize_status(cls, status_raw: Optional[str]) -> str:
        """Normalisiert Status zu einheitlichem Format"""
        if not status_raw:
            return "WARTESCHLANGE"  # Default
        
        status_lower = str(status_raw).lower().strip()
        return cls.STATUS_MAPPINGS.get(status_lower, status_raw.upper())
    
    @classmethod
    def normalize_bearbeiter(cls, bearbeiter_raw: Optional[str]) -> Optional[str]:
        """Normalisiert Bearbeiter-Namen"""
        if not bearbeiter_raw:
            return None
        
        bearbeiter = str(bearbeiter_raw).strip()
        return cls.BEARBEITER_MAPPINGS.get(bearbeiter, bearbeiter)
    
    @classmethod
    def extract_prozess_from_text(cls, text: str) -> str:
        """Extrahiert Prozesstyp aus Freitext (für Email-Parser)"""
        text_lower = text.lower()
        
        # Keyword-basierte Erkennung
        keywords = {
            "Verkauf": ["verkauf", "verkaufsbereit", "verkäufer", "vk"],
            "Foto": ["foto", "fotografiert", "bilder", "fotos", "shooting"],
            "Werkstatt": ["werkstatt", "reparatur", "service", "inspektion", "garage"],
            "Aufbereitung": ["aufbereitung", "gwa", "reinigung", "politur"],
            "Anlieferung": ["anlieferung", "angekommen", "eingetroffen", "angemeldet"],
            "Einkauf": ["einkauf", "angekauft", "erworben", "gekauft"],
        }
        
        for prozess_typ, words in keywords.items():
            if any(word in text_lower for word in words):
                return prozess_typ
        
        return "Aufbereitung"  # Default
    
    @classmethod
    def extract_status_from_text(cls, text: str) -> str:
        """Extrahiert Status aus Freitext (für Email-Parser)"""
        text_lower = text.lower()
        
        # Keyword-basierte Erkennung
        keywords = {
            "BEENDET": ["fertig", "abgeschlossen", "beendet", "erledigt", "komplett"],
            "AKTIV": ["läuft", "in bearbeitung", "aktiv", "arbeite", "dabei"],
            "WARTESCHLANGE": ["wartet", "wartend", "bereit für", "angemeldet", "eingetroffen"],
        }
        
        for status, words in keywords.items():
            if any(word in text_lower for word in words):
                return status
        
        return "WARTESCHLANGE"  # Default