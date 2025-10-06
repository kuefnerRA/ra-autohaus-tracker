"""
VIN/FIN Decoder Service
Dekodiert Fahrzeugidentifikationsnummern nach ISO 3779
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class VINDecoderService:
    """
    Service zur Dekodierung von Fahrzeugidentifikationsnummern.
    Extrahiert Hersteller und Grunddaten aus der FIN.
    """
    
    # WMI (World Manufacturer Identifier) Mappings - erste 3 Zeichen
    WMI_MAPPINGS = {
        # Deutsche Hersteller
        "WVW": {"marke": "Volkswagen", "land": "Deutschland"},
        "WVG": {"marke": "Volkswagen", "land": "Deutschland"},
        "WV1": {"marke": "Volkswagen Nutzfahrzeuge", "land": "Deutschland"},
        "WV2": {"marke": "Volkswagen Nutzfahrzeuge", "land": "Deutschland"},
        
        "WAU": {"marke": "Audi", "land": "Deutschland"},
        "WUA": {"marke": "Audi", "land": "Deutschland"},
        "WA1": {"marke": "Audi", "land": "Deutschland"},
        
        "WBA": {"marke": "BMW", "land": "Deutschland"},
        "WBS": {"marke": "BMW M", "land": "Deutschland"},
        "WBX": {"marke": "BMW", "land": "Deutschland"},
        
        "WDB": {"marke": "Mercedes-Benz", "land": "Deutschland"},
        "WDC": {"marke": "Mercedes-Benz", "land": "Deutschland"},
        "WDD": {"marke": "Mercedes-Benz", "land": "Deutschland"},
        "WDF": {"marke": "Mercedes-Benz", "land": "Deutschland"},
        
        "W0L": {"marke": "Opel", "land": "Deutschland"},
        "W0V": {"marke": "Opel", "land": "Deutschland"},
        
        "WP0": {"marke": "Porsche", "land": "Deutschland"},
        "WP1": {"marke": "Porsche", "land": "Deutschland"},
        
        # Spanische Hersteller
        "VSS": {"marke": "SEAT", "land": "Spanien"},
        "VSX": {"marke": "CUPRA", "land": "Spanien"},
        
        # Tschechische Hersteller
        "TMB": {"marke": "Skoda", "land": "Tschechien"},
        "TMP": {"marke": "Skoda", "land": "Tschechien"},
        "TMT": {"marke": "Skoda", "land": "Tschechien"},
        
        # Französische Hersteller
        "VF1": {"marke": "Renault", "land": "Frankreich"},
        "VF2": {"marke": "Renault", "land": "Frankreich"},
        "VF3": {"marke": "Peugeot", "land": "Frankreich"},
        "VF7": {"marke": "Citroën", "land": "Frankreich"},
        
        # Italienische Hersteller
        "ZFA": {"marke": "Fiat", "land": "Italien"},
        "ZFC": {"marke": "Fiat", "land": "Italien"},
        "ZFF": {"marke": "Ferrari", "land": "Italien"},
        "ZHW": {"marke": "Alfa Romeo", "land": "Italien"},
        "ZAR": {"marke": "Alfa Romeo", "land": "Italien"},
        
        # US-Hersteller
        "1FA": {"marke": "Ford", "land": "USA"},
        "1FB": {"marke": "Ford", "land": "USA"},
        "1G1": {"marke": "Chevrolet", "land": "USA"},
        "1GC": {"marke": "Chevrolet", "land": "USA"},
        
        # Japanische Hersteller
        "JHM": {"marke": "Honda", "land": "Japan"},
        "JHG": {"marke": "Honda", "land": "Japan"},
        "JMB": {"marke": "Mitsubishi", "land": "Japan"},
        "JMZ": {"marke": "Mazda", "land": "Japan"},
        "JN1": {"marke": "Nissan", "land": "Japan"},
        "JT1": {"marke": "Toyota", "land": "Japan"},
        "JT2": {"marke": "Toyota", "land": "Japan"},
        
        # Koreanische Hersteller
        "KMH": {"marke": "Hyundai", "land": "Südkorea"},
        "KNA": {"marke": "Kia", "land": "Südkorea"},
    }
    
    # Modelljahr-Codes (10. Stelle der FIN)
    YEAR_CODES = {
        'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014,
        'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019,
        'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024,
        'S': 2025, 'T': 2026, 'V': 2027, 'W': 2028, 'X': 2029,
        'Y': 2030, '1': 2031, '2': 2032, '3': 2033, '4': 2034,
        '5': 2035, '6': 2036, '7': 2037, '8': 2038, '9': 2039,
    }
    
    @classmethod
    def decode_fin(cls, fin: str) -> Dict[str, Any]:
        """
        Dekodiert eine FIN und extrahiert verfügbare Informationen.
        
        Args:
            fin: 17-stellige Fahrzeugidentifikationsnummer
            
        Returns:
            Dict mit extrahierten Fahrzeugdaten
        """
        if not fin or len(fin) != 17:
            logger.warning(f"Ungültige FIN-Länge: {len(fin) if fin else 0}")
            return {"marke": "Unbekannt", "dekodiert": False}
        
        fin_upper = fin.upper()
        result = {"fin": fin_upper, "dekodiert": False}
        
        # WMI (Hersteller) dekodieren - erste 3 Zeichen
        wmi = fin_upper[:3]
        manufacturer_info = cls.WMI_MAPPINGS.get(wmi)
        
        if manufacturer_info:
            result.update(manufacturer_info)
            result["dekodiert"] = True
            logger.info(f"✅ FIN dekodiert: {fin} -> {manufacturer_info['marke']}")
        else:
            # Versuche mit ersten 2 Zeichen (manche Hersteller)
            wmi_2 = fin_upper[:2]
            for key, value in cls.WMI_MAPPINGS.items():
                if key.startswith(wmi_2):
                    result.update(value)
                    result["dekodiert"] = True
                    result["teilweise_dekodiert"] = True
                    logger.info(f"⚠️ FIN teilweise dekodiert: {fin} -> {value['marke']}")
                    break
        
        # Modelljahr dekodieren (10. Stelle)
        if len(fin_upper) >= 10:
            year_code = fin_upper[9]
            if year_code in cls.YEAR_CODES:
                result["baujahr"] = cls.YEAR_CODES[year_code]
                result["modelljahr_dekodiert"] = True
        
        # Wenn nichts gefunden
        if not result.get("dekodiert"):
            result["marke"] = "Unbekannt"
            result["hinweis"] = f"WMI '{wmi}' nicht in Datenbank"
            logger.debug(f"❓ Unbekannte WMI: {wmi} für FIN {fin}")
        
        return result
    
    @classmethod
    def validate_fin(cls, fin: str) -> Dict[str, Any]:
        """
        Validiert eine FIN auf Plausibilität.
        
        Returns:
            Dict mit valid (bool) und errors (list)
        """
        errors = []
        
        if not fin:
            errors.append("FIN ist leer")
            return {"valid": False, "errors": errors}
        
        if len(fin) != 17:
            errors.append(f"FIN muss 17 Zeichen haben (hat {len(fin)})")
        
        # Prüfe auf ungültige Zeichen (I, O, Q sind nicht erlaubt)
        invalid_chars = set('IOQ')
        if any(c in invalid_chars for c in fin.upper()):
            errors.append("FIN enthält ungültige Zeichen (I, O oder Q)")
        
        # Prüfe ob alphanumerisch
        if not fin.replace('-', '').replace(' ', '').isalnum():
            errors.append("FIN darf nur Buchstaben und Zahlen enthalten")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    @classmethod
    async def enrich_vehicle_batch(cls, vehicle_service, limit: int = 100) -> Dict[str, Any]:
        """
        Batch-Prozess um Fahrzeuge ohne Marke anzureichern.
        
        Args:
            vehicle_service: VehicleService Instanz
            limit: Maximale Anzahl zu verarbeitender Fahrzeuge
            
        Returns:
            Statistiken über den Anreicherungsprozess
        """
        stats = {
            "processed": 0,
            "enriched": 0,
            "failed": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Hole Fahrzeuge ohne Marke - KORRIGIERT
            query = f"""
            SELECT fin, marke 
            FROM `{vehicle_service.bigquery_service.dataset_ref}.fahrzeuge_stamm`
            WHERE marke = 'Unbekannt' OR marke IS NULL
            LIMIT {limit}
            """
            
            vehicles = await vehicle_service.bigquery_service.execute_query(query)
            stats["total"] = len(vehicles)
            
            for vehicle in vehicles:
                fin = vehicle.get('fin')
                if not fin:
                    continue
                
                stats["processed"] += 1
                
                # Dekodiere FIN
                decoded = cls.decode_fin(fin)
                
                if decoded.get("dekodiert") and decoded.get("marke") != "Unbekannt":
                    # Update Fahrzeug
                    update_data = {"marke": decoded["marke"]}
                    
                    # Füge Baujahr hinzu wenn dekodiert
                    if decoded.get("baujahr"):
                        update_data["baujahr"] = decoded["baujahr"]
                    
                    try:
                        await vehicle_service.update_vehicle(
                            fin=fin,
                            update_data=update_data,
                            create_update_process=False
                        )
                        stats["enriched"] += 1
                        logger.info(f"✅ Fahrzeug {fin} angereichert: {decoded['marke']}")
                    except Exception as e:
                        stats["failed"] += 1
                        logger.error(f"❌ Update fehlgeschlagen für {fin}: {e}")
                else:
                    logger.debug(f"⏭️ Keine Anreicherung möglich für {fin}")
            
            logger.info(f"📊 Batch-Anreicherung abgeschlossen: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Batch-Anreicherung fehlgeschlagen: {e}")
            stats["error"] = str(e)
            return stats