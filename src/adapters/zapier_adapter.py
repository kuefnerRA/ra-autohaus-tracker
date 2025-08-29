# src/adapters/zapier_adapter.py
from datetime import datetime, date
from typing import Dict, Any
import logging

# Absolute Imports für Module
from models.integration import ZapierInput, UnifiedProcessData

logger = logging.getLogger(__name__)


class ZapierAdapter:
    """Konvertiert Zapier-JSON zu einheitlichem Format"""
    
    @staticmethod
    def convert_to_unified(zapier_json: Dict[str, Any]) -> UnifiedProcessData:
        """Zapier JSON → UnifiedProcessData"""
        
        # Flexible Eingangsdaten parsen
        zapier_input = ZapierInput(**zapier_json)
        
        # Pflichtfelder extrahieren
        fin = zapier_input.get_fin()
        prozess_typ = zapier_input.get_prozess_typ()
        status = zapier_input.get_status()
        
        if not fin or not prozess_typ or not status:
            missing = []
            if not fin: missing.append("fin")
            if not prozess_typ: missing.append("prozess_typ") 
            if not status: missing.append("status")
            raise ValueError(f"Missing required fields: {missing}")
        
        # Datum konvertieren falls vorhanden
        datum_erstzulassung = None
        if zapier_input.datum_erstzulassung:
            try:
                datum_erstzulassung = datetime.strptime(
                    zapier_input.datum_erstzulassung, '%d.%m.%Y'
                ).date()
            except Exception as e:
                logger.warning(f"Datum parsing failed: {e}")
        
        return UnifiedProcessData(
            fin=fin,
            prozess_typ=prozess_typ,
            status=status,
            bearbeiter=zapier_input.get_bearbeiter(),
            prioritaet=zapier_input.prioritaet or 5,  # FIX: Default-Wert hinzugefügt
            notizen=zapier_input.notizen,
            datenquelle="zapier",
            
            # Fahrzeugdaten
            marke=zapier_input.marke,
            modell=zapier_input.modell,
            antriebsart=zapier_input.antriebsart,
            farbe=zapier_input.farbe,
            baujahr=zapier_input.baujahr,
            datum_erstzulassung=datum_erstzulassung,
            kw_leistung=zapier_input.kw_leistung,
            km_stand=zapier_input.km_stand,
            anzahl_fahrzeugschluessel=zapier_input.anzahl_fahrzeugschluessel,
            bereifungsart=zapier_input.bereifungsart,
            anzahl_vorhalter=zapier_input.anzahl_vorhalter,
            ek_netto=zapier_input.ek_netto,
            besteuerungsart=zapier_input.besteuerungsart
        )