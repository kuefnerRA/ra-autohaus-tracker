# src/main.py - Saubere minimale Version (< 60 Zeilen)
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BigQuery Setup
try:
    from google.cloud import bigquery
    bq_client = bigquery.Client(project="ra-autohaus-tracker")
    logger.info("BigQuery Client initialisiert")
    BIGQUERY_AVAILABLE = True
except Exception as e:
    logger.error(f"BigQuery Client Fehler: {e}")
    bq_client = None
    BIGQUERY_AVAILABLE = False

# FastAPI App erstellen
app = FastAPI(
    title="RA Autohaus Tracker API",
    description="Multi-Source Fahrzeugprozess-Tracking für Reinhardt Automobile", 
    version="2.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router einbinden (mit korrekten absoluten Imports)
try:
    from routers.integration import router as integration_router, init_router
    
    # Router mit BigQuery-Client initialisieren
    init_router(bq_client)
    app.include_router(integration_router)
    logger.info("Integration Router geladen")
    
except ImportError as e:
    logger.error(f"Integration Router Import-Fehler: {e}")

# Basis-Endpoints
@app.get("/")
async def root():
    return {
        "message": "RA Autohaus Tracker API - Saubere Architektur",
        "version": "2.0.0", 
        "docs": "/docs",
        "bigquery_available": BIGQUERY_AVAILABLE,
        "architecture": "clean",
        "endpoints": {
            "zapier_new": "/integration/zapier/webhook",
            "zapier_legacy": "/integration/zapier/flexible",
            "debug": "/integration/zapier/debug"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "architecture": "clean",
        "services": {
            "api": "healthy",
            "bigquery": "healthy" if bq_client else "unavailable"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)