# src/main.py - Refaktorierte Hauptanwendung
import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

# Python Path Setup für absolute Imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Lade Umgebungsvariablen
load_dotenv()

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup und Shutdown Events"""
    # Startup
    logger.info("🚀 RA Autohaus Tracker startet...")
    
    # Services initialisieren
    try:
        from services.bigquery_service import BigQueryService
        bq_service = BigQueryService()
        await bq_service.initialize()
        logger.info("✅ BigQuery Service initialisiert")
    except Exception as e:
        logger.error(f"❌ BigQuery Initialisierung fehlgeschlagen: {e}")
    
    # Email-Service initialisieren (optional)
    try:
        from handlers.email_handler import EmailHandler
        email_handler = EmailHandler()
        # Background-Task für E-Mail-Processing könnte hier gestartet werden
        logger.info("✅ E-Mail Service bereit")
    except Exception as e:
        logger.error(f"⚠️ E-Mail Service optional: {e}")
    
    logger.info("🎯 RA Autohaus Tracker erfolgreich gestartet!")
    
    yield
    
    # Shutdown
    logger.info("🛑 RA Autohaus Tracker wird heruntergefahren...")

# FastAPI App erstellen
app = FastAPI(
    title="RA Autohaus Tracker API",
    description="Multi-Source Fahrzeugprozess-Tracking für Reinhardt Automobile",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion spezifischer setzen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router importieren und einbinden
from routers import dashboard, vehicles, processes, integration

app.include_router(dashboard.router)
app.include_router(vehicles.router)  
app.include_router(processes.router)
app.include_router(integration.router)

# Basis-Endpunkte
@app.get("/")
async def root():
    """Root-Endpoint mit API-Übersicht"""
    return {
        "message": "RA Autohaus Tracker API - Refaktoriert",
        "version": "2.0.0", 
        "documentation": "/docs",
        "redoc": "/redoc",
        "architecture": "modular",
        "available_endpoints": {
            "dashboard": "/dashboard/*",
            "fahrzeuge": "/fahrzeuge/*", 
            "processes": "/processes/*",
            "integration": "/integration/*"
        },
        "integration_endpoints": [
            "/integration/zapier/webhook",
            "/integration/email/webhook",
            "/integration/flowers/webhook",
            "/integration/unified",
            "/integration/zapier/flexible (legacy)"
        ],
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health Check Endpoint"""
    try:
        # Services prüfen
        from services.bigquery_service import BigQueryService
        bq_service = BigQueryService()
        bq_status = await bq_service.health_check()
        
        return {
            "status": "healthy",
            "version": "2.0.0",
            "architecture": "modular",
            "services": {
                "api": "healthy",
                "bigquery": "healthy" if bq_status else "unavailable",
                "routers": {
                    "dashboard": "loaded",
                    "vehicles": "loaded", 
                    "processes": "loaded",
                    "integration": "loaded"
                }
            },
            "endpoints_active": True
        }
    except Exception as e:
        logger.error(f"Health Check Fehler: {e}")
        return {
            "status": "degraded",
            "error": str(e)
        }

@app.get("/info")
async def api_info():
    """API-Informationen und verfügbare Endpunkte"""
    return {
        "api": "RA Autohaus Tracker",
        "version": "2.0.0",
        "description": "Multi-Source Fahrzeugprozess-Tracking für Reinhardt Automobile",
        "features": [
            "Zapier-Integration",
            "E-Mail-Verarbeitung", 
            "Flowers-Software-Anbindung",
            "BigQuery-Datenspeicherung",
            "SLA-Monitoring",
            "Dashboard-APIs",
            "Warteschlangen-Management"
        ],
        "endpoints": {
            "/dashboard/kpis": "Dashboard KPIs",
            "/dashboard/warteschlangen": "Warteschlangen-Status",
            "/dashboard/sla-status": "SLA-Violations",
            "/fahrzeuge": "Fahrzeug CRUD",
            "/processes": "Prozess-Management", 
            "/processes/warteschlange/{typ}": "Prozess-Warteschlangen",
            "/integration/zapier/webhook": "Zapier-Integration",
            "/integration/email/webhook": "E-Mail-Integration",
            "/integration/flowers/webhook": "Flowers-Integration"
        },
        "supported_processes": [
            "Einkauf",
            "Anlieferung", 
            "Aufbereitung",
            "Foto",
            "Werkstatt",
            "Verkauf"
        ]
    }

# Redirect für veraltete Endpunkte
@app.get("/docs-old")
async def old_docs_redirect():
    """Umleitung von alten Dokumentations-URLs"""
    return RedirectResponse(url="/docs")

@app.get("/info/prozesse")
async def info_prozesse():
    """Legacy-Endpoint für Prozess-Informationen"""
    return RedirectResponse(url="/processes/info/prozesse")

# Fallback für nicht gefundene Routen
@app.get("/{path:path}")
async def catch_all(path: str):
    """Catch-All für undefinierte Routen mit hilfreichen Hinweisen"""
    suggestions = []
    
    if "dashboard" in path.lower():
        suggestions.append("/dashboard/kpis")
    if "fahrzeug" in path.lower() or "vehicle" in path.lower():
        suggestions.append("/fahrzeuge")
    if "process" in path.lower() or "prozess" in path.lower():
        suggestions.append("/processes")
    if "integration" in path.lower() or "webhook" in path.lower():
        suggestions.extend([
            "/integration/zapier/webhook",
            "/integration/email/webhook"
        ])
    
    return {
        "error": "Endpunkt nicht gefunden",
        "requested_path": f"/{path}",
        "suggestions": suggestions if suggestions else ["Siehe /docs für alle verfügbaren Endpunkte"],
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Entwicklungsserver
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8080,
        reload=True,
        log_level="info"
    )