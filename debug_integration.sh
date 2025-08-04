#!/bin/bash
# debug_integration.sh - Schrittweise BigQuery Integration

echo "🔍 BigQuery Integration Debug"

# 1. Python Path und Module prüfen
echo "1. Python Environment prüfen..."
source venv/bin/activate
echo "Python Path: $PYTHONPATH"
echo "Current Directory: $(pwd)"

# 2. Services Verzeichnis prüfen
echo -e "\n2. Services Verzeichnis:"
ls -la src/services/ || echo "❌ Services Verzeichnis nicht gefunden"

# 3. Python Module Test
echo -e "\n3. Python Import Test..."
cd src
python3 -c "
try:
    import sys
    sys.path.append('..')
    from services.bigquery_service import BigQueryService
    print('✅ BigQuery Service import erfolgreich')
except Exception as e:
    print(f'❌ Import Fehler: {e}')
"
cd ..

# 4. Alternative: BigQuery Service direkt in main.py integrieren
echo -e "\n4. Creating integrated main.py..."
cat > src/main_integrated.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, date
import os
import uuid
import logging

# BigQuery direkt importieren
try:
    from google.cloud import bigquery
    BIGQUERY_AVAILABLE = True
    print("✅ BigQuery verfügbar")
except ImportError:
    BIGQUERY_AVAILABLE = False
    print("⚠️ BigQuery nicht verfügbar")

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RA Autohaus Tracker API",
    description="Multi-Source Fahrzeugprozess-Tracking für Reinhardt Automobile", 
    version="1.0.0"
)

# BigQuery Client (falls verfügbar)
if BIGQUERY_AVAILABLE:
    try:
        bq_client = bigquery.Client(project="ra-autohaus-tracker")
        logger.info("BigQuery Client initialisiert")
    except Exception as e:
        logger.error(f"BigQuery Client Fehler: {e}")
        bq_client = None
else:
    bq_client = None

# In-Memory Fallback
vehicles_db = {}
processes_db = {}

class VehicleCreate(BaseModel):
    fin: str = Field(..., min_length=17, max_length=17)
    marke: str
    modell: str
    antriebsart: str
    farbe: str
    baujahr: Optional[int] = None

class ProcessCreate(BaseModel):
    fin: str = Field(..., min_length=17, max_length=17)
    prozess_typ: str
    bearbeiter: Optional[str] = None
    prioritaet: Optional[int] = Field(5, ge=1, le=10)
    anlieferung_datum: Optional[date] = None
    notizen: Optional[str] = None

async def save_vehicle_to_bigquery(vehicle_data: dict) -> bool:
    """Fahrzeug in BigQuery speichern"""
    if not bq_client:
        return False
    
    try:
        table_id = "ra-autohaus-tracker.autohaus.fahrzeuge_stamm"
        table = bq_client.get_table(table_id)
        
        row = {
            "fin": vehicle_data["fin"],
            "marke": vehicle_data["marke"],
            "modell": vehicle_data["modell"],
            "antriebsart": vehicle_data["antriebsart"],
            "farbe": vehicle_data["farbe"],
            "baujahr": vehicle_data.get("baujahr"),
            "ersterfassung_datum": datetime.now(),
            "aktiv": True
        }
        
        errors = bq_client.insert_rows_json(table, [row])
        if errors:
            logger.error(f"BigQuery errors: {errors}")
            return False
        
        logger.info(f"Vehicle saved to BigQuery: {vehicle_data['fin']}")
        return True
        
    except Exception as e:
        logger.error(f"BigQuery save error: {e}")
        return False

@app.get("/")
async def root():
    return {
        "message": "RA Autohaus Tracker API",
        "version": "1.0.0",
        "docs": "/docs",
        "bigquery_available": BIGQUERY_AVAILABLE
    }

@app.get("/health")
async def health_check():
    """Health Check mit BigQuery Status"""
    bigquery_status = "healthy" if bq_client else "unavailable"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "services": {
            "api": "healthy",
            "bigquery": bigquery_status,
            "bigquery_available": BIGQUERY_AVAILABLE
        }
    }

@app.post("/fahrzeuge", status_code=201)
async def create_fahrzeug(fahrzeug: VehicleCreate):
    """Fahrzeug anlegen (BigQuery + Memory Fallback)"""
    try:
        # Versuche BigQuery
        bigquery_success = await save_vehicle_to_bigquery(fahrzeug.dict())
        
        # Fallback: In-Memory speichern
        if not bigquery_success:
            logger.warning("BigQuery nicht verfügbar, speichere in Memory")
            vehicles_db[fahrzeug.fin] = {
                **fahrzeug.dict(),
                "erstellt_am": datetime.now().isoformat()
            }
        
        return {
            "message": "Fahrzeug erfolgreich angelegt",
            "fin": fahrzeug.fin,
            "storage": "bigquery" if bigquery_success else "memory"
        }
        
    except Exception as e:
        logger.error(f"Error creating vehicle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fahrzeuge")
async def list_fahrzeuge():
    """Fahrzeuge auflisten"""
    if bq_client:
        try:
            query = """
            SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
            WHERE aktiv = TRUE
            ORDER BY ersterfassung_datum DESC
            LIMIT 50
            """
            result = bq_client.query(query)
            vehicles = [dict(row) for row in result]
            
            return {
                "fahrzeuge": vehicles,
                "anzahl": len(vehicles),
                "source": "bigquery"
            }
        except Exception as e:
            logger.error(f"BigQuery query error: {e}")
    
    # Fallback: Memory
    return {
        "fahrzeuge": list(vehicles_db.values()),
        "anzahl": len(vehicles_db),
        "source": "memory"
    }

@app.get("/test/bigquery")
async def test_bigquery():
    """BigQuery Verbindung testen"""
    if not bq_client:
        return {"status": "BigQuery Client nicht verfügbar"}
    
    try:
        # Einfache Test-Query
        query = "SELECT 1 as test"
        result = bq_client.query(query)
        list(result)  # Query ausführen
        
        return {
            "status": "BigQuery Verbindung erfolgreich",
            "project": bq_client.project,
            "location": bq_client.location
        }
    except Exception as e:
        return {
            "status": "BigQuery Fehler", 
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
EOF

echo "✅ Integrierte main.py erstellt"
echo ""
echo "📝 Test-Schritte:"
echo "1. cp src/main_integrated.py src/main.py"
echo "2. uvicorn src.main:app --reload --host 0.0.0.0 --port 8080"
echo "3. curl http://localhost:8080/health"
echo "4. curl http://localhost:8080/test/bigquery"