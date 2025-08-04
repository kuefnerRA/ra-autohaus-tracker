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
    logger = logging.getLogger(__name__)
    logger.info("✅ BigQuery verfügbar")
except ImportError:
    BIGQUERY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ BigQuery nicht verfügbar")

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)

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

class ProcessUpdate(BaseModel):
    status: str
    bearbeiter: Optional[str] = None
    notizen: Optional[str] = None

async def save_vehicle_to_bigquery(vehicle_data: dict) -> bool:
    """Fahrzeug in BigQuery speichern"""
    if not bq_client:
        logger.warning("BigQuery Client nicht verfügbar")
        return False
    
    try:
        table_id = "ra-autohaus-tracker.autohaus.fahrzeuge_stamm"
        table = bq_client.get_table(table_id)
        
        now_iso = datetime.now().isoformat()
        
        row = {
            "fin": vehicle_data["fin"],
            "marke": vehicle_data["marke"],
            "modell": vehicle_data["modell"],
            "antriebsart": vehicle_data["antriebsart"],
            "farbe": vehicle_data["farbe"],
            "baujahr": vehicle_data.get("baujahr"),
            "ersterfassung_datum": now_iso,
            "aktiv": True
        }
        
        row = {k: v for k, v in row.items() if v is not None}
        
        errors = bq_client.insert_rows_json(table, [row])
        if errors:
            logger.error(f"BigQuery errors: {errors}")
            return False
        
        logger.info(f"✅ Vehicle saved to BigQuery: {vehicle_data['fin']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ BigQuery save error: {e}")
        return False

async def save_process_to_bigquery(process_data: dict) -> bool:
    """Prozess in BigQuery speichern"""
    if not bq_client:
        return False
    
    try:
        table_id = "ra-autohaus-tracker.autohaus.fahrzeug_prozesse"
        table = bq_client.get_table(table_id)
        
        # DateTime-Objekte zu ISO Strings konvertieren
        row = {}
        for key, value in process_data.items():
            if isinstance(value, datetime):
                row[key] = value.isoformat()
            elif isinstance(value, date):
                row[key] = value.isoformat()
            elif value is not None:
                row[key] = value
        
        if "erstellt_am" not in row:
            row["erstellt_am"] = datetime.now().isoformat()
        
        logger.info(f"Inserting process into BigQuery: {row}")
        
        errors = bq_client.insert_rows_json(table, [row])
        if errors:
            logger.error(f"BigQuery process errors: {errors}")
            return False
        
        logger.info(f"✅ Process saved to BigQuery: {process_data['prozess_id']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ BigQuery process save error: {e}")
        return False

async def update_process_in_bigquery(prozess_id: str, update_data: Dict[str, Any]) -> bool:
    """Prozess in BigQuery aktualisieren"""
    if not bq_client:
        return False
    
    try:
        # Update Query bauen
        set_clauses = []
        query_params = [bigquery.ScalarQueryParameter("prozess_id", "STRING", prozess_id)]
        
        for key, value in update_data.items():
            if value is not None and key not in ['prozess_id']:
                set_clauses.append(f"{key} = @{key}")
                
                # Parameter-Typ bestimmen
                if isinstance(value, str):
                    param_type = "STRING"
                elif isinstance(value, int):
                    param_type = "INT64"
                elif isinstance(value, datetime):
                    param_type = "DATETIME"
                    value = value.isoformat()
                else:
                    param_type = "STRING"
                    value = str(value)
                
                query_params.append(bigquery.ScalarQueryParameter(key, param_type, value))
        
        if not set_clauses:
            logger.warning("Keine Update-Daten provided")
            return False
        
        # Aktualisierungs-Timestamp hinzufügen
        set_clauses.append("aktualisiert_am = CURRENT_DATETIME()")
        
        query = f"""
        UPDATE `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
        SET {', '.join(set_clauses)}
        WHERE prozess_id = @prozess_id
        """
        
        logger.info(f"Update query: {query}")
        logger.info(f"Parameters: {query_params}")
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        
        query_job = bq_client.query(query, job_config=job_config)
        result = query_job.result()
        
        # Prüfen ob Zeilen betroffen waren
        if query_job.num_dml_affected_rows == 0:
            logger.warning(f"Keine Zeilen aktualisiert für prozess_id: {prozess_id}")
            return False
        
        logger.info(f"✅ Prozess in BigQuery aktualisiert: {prozess_id} ({query_job.num_dml_affected_rows} Zeilen)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Prozess-Update Fehler: {e}")
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
    """Fahrzeug anlegen"""
    try:
        bigquery_success = await save_vehicle_to_bigquery(fahrzeug.dict())
        
        if not bigquery_success:
            logger.warning("BigQuery speichern fehlgeschlagen, verwende Memory")
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
    
    return {
        "fahrzeuge": list(vehicles_db.values()),
        "anzahl": len(vehicles_db),
        "source": "memory"
    }

