"""
Data Transformer für eingehende Zapier/External Daten
Transformiert Rohdaten in Pydantic-kompatible Formate
"""

import re
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class DataTransformer:
    """Transformiert externe Daten in interne Formate"""
    
    @staticmethod
    def transform_zapier_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transformiert Zapier-Daten in Pydantic-kompatible Formate
        
        Args:
            data: Rohdaten von Zapier
            
        Returns:
            Transformierte Daten
        """
        transformed = {}

            # DEBUG: Eingangsdaten prüfen
        logger.info(f"🔍 DEBUG - Eingangsdaten: {list(data.keys())}")
        logger.info(f"🔍 DEBUG - neuer_status vorhanden: {'neuer_status' in data}")
        logger.info(f"🔍 DEBUG - neuer_status Wert: {data.get('neuer_status')}")

        # WICHTIG: Status-Mapping hinzufügen
        # Zapier sendet "neuer_status", wir brauchen "status"
        if 'neuer_status' in data and data['neuer_status']:
            # Bereinige doppelte Anführungszeichen
            status_value = str(data['neuer_status']).strip().strip('"').strip("'")
            transformed['status'] = status_value
            logger.debug(f"Mapped: neuer_status '{data['neuer_status']}' -> status '{status_value}'")
        elif 'status' in data and data['status']:
            status_value = str(data['status']).strip().strip('"').strip("'") 
            transformed['status'] = status_value
        
        # Prozess-Mapping
        # Zapier sendet "prozess_name", wir brauchen "prozess_typ"
        if 'prozess_name' in data and data['prozess_name']:
            transformed['prozess_typ'] = data['prozess_name']
            logger.debug(f"Mapped: prozess_name '{data['prozess_name']}' -> prozess_typ")
        elif 'prozess_typ' in data and data['prozess_typ']:
            transformed['prozess_typ'] = data['prozess_typ']
        
        # Direkt durchreichen (keine Transformation nötig)
        direct_fields = [
            'fin', 'marke', 'modell', 'antriebsart', 'farbe', 
            'bearbeiter'
        ]
        for field in direct_fields:
            if field in data and data[field] is not None:
                transformed[field] = data[field]
        
        # Integer-Felder
        transformed.update(DataTransformer._transform_integers(data))
        
        # Decimal-Felder (Deutsches Format -> Decimal)
        transformed.update(DataTransformer._transform_decimals(data))
        
        # Enum-Felder
        transformed.update(DataTransformer._transform_enums(data))
        
        # Datum-Felder
        transformed.update(DataTransformer._transform_dates(data))
        
        logger.info(f"✅ Daten transformiert: {len(transformed)} Felder")
        logger.debug(f"Transformierte Felder: {list(transformed.keys())}")
        return transformed
    
    @staticmethod
    def _transform_integers(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transformiert Integer-Felder"""
        result = {}
        
        # anzahl_fahrzeugschluessel: "2 Fahrzeugschlüssel" -> 2
        for key in ['anzahl_fahrzeugschluessel', 'anzahl_fahrzeugschlüssel']:
            if key in data and data[key]:
                value = data[key]
                if isinstance(value, str):
                    # Extrahiere erste Zahl aus String
                    match = re.search(r'(\d+)', value)
                    if match:
                        result['anzahl_fahrzeugschluessel'] = int(match.group(1))
                        logger.debug(f"Transformiert: {key} '{value}' -> {result['anzahl_fahrzeugschluessel']}")
                elif isinstance(value, (int, float)):
                    result['anzahl_fahrzeugschluessel'] = int(value)
        
        # anzahl_vorhalter: "2 Fahrzeughalter" -> 2
        if 'anzahl_vorhalter' in data and data['anzahl_vorhalter']:
            value = data['anzahl_vorhalter']
            if isinstance(value, str):
                match = re.search(r'(\d+)', value)
                if match:
                    result['anzahl_vorhalter'] = int(match.group(1))
                    logger.debug(f"Transformiert: anzahl_vorhalter '{value}' -> {result['anzahl_vorhalter']}")
            elif isinstance(value, (int, float)):
                result['anzahl_vorhalter'] = int(value)
        
        # Weitere Integer-Felder
        simple_int_fields = ['baujahr', 'kw_leistung', 'km_stand']
        for field in simple_int_fields:
            if field in data and data[field]:
                try:
                    # Entferne Tausender-Punkte falls vorhanden
                    value = str(data[field]).replace('.', '')
                    result[field] = int(value)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Konnte {field} nicht zu Integer konvertieren: {data[field]}")
        
        return result
    
    @staticmethod
    def _transform_decimals(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transformiert Decimal-Felder (Deutsches Format)"""
        result = {}
        
        # ek_netto: "21.454,08" -> Decimal
        if 'ek_netto' in data and data['ek_netto']:
            value = data['ek_netto']
            if isinstance(value, str):
                try:
                    # Deutsches Format: Punkt als Tausender, Komma als Dezimal
                    # Entferne Tausender-Punkte und ersetze Komma durch Punkt
                    clean_value = value.replace('.', '').replace(',', '.')
                    result['ek_netto'] = Decimal(clean_value)
                    logger.debug(f"Transformiert: ek_netto '{value}' -> {result['ek_netto']}")
                except Exception as e:
                    logger.warning(f"Konnte ek_netto nicht konvertieren: {value} - {e}")
            elif isinstance(value, (int, float)):
                result['ek_netto'] = Decimal(str(value))
        
        return result
    
    @staticmethod
    def _transform_enums(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transformiert Enum-Felder"""
        result = {}
        
        # bereifungsart: "4x bereift" / "8x bereift" -> Mapping
        if 'bereifungsart' in data and data['bereifungsart']:
            value = str(data['bereifungsart']).lower()
            if '8x' in value or 'allwetter' in value or 'ganzjahr' in value:
                result['bereifungsart'] = 'Ganzjahr'
            elif 'winter' in value:
                result['bereifungsart'] = 'Winter'
            elif 'sommer' in value:
                result['bereifungsart'] = 'Sommer'
            elif '4x' in value:
                # 4x bereift könnte Sommer oder Winter sein - Default: Sommer
                result['bereifungsart'] = 'Sommer'
            else:
                # Fallback
                result['bereifungsart'] = 'Sommer'
            logger.debug(f"Transformiert: bereifungsart '{data['bereifungsart']}' -> {result['bereifungsart']}")
        
        # besteuerungsart: "Regelbesteuert" -> "Regel"
        if 'besteuerungsart' in data and data['besteuerungsart']:
            value = str(data['besteuerungsart']).lower()
            if 'regel' in value:
                result['besteuerungsart'] = 'Regel'
            elif 'differenz' in value:
                result['besteuerungsart'] = 'Differenz'
            elif 'export' in value:
                result['besteuerungsart'] = 'Export'
            else:
                # Default
                result['besteuerungsart'] = 'Regel'
            logger.debug(f"Transformiert: besteuerungsart '{data['besteuerungsart']}' -> {result['besteuerungsart']}")
        
        # antriebsart: Normalisierung
        if 'antriebsart' in data and data['antriebsart']:
            value = str(data['antriebsart']).lower()
            if 'elektro' in value or 'electric' in value:
                result['antriebsart'] = 'Elektro'
            elif 'diesel' in value:
                result['antriebsart'] = 'Diesel'
            elif 'benzin' in value or 'petrol' in value:
                result['antriebsart'] = 'Benzin'
            elif 'plugin' in value or 'plug-in' in value:
                result['antriebsart'] = 'Plugin-Hybrid'
            elif 'hybrid' in value:
                result['antriebsart'] = 'Hybrid'
            elif 'erdgas' in value or 'cng' in value:
                result['antriebsart'] = 'Erdgas'
            elif 'autogas' in value or 'lpg' in value:
                result['antriebsart'] = 'Autogas'
            else:
                result['antriebsart'] = data['antriebsart']  # Original beibehalten
        
        return result
    
    @staticmethod
    def _transform_dates(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transformiert Datum-Felder"""
        result = {}
        
        date_fields = ['datum_erstzulassung']
        for field in date_fields:
            if field in data and data[field]:
                value = data[field]
                # Wenn bereits ein String im ISO-Format (YYYY-MM-DD), direkt übernehmen
                if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                    result[field] = value
                else:
                    # Versuche andere Formate zu parsen
                    try:
                        # Hier könnten weitere Datumsformate behandelt werden
                        result[field] = value
                    except Exception as e:
                        logger.warning(f"Konnte Datum {field} nicht parsen: {value}")
        
        return result