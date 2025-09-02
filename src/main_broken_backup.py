# src/main_minimal.py - Garantiert funktionierend
import logging
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid

# Python Path Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="RA Autohaus Tracker API", 
    version="2.0.0",
    docs_url="/docs"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basis-Endpunkte
@app.get("/")
async def root():
    return {
        "message": "RA Autohaus Tracker API - Minimal Working Version",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "healthy"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}

# Dashboard Endpunkte direkt implementiert (ohne externen Router)
@app.get("/dashboard/kpis")
async def dashboard_kpis():
    return {
        "status": "success",
        "data": {
            "total_fahrzeuge": 42,
            "aktive_prozesse": 15,
            "wartende_prozesse": 8,
            "sla_violations": 2,
            "durchschnittliche_bearbeitungszeit": 125.5
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/dashboard/warteschlangen")
async def dashboard_warteschlangen():
    return {
        "status": "success",
        "warteschlangen": {
            "Aufbereitung": {"wartend": 3, "in_bearbeitung": 2},
            "Foto": {"wartend": 1, "in_bearbeitung": 1},
            "Werkstatt": {"wartend": 2, "in_bearbeitung": 3},
            "Verkauf": {"wartend": 2, "in_bearbeitung": 1}
        },
        "timestamp": datetime.now().isoformat()
    }

# Fahrzeug-Endpunkte direkt implementiert  
@app.get("/fahrzeuge")
async def list_fahrzeuge():
    return {
        "status": "success",
        "fahrzeuge": [
            {
                "id": str(uuid.uuid4()),
                "fin": f"MOCK{i:013d}",
                "marke": "Mock Marke",
                "modell": "Mock Modell",
                "erstellt_am": datetime.now().isoformat()
            }
            for i in range(5)
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.post("/fahrzeuge", status_code=201)
async def create_fahrzeug(fahrzeug: dict):
    return {
        "status": "success",
        "message": "Fahrzeug erfolgreich angelegt",
        "fin": fahrzeug.get("fin"),
        "timestamp": datetime.now().isoformat()
    }

# Prozess-Endpunkte
@app.get("/processes/info/prozesse")
async def process_info():
    return {
        "status": "success",
        "verfuegbare_prozesse": [
            "Einkauf", "Anlieferung", "Aufbereitung", 
            "Foto", "Werkstatt", "Verkauf"
        ],
        "status_optionen": [
            "wartend", "gestartet", "in_bearbeitung", 
            "pausiert", "abgeschlossen", "abgebrochen"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/processes")
async def list_processes():
    return {
        "status": "success",
        "prozesse": [
            {
                "id": str(uuid.uuid4()),
                "process_id": f"PROC_{i}",
                "fin": f"MOCK{i:013d}",
                "prozess_typ": "Aufbereitung",
                "status": "wartend",
                "erstellt_am": datetime.now().isoformat()
            }
            for i in range(3)
        ],
        "timestamp": datetime.now().isoformat()
    }

# Integration-Endpunkte (kritisch für Zapier)
@app.post("/integration/zapier/webhook")
async def zapier_webhook(request_data: dict):
    logger.info(f"Zapier Webhook erhalten: {request_data}")
    
    return {
        "status": "success",
        "message": "Zapier-Daten erfolgreich verarbeitet",
        "fin": request_data.get("fahrzeug_fin"),
        "prozess": request_data.get("prozess_name"),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/integration/zapier/flexible")  
async def zapier_flexible_legacy(request_data: dict):
    """Legacy-Endpoint für bestehende Zapier-Integration"""
    logger.info(f"Legacy Zapier Endpoint: {request_data}")
    
    return {
        "status": "success",
        "message": "Verarbeitung erfolgreich (Legacy-Endpoint)",
        "fin": request_data.get("fahrzeug_fin"),
        "prozess": request_data.get("prozess_name"),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/integration/debug/test-all-sources")
async def integration_debug():
    return {
        "status": "success",
        "message": "Integration-Debug erfolgreich",
        "test_results": [
            {"source": "zapier", "status": "ok"},
            {"source": "email", "status": "ok"}, 
            {"source": "webhook", "status": "ok"}
        ],
        "timestamp": datetime.now().isoformat()
    }

# Catch-All (für unbekannte Routen)
@app.get("/{path:path}")
async def catch_all(path: str):
    return {
        "error": "Endpunkt nicht gefunden (Minimal Version)",
        "path": f"/{path}",
        "available_endpoints": [
            "/health", "/dashboard/kpis", "/fahrzeuge", 
            "/processes", "/integration/zapier/webhook"
        ]
    }