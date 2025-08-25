# tests/test_flowers_handler.py
import pytest
from src.handlers.flowers_handler import FlowersHandler

class TestFlowersHandler:
    
    def setup_method(self):
        self.handler = FlowersHandler()
    
    def test_prozess_normalisierung(self):
        test_cases = [
            ("gwa", "Aufbereitung"),
            ("GWA", "Aufbereitung"),
            ("garage", "Werkstatt"),
            ("fotoshooting", "Foto"),
            ("unbekannt", "unbekannt")  # Fallback
        ]
        
        for input_val, expected in test_cases:
            result = self.handler.normalize_prozess_typ(input_val)
            assert result == expected, f"'{input_val}' sollte '{expected}' ergeben, nicht '{result}'"
    
    def test_fin_extraktion(self):
        test_texts = [
            ("FIN: WBA12345678901234", "WBA12345678901234"),
            ("Fahrzeug WBA12345678901234 bereit", "WBA12345678901234"),
            ("Kein FIN hier", None)
        ]
        
        for text, expected in test_texts:
            result = self.handler.extract_fin_from_text(text)
            assert result == expected