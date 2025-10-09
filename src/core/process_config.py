"""
Zentrale Prozesskonfiguration für RA Autohaus Tracker
Alle prozessbezogenen Einstellungen an einem Ort
"""

from typing import List

class ProcessConfig:
    """Zentrale Konfiguration für alle Prozesstypen"""
    
    # SLA-Definitionen in Stunden
    SLA_HOURS = {
        "Einkauf": 48,       # 2 Tage
        "Anlieferung": 24,   # 1 Tag
        "Aufbereitung": 72,  # 3 Tage
        "Foto": 24,          # 1 Tag
        "Werkstatt": 168,    # 7 Tage (einheitlich!)
        "Verkauf": 720,      # 30 Tage
        "Gewährleistung": 48,  # 2 Tage
    }
    
    # Prioritätsbereiche [min, max]
    PRIORITY_RANGES = {
        "Einkauf": [1, 3],
        "Anlieferung": [2, 4],
        "Aufbereitung": [3, 5],
        "Foto": [4, 6],
        "Werkstatt": [2, 5],
        "Verkauf": [1, 3],
        "Gewährleistung": [1, 2],  # Hohe Priorität
    }
    
    # Kombinierte Konfiguration - DIREKT DEFINIERT ohne Comprehension
    PROCESS_CONFIG = {
        "Einkauf": {"sla_stunden": 48, "priority_range": [1, 3]},
        "Anlieferung": {"sla_stunden": 24, "priority_range": [2, 4]},
        "Aufbereitung": {"sla_stunden": 72, "priority_range": [3, 5]},
        "Foto": {"sla_stunden": 24, "priority_range": [4, 6]},
        "Werkstatt": {"sla_stunden": 168, "priority_range": [2, 5]},
        "Verkauf": {"sla_stunden": 720, "priority_range": [1, 3]},
        "Gewährleistung": {"sla_stunden": 48, "priority_range": [1, 2]},
    }
    
    # Spezielle Prozesstypen die keine normalen Geschäftsprozesse sind
    SPECIAL_PROCESS_TYPES = ["Bearbeiterwechsel", "Deadlinewechsel"]
    
    @classmethod
    def get_sla_hours(cls, prozess_typ: str) -> int:
        """Gibt SLA-Stunden für Prozesstyp zurück"""
        return cls.SLA_HOURS.get(prozess_typ, 72)  # Default 3 Tage
    
    @classmethod
    def get_priority_range(cls, prozess_typ: str) -> List[int]:
        """Gibt Prioritätsbereich für Prozesstyp zurück"""
        return cls.PRIORITY_RANGES.get(prozess_typ, [3, 5])  # Default mittlere Priorität
    
    @classmethod
    def is_special_process(cls, prozess_typ: str) -> bool:
        """Prüft ob es ein spezieller Prozesstyp ist"""
        return prozess_typ in cls.SPECIAL_PROCESS_TYPES