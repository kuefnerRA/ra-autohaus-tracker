# src/main.py - Finale modulare Version
"""
RA Autohaus Tracker - Hauptanwendung
Modulare FastAPI Anwendung für Multi-Source Fahrzeugprozess-Tracking
"""

import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Core imports
from src.core.dependencies import set_bigquery_service, get_services_health

# Router imports  
from src.api.routes.integration import router as integration_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.vehicles import router as vehicles_router
from src.api.routes.info import router as info_router

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BigQuery Service Setup
try:
    from src.services.bigquery_service import BigQueryService
    bq_service = BigQueryService()
    logger.info("✅ BigQuery Service erfolgreich initialisiert")
    BIGQUERY_AVAILABLE = True
except Exception as e:
    logger.error(f"❌ BigQuery Service Fehler: {e}")
    bq_service = None
    BIGQUERY_AVAILABLE = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application Lifecycle Management"""
    # Startup
    logger.info("🚀 RA Autohaus Tracker startet...")
    
    # BigQuery Client in Dependencies injizieren
    set_bigquery_service(bq_service)
    
    # Services Health Check
    services = get_services_health()
    logger.info(f"📊 Services Status: {services}")
    
    yield
    
    # Shutdown
    logger.info("⏹️  RA Autohaus Tracker wird beendet...")

# FastAPI App mit Lifecycle
app = FastAPI(
    title="RA Autohaus Tracker API",
    description="Multi-Source Fahrzeugprozess-Tracking für Reinhardt Automobile",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router Registration
app.include_router(integration_router)  # Integration Routes (bereits vorhanden)
app.include_router(dashboard_router)    # Dashboard Routes (neu)
app.include_router(vehicles_router)     # Vehicle Routes (neu)  
app.include_router(info_router)         # Info Routes (neu)

# Root Endpoints
@app.get("/")
async def root():
    """API Root mit Übersicht"""
    return {
        "message": "RA Autohaus Tracker API",
        "version": "2.0.0",
        "architektur": "modular",
        "docs": "/docs",
        "bigquery_verfügbar": BIGQUERY_AVAILABLE,
        "services": get_services_health(),
        "api_bereiche": {
            "integration": "/integration/* - Webhook-Integrationen (Zapier, Flowers)",
            "dashboard": "/dashboard/* - KPIs und Warteschlangen",
            "fahrzeuge": "/fahrzeuge/* - Fahrzeug-Management", 
            "info": "/info/* - System-Informationen"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Umfassender Gesundheitscheck"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "architektur": "modular",
        "components": {
            "api": "healthy",
            "bigquery": "healthy" if bq_service else "unavailable",
            "services": get_services_health()
        },
        "endpoints": {
            "integration": ["/integration/zapier/webhook", "/integration/email/webhook"],
            "dashboard": ["/dashboard/kpis", "/dashboard/warteschlangen"],
            "fahrzeuge": ["/fahrzeuge", "/fahrzeuge/{fin}"],
            "info": ["/info/prozesse", "/info/bearbeiter", "/info/system"]
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)