@app.get("/fahrzeuge/{fin}")
async def get_fahrzeug(fin: str):
    """Einzelnes Fahrzeug abrufen"""
    if bq_client:
        try:
            query = """
            SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
            WHERE fin = @fin AND aktiv = TRUE
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("fin", "STRING", fin)
                ]
            )
            result = bq_client.query(query, job_config=job_config)
            vehicles = [dict(row) for row in result]
            
            if vehicles:
                return vehicles[0]
                
        except Exception as e:
            logger.error(f"BigQuery query error: {e}")
    
    if fin in vehicles_db:
        return vehicles_db[fin]
    
    raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")

@app.post("/prozesse/start", status_code=201)
async def start_prozess(prozess: ProcessCreate):
    """Neuen Prozess starten"""
    try:
        prozess_id = str(uuid.uuid4())
        
        process_data = {
            "prozess_id": prozess_id,
            **prozess.dict(),
            "status": "gestartet",
            "start_timestamp": datetime.now(),
            "datenquelle": "api"
        }
        
        bigquery_success = await save_process_to_bigquery(process_data)
        
        if not bigquery_success:
            logger.warning("BigQuery Process speichern fehlgeschlagen, verwende Memory")
            processes_db[prozess_id] = {
                **process_data,
                "start_timestamp": process_data["start_timestamp"].isoformat()
            }
        
        return {
            "message": "Prozess erfolgreich gestartet",
            "prozess_id": prozess_id,
            "fin": prozess.fin,
            "prozess_typ": prozess.prozess_typ,
            "storage": "bigquery" if bigquery_success else "memory"
        }
        
    except Exception as e:
        logger.error(f"Error starting process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/prozesse/{prozess_id}")
async def update_prozess(prozess_id: str, update: ProcessUpdate):
    """Prozess-Status aktualisieren"""
    try:
        update_data = update.dict(exclude_unset=True)
        
        # Bei Abschluss End-Timestamp setzen
        if update.status == "abgeschlossen":
            update_data["ende_timestamp"] = datetime.now()
        
        logger.info(f"Updating process {prozess_id} with data: {update_data}")
        
        success = await update_process_in_bigquery(prozess_id, update_data)
        
        if not success:
            # Fallback: In Memory suchen und updaten
            if prozess_id in processes_db:
                processes_db[prozess_id].update(update_data)
                success = True
                storage = "memory"
            else:
                raise HTTPException(status_code=404, detail=f"Prozess {prozess_id} nicht gefunden")
        else:
            storage = "bigquery"
        
        return {
            "message": "Prozess erfolgreich aktualisiert",
            "prozess_id": prozess_id,
            "status": update.status,
            "storage": storage
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/prozesse/{prozess_id}")
async def get_prozess(prozess_id: str):
    """Einzelnen Prozess abrufen"""
    if bq_client:
        try:
            query = """
            SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE prozess_id = @prozess_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("prozess_id", "STRING", prozess_id)
                ]
            )
            result = bq_client.query(query, job_config=job_config)
            processes = [dict(row) for row in result]
            
            if processes:
                return processes[0]
                
        except Exception as e:
            logger.error(f"BigQuery process query error: {e}")
    
    # Fallback: Memory
    if prozess_id in processes_db:
        return processes_db[prozess_id]
    
    raise HTTPException(status_code=404, detail="Prozess nicht gefunden")

