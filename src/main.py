"""
FastAPI Main Application - Vollversion
Reinhardt Automobile GmbH - RA Autohaus Tracker
"""

import os
from dotenv import load_dotenv
load_dotenv()

import logging
import asyncio


from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware



import structlog
from structlog import configure, get_logger
from structlog.processors import JSONRenderer, TimeStamper
from structlog.stdlib import filter_by_level, add_logger_name, add_log_level

# Import der eigenen Module
from src.core.dependencies import startup_services, shutdown_services, check_all_services_health
from src.core.dependencies import (
    get_bigquery_service,
    get_vehicle_service,
    get_process_service,
    get_dashboard_service,
    get_info_service,
    reset_services
)

from src.api.routes.vehicles import router as vehicles_router
from src.api.routes.process import router as process_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.info import router as info_router
from src.api.routes.integration import router as integration_router
from src.api.routes.email import router as email_router
from src.services.process_cleanup_service import ProcessCleanupJob
from src.core.background_tasks import background_manager
import asyncio

load_dotenv()

# Strukturiertes Logging konfigurieren
def configure_logging():
    """Konfiguriert strukturiertes Logging für die Anwendung."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    configure(
        processors=[
            filter_by_level,
            add_logger_name,
            add_log_level,
            TimeStamper(fmt="ISO", utc=True),
            JSONRenderer() if os.getenv('ENVIRONMENT') == 'production' else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True
    )
    
    # Standard Python Logging Level setzen
    logging.basicConfig(level=getattr(logging, log_level))
    
    return get_logger(__name__)

# Lifecycle Management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifecycle Management.
    
    Startup:
    - Services initialisieren
    - Health Checks durchführen  
    - Environment validieren
    
    Shutdown:
    - Services sauber herunterfahren
    """
    logger = configure_logging()
    
    # Startup
    logger.info("🚀 RA Autohaus Tracker startet...")
    
    try:
        await startup_services()
        logger.info("✅ Application erfolgreich gestartet")
        
    except Exception as e:
        logger.error("💥 Kritischer Startup-Fehler", error=str(e))
        raise
    
    yield  # Application läuft
    
    # Shutdown  
    logger.info("🛑 RA Autohaus Tracker wird heruntergefahren...")
    
    try:
        await shutdown_services()
        logger.info("✅ Application sauber heruntergefahren")
        
    except Exception as e:
        logger.error("❌ Fehler beim Shutdown", error=str(e))