@app.get("/prozesse")
async def list_prozesse(fin: Optional[str] = None, status: Optional[str] = None, limit: int = 50):
    """Alle Prozesse auflisten"""
    if bq_client:
        try:
            where_clauses = []
            query_params = []
            
            if fin:
                where_clauses.append("fin = @fin")
                query_params.append(bigquery.ScalarQueryParameter("fin", "STRING", fin))
            
            if status:
                where_clauses.append("status = @status")
                query_params.append(bigquery.ScalarQueryParameter("status", "STRING", status))
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
            SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE {where_clause}
            ORDER BY erstellt_am DESC
            LIMIT {limit}
            """
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params) if query_params else None
            result = bq_client.query(query, job_config=job_config)
            processes = [dict(row) for row in result]
            
            return {
                "prozesse": processes,
                "anzahl": len(processes),
                "source": "bigquery"
            }
                
        except Exception as e:
            logger.error(f"BigQuery processes query error: {e}")
    
    # Memory Fallback
    filtered = list(processes_db.values())
    if fin:
        filtered = [p for p in filtered if p.get("fin") == fin]
    if status:
        filtered = [p for p in filtered if p.get("status") == status]
    
    return {
        "prozesse": filtered[:limit],
        "anzahl": len(filtered),
        "source": "memory"
    }

@app.get("/dashboard/kpis")
async def get_dashboard_kpis():
    """Dashboard KPIs"""
    if bq_client:
        try:
            query = """
            SELECT 
              COUNT(DISTINCT fin) as total_vehicles,
              COUNT(*) as total_records
            FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
            WHERE aktiv = TRUE
            """
            result = bq_client.query(query)
            rows = list(result)
            
            if rows:
                return dict(rows[0])
                
        except Exception as e:
            logger.error(f"BigQuery KPI error: {e}")
    
    return {
        "total_vehicles": len(vehicles_db),
        "total_processes": len(processes_db),
        "source": "memory"
    }

@app.get("/dashboard/warteschlangen")
async def get_warteschlangen():
    """Warteschlangen-Übersicht"""
    if bq_client:
        try:
            query = """
            SELECT 
              prozess_typ,
              COUNT(*) as anzahl_wartend
            FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE status = 'warteschlange'
            GROUP BY prozess_typ
            ORDER BY anzahl_wartend DESC
            """
            result = bq_client.query(query)
            queues = [dict(row) for row in result]
            
            return {
                "warteschlangen": queues,
                "source": "bigquery"
            }
                
        except Exception as e:
            logger.error(f"BigQuery queues error: {e}")
    
    return {"warteschlangen": [], "source": "memory"}

# Debug Endpoints
@app.get("/debug/bigquery-info")
async def debug_bigquery_info():
    """BigQuery Debug-Informationen"""
    if not bq_client:
        return {"error": "BigQuery Client nicht verfügbar"}
    
    try:
        info = {
            "project": bq_client.project,
            "location": bq_client.location
        }
        
        dataset = bq_client.get_dataset("autohaus")
        info["dataset"] = {
            "dataset_id": dataset.dataset_id,
            "location": dataset.location
        }
        
        tables = list(bq_client.list_tables("autohaus"))
        info["tables"] = [table.table_id for table in tables]
        
        return info
        
    except Exception as e:
        return {"error": f"BigQuery Debug Fehler: {e}"}

@app.post("/debug/bigquery-insert")
async def debug_bigquery_insert():
    """Test-Insert in BigQuery"""
    if not bq_client:
        return {"error": "BigQuery Client nicht verfügbar"}
    
    try:
        table_id = "ra-autohaus-tracker.autohaus.fahrzeuge_stamm"
        table = bq_client.get_table(table_id)
        
        test_fin = f"DEBUG{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        test_row = {
            "fin": test_fin,
            "marke": "Debug",
            "modell": "Test",
            "antriebsart": "Debug",
            "farbe": "Debug",
            "baujahr": 2024,
            "ersterfassung_datum": datetime.now().isoformat(),
            "aktiv": True
        }
        
        errors = bq_client.insert_rows_json(table, [test_row])
        
        if errors:
            return {"status": "error", "errors": errors}
        else:
            return {"status": "success", "test_fin": test_fin}
            
    except Exception as e:
        return {"status": "exception", "error": str(e)}

@app.get("/debug/prozesse/search/{prozess_id}")
async def debug_prozess_search(prozess_id: str):
    """Debug: Prozess in BigQuery und Memory suchen"""
    result = {
        "prozess_id": prozess_id,
        "bigquery": None,
        "memory": None
    }
    
    # BigQuery suchen
    if bq_client:
        try:
            query = """
            SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
            WHERE prozess_id = @prozess_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("prozess_id", "STRING", prozess_id)
                ]
            )
            bq_result = bq_client.query(query, job_config=job_config)
            processes = [dict(row) for row in bq_result]
            
            result["bigquery"] = processes[0] if processes else "nicht_gefunden"
            
        except Exception as e:
            result["bigquery"] = f"fehler: {e}"
    
    # Memory suchen
    if prozess_id in processes_db:
        result["memory"] = processes_db[prozess_id]
    else:
        result["memory"] = "nicht_gefunden"
    
    return result

@app.get("/debug/clear-memory")
async def clear_memory():
    """Memory-Storage leeren"""
    global vehicles_db, processes_db
    vehicles_db.clear()
    processes_db.clear()
    return {"message": "Memory-Storage geleert"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
@app.post("/prozesse/create-with-status", status_code=201)
async def create_prozess_with_status(
    fin: str,
    prozess_typ: str,
    status: str = "gestartet",
    bearbeiter: Optional[str] = None,
    prioritaet: Optional[int] = 5,
    anlieferung_datum: Optional[str] = None,
    notizen: Optional[str] = None
):
    """Prozess mit beliebigem Status erstellen (umgeht UPDATE-Problem)"""
    try:
        prozess_id = str(uuid.uuid4())
        
        process_data = {
            "prozess_id": prozess_id,
            "fin": fin,
            "prozess_typ": prozess_typ,
            "status": status,  # Direkter Status
            "bearbeiter": bearbeiter,
            "prioritaet": prioritaet,
            "anlieferung_datum": anlieferung_datum,
            "start_timestamp": datetime.now(),
            "datenquelle": "api",
            "notizen": notizen
        }
        
        bigquery_success = await save_process_to_bigquery(process_data)
        
        return {
            "message": f"Prozess mit Status '{status}' erstellt",
            "prozess_id": prozess_id,
            "fin": fin,
            "prozess_typ": prozess_typ,
            "status": status,
            "storage": "bigquery" if bigquery_success else "memory"
        }
        
    except Exception as e:
        logger.error(f"Error creating process with status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def create_status_update(prozess_id: str, alter_status: str, neuer_status: str, bearbeiter: Optional[str] = None, notizen: Optional[str] = None) -> bool:
    """Status-Update in separate Tabelle speichern"""
    if not bq_client:
        return False
    
    try:
        table_id = "ra-autohaus-tracker.autohaus.prozess_status_updates"
        table = bq_client.get_table(table_id)
        
        update_row = {
            "update_id": str(uuid.uuid4()),
            "prozess_id": prozess_id,
            "alter_status": alter_status,
            "neuer_status": neuer_status,
            "bearbeiter": bearbeiter,
            "update_timestamp": datetime.now().isoformat(),
            "notizen": notizen,
            "datenquelle": "api"
        }
        
        # None-Werte entfernen
        update_row = {k: v for k, v in update_row.items() if v is not None}
        
        errors = bq_client.insert_rows_json(table, [update_row])
        
        if errors:
            logger.error(f"Status-Update BigQuery errors: {errors}")
            return False
        
        logger.info(f"✅ Status-Update gespeichert: {prozess_id} -> {neuer_status}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Status-Update Fehler: {e}")
        return False

@app.put("/prozesse/{prozess_id}/status")
async def update_prozess_status(prozess_id: str, update: ProcessUpdate):
    """Prozess-Status über Status-Update-Tabelle ändern"""
    try:
        # Aktuellen Status aus View holen
        if bq_client:
            query = """
            SELECT effektiver_status, prozess_typ, fin
            FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status`
            WHERE prozess_id = @prozess_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("prozess_id", "STRING", prozess_id)
                ]
            )
            result = bq_client.query(query, job_config=job_config)
            processes = [dict(row) for row in result]
            
            if not processes:
                raise HTTPException(status_code=404, detail="Prozess nicht gefunden")
            
            current_process = processes[0]
            alter_status = current_process["effektiver_status"]
            
            # Status-Update speichern
            success = await create_status_update(
                prozess_id=prozess_id,
                alter_status=alter_status,
                neuer_status=update.status,
                bearbeiter=update.bearbeiter,
                notizen=update.notizen
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Status-Update fehlgeschlagen")
            
            return {
                "message": "Status erfolgreich aktualisiert",
                "prozess_id": prozess_id,
                "alter_status": alter_status,
                "neuer_status": update.status,
                "fin": current_process["fin"],
                "prozess_typ": current_process["prozess_typ"]
            }
        
        else:
            raise HTTPException(status_code=503, detail="BigQuery nicht verfügbar")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating process status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/warteschlange-data")
async def debug_warteschlange_data():
    """Debug: Daten für Warteschlangen-Views"""
    if not bq_client:
        return {"error": "BigQuery nicht verfügbar"}
    
    try:
        result = {}
        
        # 1. Alle Prozesse
        query1 = "SELECT COUNT(*) as total FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`"
        result["total_prozesse"] = [dict(row) for row in bq_client.query(query1)][0]
        
        # 2. Status-Updates
        query2 = "SELECT COUNT(*) as total FROM `ra-autohaus-tracker.autohaus.prozess_status_updates`"
        result["total_status_updates"] = [dict(row) for row in bq_client.query(query2)][0]
        
        # 3. Prozesse mit effektivem Status "warteschlange"
        query3 = """
        SELECT COUNT(*) as warteschlange_count
        FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status`
        WHERE effektiver_status = 'warteschlange'
        """
        result["warteschlange_prozesse"] = [dict(row) for row in bq_client.query(query3)][0]
        
        # 4. Werkstatt-Prozesse mit Warteschlange-Status
        query4 = """
        SELECT COUNT(*) as gwa_warteschlange_count
        FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status`
        WHERE prozess_typ = 'Werkstatt' 
          AND effektiver_status = 'warteschlange'
          AND anlieferung_datum IS NOT NULL
        """
        result["gwa_warteschlange_berechtigt"] = [dict(row) for row in bq_client.query(query4)][0]
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/dashboard/warteschlangen-status")
async def get_warteschlangen_mit_status():
    """Warteschlangen basierend auf Status-Update-System"""
    if bq_client:
        try:
            query = """
            SELECT 
              prozess_typ,
              COUNT(*) as anzahl_wartend,
              AVG(prioritaet) as avg_prioritaet,
              AVG(standzeit_tage_berechnet) as avg_standzeit
            FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status`
            WHERE effektiver_status = 'warteschlange'
            GROUP BY prozess_typ
            ORDER BY anzahl_wartend DESC
            """
            result = bq_client.query(query)
            queues = [dict(row) for row in result]
            
            return {
                "warteschlangen": queues,
                "source": "bigquery_status_updates"
            }
                
        except Exception as e:
            logger.error(f"BigQuery status queues error: {e}")
            return {"error": str(e)}
    
    return {"warteschlangen": [], "source": "bigquery_unavailable"}

@app.get("/dashboard/gwa-warteschlange")
async def get_gwa_warteschlange_api():
    """GWA Warteschlange über API"""
    if bq_client:
        try:
            query = """
            SELECT * FROM `ra-autohaus-tracker.autohaus.gwa_warteschlange`
            ORDER BY standzeit_tage DESC
            """
            result = bq_client.query(query)
            queue = [dict(row) for row in result]
            
            return {
                "gwa_warteschlange": queue,
                "anzahl": len(queue),
                "source": "bigquery"
            }
                
        except Exception as e:
            logger.error(f"GWA queue error: {e}")
            return {"error": str(e)}
    
    return {"gwa_warteschlange": [], "source": "bigquery_unavailable"}