# FastAPI Application erstellen
app = FastAPI(
    title="RA Autohaus Tracker",
    description="""
    # Fahrzeugprozess-Tracking-System für Reinhardt Automobile GmbH
    
    **Funktionen:**
    - 🚗 Vollständige Fahrzeugverwaltung mit Stammdaten
    - 📊 Prozess-Tracking mit SLA-Monitoring  
    - 🔄 Multi-Channel-Integrationen (Zapier, E-Mail, APIs)
    - 📈 Real-time Dashboard & KPIs
    - ⚡ High-Performance mit BigQuery Backend
    
    **Entwickelt für:** Reinhardt Automobile GmbH
    
    ---
    
    ## API-Bereiche
    - **Fahrzeuge** (`/api/v1/fahrzeuge`): CRUD-Operationen für Fahrzeugdaten
    - **System** (`/info`, `/health`): System-Informationen und Health Checks
    
    ## Technische Details
    - **Backend:** FastAPI mit Python 3.12
    - **Datenbank:** Google BigQuery (Mock-Modus für lokale Entwicklung)
    - **Hosting:** Google Cloud Run
    """,
    version="1.0.0-alpha",
    contact={
        "name": "Maximilian Reinhardt",
        "email": "max@reinhardt-automobile.de"
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Logger nach App-Initialisierung
logger = get_logger(__name__)

# Middleware Configuration
def setup_middleware():
    """Konfiguriert FastAPI Middleware."""
    
    # CORS - Entwicklung vs. Produktion
    if os.getenv('ENVIRONMENT') == 'production':
        # Produktion: Restriktive CORS
        allowed_origins = [
            "https://ra-autohaus-tracker-*.run.app",
            "https://reinhardt-automobile.de"
        ]
    else:
        # Entwicklung: Permissive CORS
        allowed_origins = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"]
    )
    
    # GZip Compression für bessere Performance
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    logger.info("🔧 Middleware erfolgreich konfiguriert", 
               environment=os.getenv('ENVIRONMENT', 'development'))

setup_middleware()

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Globaler Exception Handler für unbehandelte Fehler.
    """
    logger.error("💥 Unbehandelter Fehler", 
                error=str(exc),
                path=str(request.url),
                method=request.method,
                exc_info=True)
    
    # In Produktion: Keine internen Details preisgeben
    if os.getenv('ENVIRONMENT') == 'production':
        detail = "Ein interner Serverfehler ist aufgetreten"
    else:
        detail = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "internal_server_error",
            "message": detail,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )

# Request Logging Middleware  
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Loggt alle HTTP-Requests strukturiert.
    """
    start_time = datetime.now()
    
    # Request loggen (nur bei DEBUG Level)
    if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
        logger.debug("📥 HTTP Request", 
                   method=request.method,
                   path=str(request.url.path),
                   query=str(request.url.query) if request.url.query else None)
    
    response = await call_next(request)
    
    # Response loggen
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info("📤 HTTP Response",
               method=request.method,
               path=str(request.url.path),
               status_code=response.status_code,
               duration_seconds=round(duration, 3))
    
    return response

@app.on_event("startup")
async def startup_event():
    """Application Startup"""
    await startup_services()
    
    # Cleanup-Job im Hintergrund starten (nur in Production)
    if os.getenv('ENVIRONMENT') == 'production':
        asyncio.create_task(
            background_manager.start_cleanup_job(interval_minutes=10)
        )
        logger.info("🔄 Background Cleanup-Job gestartet")

@app.on_event("shutdown")
async def shutdown_event():
    """Application Shutdown"""
    await background_manager.stop_cleanup_job()
    await shutdown_services()

# Router Registration
app.include_router(vehicles_router, prefix="/api/v1")
app.include_router(process_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(info_router, prefix="/api/v1")
app.include_router(integration_router, prefix="/api/v1")
app.include_router(email_router, prefix="/api/v1")


# System Endpoints
@app.get("/health", summary="System Health Check")
async def health_check():
    """
    Umfassender System-Health-Check.
    
    Prüft:
    - Application Status
    - Service Health (BigQuery, etc.)
    - Environment-Konfiguration
    - Basis-Funktionalität
    """
    try:
        health_status = await check_all_services_health()
        
        return JSONResponse(
            content={
                'status': health_status['overall_status'],
                'timestamp': datetime.now().isoformat(),
                'application': {
                    'name': 'RA Autohaus Tracker',
                    'version': '1.0.0-alpha',
                    'environment': os.getenv('ENVIRONMENT', 'development')
                },
                'services': health_status['services']
            },
            status_code=200 if health_status['overall_status'] == 'healthy' else 503
        )
        
    except Exception as e:
        logger.error("❌ Health Check fehlgeschlagen", error=str(e))
        return JSONResponse(
            content={
                'status': 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            },
            status_code=503
        )

@app.get("/info", summary="System Information")
async def system_info():
    """
    System-Informationen für Debugging und Monitoring.
    """
    from src.core.dependencies import get_service_info, get_environment_config
    
    try:
        return {
            'application': {
                'name': 'RA Autohaus Tracker',
                'version': '1.0.0-alpha',
                'description': 'Fahrzeugprozess-Tracking für Reinhardt Automobile GmbH'
            },
            'environment': get_environment_config(),
            'services': get_service_info(),
            'endpoints': {
                'vehicles': '/api/v1/fahrzeuge',
                'health': '/health',
                'docs': '/docs',
                'redoc': '/redoc'
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("❌ System-Info-Abruf fehlgeschlagen", error=str(e))
        return JSONResponse(
            content={'error': str(e)},
            status_code=500
        )

@app.get("/", summary="API Root")
async def root():
    """
    API Root - Willkommens-Endpunkt.
    """
    return {
        'message': 'RA Autohaus Tracker API',
        'version': '1.0.0-alpha',
        'status': 'running',
        'documentation': '/docs',
        'health_check': '/health',
        'system_info': '/info',
        'vehicles_api': '/api/v1/fahrzeuge',
        'timestamp': datetime.now().isoformat(),
        'developer': {
            'company': 'Reinhardt Automobile GmbH',
            'contact': 'Maximilian Reinhardt'
        }
    }

# Development-Only Endpoints
if os.getenv('ENVIRONMENT') != 'production':
    @app.get("/dev/reset-services", summary="[DEV] Services zurücksetzen")
    async def dev_reset_services():
        """
        Entwicklungs-Endpunkt zum Zurücksetzen aller Services.
        
        ⚠️ Nur in Development-Umgebung verfügbar!
        """
        from src.core.dependencies import reset_services
        
        try:
            reset_services()
            await startup_services()
            
            return {
                'message': 'Services erfolgreich zurückgesetzt und neu initialisiert',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("❌ Dev-Reset fehlgeschlagen", error=str(e))
            return JSONResponse(
                content={'error': str(e)},
                status_code=500
            )

if __name__ == "__main__":
    import uvicorn
    
    # Development Server
    logger = configure_logging()
    logger.info("🧪 Entwicklungsserver wird gestartet...")
    
    uvicorn.run(
        "src.main:app",
        host=os.getenv('API_HOST', '0.0.0.0'),
        port=int(os.getenv('API_PORT', 8080)),
        reload=os.getenv('API_RELOAD', 'true').lower() == 'true',
        log_level=os.getenv('LOG_LEVEL', 'info').lower(),
        access_log=True
    )