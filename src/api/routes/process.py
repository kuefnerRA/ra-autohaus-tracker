# src/api/routes/process.py
"""
Process API Routes - REST Endpunkte für Fahrzeugprozess-Management
Reinhardt Automobile GmbH - RA Autohaus Tracker

API-Layer für ProcessService mit Zapier/E-Mail-Integration.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

from src.core.dependencies import get_process_service
from src.services.process_service import ProcessService, ProcessingSource

# Router Setup
router = APIRouter(prefix="/process", tags=["Process Management"])
logger = structlog.get_logger(__name__)

# ===============================
# Request/Response Models
# ===============================

class ZapierWebhookRequest(BaseModel):
    """Model für eingehende Zapier Webhook-Daten."""
    fahrzeug_fin: str = Field(..., min_length=17, max_length=17, description="17-stellige Fahrzeug-FIN")
    prozess_name: str = Field(..., min_length=1, description="Prozess-Name (gwa, garage, foto, etc.)")
    neuer_status: str = Field(..., min_length=1, description="Neuer Prozess-Status")
    bearbeiter_name: Optional[str] = Field(None, description="Name des Bearbeiters")
    prioritaet: Optional[str] = Field(None, description="Priorität als String (wird zu Int konvertiert)")
    notizen: Optional[str] = Field(None, description="Zusätzliche Notizen")
    timestamp: Optional[str] = Field(None, description="Zapier-Timestamp")
    trigger_type: Optional[str] = Field(None, description="Art des Zapier-Triggers")

class EmailProcessRequest(BaseModel):
    """Model für E-Mail-Verarbeitungsanfragen."""
    email_content: str = Field(..., min_length=10, description="E-Mail-Inhalt")
    subject: str = Field(..., min_length=1, description="E-Mail-Betreff")
    sender: str = Field(..., min_length=1, description="E-Mail-Absender")
    received_at: Optional[datetime] = Field(None, description="E-Mail-Empfangszeitpunkt")
    headers: Optional[Dict[str, str]] = Field(None, description="E-Mail-Headers")

class UnifiedProcessRequest(BaseModel):
    """Model für direkte einheitliche Datenverarbeitung."""
    fin: str = Field(..., min_length=17, max_length=17, description="17-stellige Fahrzeug-FIN")
    prozess_typ: str = Field(..., description="Prozess-Typ")
    status: str = Field(..., description="Aktueller Status")
    bearbeiter: Optional[str] = Field(None, description="Bearbeiter")
    prioritaet: Optional[int] = Field(None, ge=1, le=10, description="Priorität 1-10")
    notizen: Optional[str] = Field(None, description="Notizen")
    zusatz_daten: Optional[Dict[str, Any]] = Field(None, description="Zusätzliche Daten")

class ProcessResponse(BaseModel):
    """Standard-Response für Process-Operationen."""
    success: bool = Field(..., description="Erfolgsstatus")
    processing_id: str = Field(..., description="Eindeutige Processing-ID")
    source: str = Field(..., description="Datenquelle")
    message: str = Field(..., description="Status-Nachricht")
    result: Optional[Dict[str, Any]] = Field(None, description="Verarbeitungsresultat")
    sla_data: Optional[Dict[str, Any]] = Field(None, description="SLA-Informationen")
    timestamp: datetime = Field(..., description="Verarbeitungszeitpunkt")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Fehlerdetails bei Fehlern")

# ===============================
# Zapier Integration Endpoints
# ===============================

@router.post(
    "/zapier/webhook",
    response_model=ProcessResponse,
    summary="Zapier Webhook Processor",
    description="Verarbeitet eingehende Zapier Webhooks für Fahrzeugprozess-Updates."
)
async def process_zapier_webhook(
    webhook_data: ZapierWebhookRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    process_service: ProcessService = Depends(get_process_service)
) -> ProcessResponse:
    """
    Zapier Webhook Verarbeitung mit automatischen Mappings.
    
    Konvertiert Zapier-Daten in einheitliches Format und verarbeitet sie.
    Unterstützt:
    - Automatische Prozess-Typ-Mappings (gwa → Aufbereitung)
    - Bearbeiter-Normalisierung (Thomas K. → Thomas Küfner)
    - SLA-Berechnung
    - Geschäftsregeln-Validierung
    
    Args:
        webhook_data: Zapier Webhook-Payload
        request: HTTP-Request für Header-Extraktion
        background_tasks: Background Tasks für Logging
        
    Returns:
        ProcessResponse: Verarbeitungsergebnis mit Status und Details
    """
    
    logger.info("🔄 Zapier Webhook empfangen",
               fin=webhook_data.fahrzeug_fin,
               prozess=webhook_data.prozess_name,
               user_agent=request.headers.get("user-agent"))
    
    try:
        # Request Headers extrahieren
        headers = dict(request.headers)
        
        # Zapier-Daten zu Dictionary konvertieren
        zapier_dict = webhook_data.model_dump()
        
        # ProcessService aufrufen
        result = await process_service.process_zapier_webhook(
            zapier_dict, headers
        )
        
        # Background Task für erweiterte Verarbeitung
        background_tasks.add_task(
            log_webhook_processing, 
            webhook_data.fahrzeug_fin,
            result["processing_id"],
            result["success"]
        )
        
        # Response erstellen
        response = ProcessResponse(
            success=result["success"],
            processing_id=result["processing_id"], 
            source=result["source"],
            message="Zapier Webhook erfolgreich verarbeitet" if result["success"] else "Verarbeitung fehlgeschlagen",
            result=result.get("result"),
            sla_data=result.get("sla_data"),
            timestamp=datetime.fromisoformat(result["timestamp"]),
            error_details={"error": result.get("error")} if not result["success"] else None
        )
        
        if result["success"]:
            logger.info("✅ Zapier Webhook erfolgreich verarbeitet",
                       processing_id=result["processing_id"],
                       fin=webhook_data.fahrzeug_fin)
        else:
            logger.error("❌ Zapier Webhook Verarbeitung fehlgeschlagen",
                        processing_id=result["processing_id"],
                        error=result.get("error"))
        
        return response
        
    except Exception as e:
        logger.error("💥 Zapier Webhook API-Fehler",
                    fin=webhook_data.fahrzeug_fin,
                    error=str(e),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook-Verarbeitung fehlgeschlagen: {str(e)}"
        )

# ===============================
# E-Mail Processing Endpoints
# ===============================

@router.post(
    "/email/parse",
    response_model=ProcessResponse,
    summary="E-Mail Parser",
    description="Parst E-Mail-Inhalte und extrahiert Fahrzeugprozess-Informationen."
)
async def process_email(
    email_data: EmailProcessRequest,
    background_tasks: BackgroundTasks,
    process_service: ProcessService = Depends(get_process_service)
) -> ProcessResponse:
    """
    Verarbeitet E-Mail-Inhalte und extrahiert Fahrzeugdaten.
    
    Funktionen:
    - FIN-Extraktion mit RegEx
    - Keyword-basierte Prozess-Erkennung
    - Automatische Datenstrukturierung
    - Integration in Unified Processing
    
    Args:
        email_data: E-Mail-Daten und Metainformationen
        background_tasks: Background Tasks
        
    Returns:
        ProcessResponse: Parsing- und Verarbeitungsergebnis
    """
    
    logger.info("📧 E-Mail Processing gestartet",
               sender=email_data.sender,
               subject=email_data.subject[:100])
    
    try:
        # ProcessService E-Mail-Verarbeitung aufrufen
        result = await process_service.process_email_data(
            email_content=email_data.email_content,
            subject=email_data.subject,
            sender=email_data.sender,
            metadata={
                "received_at": email_data.received_at.isoformat() if email_data.received_at else None,
                "headers": email_data.headers or {}
            }
        )
        
        # Background Task für E-Mail-Archivierung
        background_tasks.add_task(
            archive_processed_email,
            email_data.sender,
            email_data.subject,
            result["processing_id"]
        )
        
        response = ProcessResponse(
            success=result["success"],
            processing_id=result["processing_id"],
            source=result["source"],
            message="E-Mail erfolgreich geparst und verarbeitet" if result["success"] else "E-Mail-Verarbeitung fehlgeschlagen",
            result=result.get("result"),
            sla_data=result.get("sla_data"),
            timestamp=datetime.fromisoformat(result["timestamp"]),
            error_details={"error": result.get("error")} if not result["success"] else None
        )
        
        return response
        
    except ValueError as e:
        # Business Logic Fehler (z.B. keine FIN gefunden)
        logger.warning("⚠️ E-Mail enthält keine verarbeitbaren Fahrzeugdaten",
                      sender=email_data.sender,
                      error=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"E-Mail-Verarbeitung nicht möglich: {str(e)}"
        )
        
    except Exception as e:
        logger.error("💥 E-Mail Processing API-Fehler",
                    sender=email_data.sender,
                    error=str(e),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"E-Mail-Verarbeitung fehlgeschlagen: {str(e)}"
        )

# ===============================
# Unified Processing Endpoint
# ===============================

@router.post(
    "/unified",
    response_model=ProcessResponse,
    summary="Unified Data Processing",
    description="Direkte einheitliche Datenverarbeitung für strukturierte Eingaben."
)
async def process_unified_data(
    data: UnifiedProcessRequest,
    background_tasks: BackgroundTasks,  # Non-default parameter zuerst
    source: str = "api",  # Default parameter danach
    process_service: ProcessService = Depends(get_process_service)
) -> ProcessResponse:
    """
    Direkte einheitliche Datenverarbeitung.
    
    Für strukturierte API-Calls die bereits normalisierte Daten liefern.
    Verwendet dieselbe Business Logic wie Zapier/E-Mail-Verarbeitung.
    
    Args:
        data: Strukturierte Fahrzeugprozess-Daten
        source: Datenquelle-Identifikation
        background_tasks: Background Tasks
        
    Returns:
        ProcessResponse: Verarbeitungsergebnis
    """
    
    logger.info("🔧 Unified Processing - direkter API-Call",
               fin=data.fin,
               prozess_typ=data.prozess_typ,
               source=source)
    
    try:
        # Source-Mapping
        processing_source = ProcessingSource.API
        if source == "manual":
            processing_source = ProcessingSource.MANUAL
        
        # Daten zu Dictionary konvertieren
        unified_dict = data.model_dump()
        
        # ProcessService aufrufen
        result = await process_service.process_unified_data(
            data=unified_dict,
            source=processing_source,
            metadata={"api_source": source, "direct_call": True}
        )
        
        # Background Analytics
        background_tasks.add_task(
            track_api_usage,
            data.fin,
            data.prozess_typ,
            source,
            result["processing_id"]
        )
        
        response = ProcessResponse(
            success=result["success"],
            processing_id=result["processing_id"],
            source=result["source"],
            message="Daten erfolgreich verarbeitet" if result["success"] else "Verarbeitung fehlgeschlagen",
            result=result.get("result"),
            sla_data=result.get("sla_data"),
            timestamp=datetime.fromisoformat(result["timestamp"]),
            error_details={"error": result.get("error")} if not result["success"] else None
        )
        
        return response
        
    except Exception as e:
        logger.error("💥 Unified Processing API-Fehler",
                    fin=data.fin,
                    error=str(e),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unified Processing fehlgeschlagen: {str(e)}"
        )

# ===============================
# System Endpoints
# ===============================

@router.get(
    "/health",
    summary="Process Service Health Check",
    description="Umfassender Health Check für ProcessService und Dependencies."
)
async def process_health_check(
    process_service: ProcessService = Depends(get_process_service)
):
    """
    Detaillierter Health Check für ProcessService.
    
    Prüft:
    - ProcessService Status
    - VehicleService Dependency
    - BigQuery Dependency  
    - Geschäftslogik-Fähigkeiten
    - Mapping-Konfigurationen
    
    Returns:
        Detaillierter Health-Status mit Dependency-Informationen
    """
    
    try:
        health_status = await process_service.health_check()
        
        http_status = 200 if health_status["status"] == "healthy" else 503
        
        return JSONResponse(
            content=health_status,
            status_code=http_status
        )
        
    except Exception as e:
        logger.error("❌ Process Health Check fehlgeschlagen", error=str(e))
        return JSONResponse(
            content={
                "status": "unhealthy",
                "service": "ProcessService",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

@router.get(
    "/info",
    summary="Process Service Information",
    description="Systemdetails und Konfiguration des ProcessService."
)
async def process_info(
    process_service: ProcessService = Depends(get_process_service)
):
    """
    ProcessService Konfiguration und Capabilities.
    
    Returns:
        Service-Informationen, Mappings und verfügbare Funktionen
    """
    
    return {
        "service": "ProcessService",
        "version": "2.0.0",
        "capabilities": {
            "unified_processing": True,
            "zapier_integration": True,
            "email_processing": True,
            "sla_calculation": True,
            "background_tasks": True
        },
        "mappings": {
            "process_types": list(process_service.process_mappings.keys()),
            "bearbeiter_mappings": list(process_service.bearbeiter_mappings.keys()),
            "sla_hours": {str(k): v for k, v in process_service.sla_hours.items()}
        },
        "endpoints": {
            "zapier_webhook": "/api/v1/process/zapier/webhook",
            "email_processing": "/api/v1/process/email/parse",
            "unified_processing": "/api/v1/process/unified",
            "health_check": "/api/v1/process/health"
        },
        "timestamp": datetime.now().isoformat()
    }

# ===============================
# Background Tasks
# ===============================

async def log_webhook_processing(fin: str, processing_id: str, success: bool):
    """Background Task: Webhook-Verarbeitung loggen."""
    logger.info("📊 Webhook Processing Analytics",
               fin=fin,
               processing_id=processing_id,
               success=success,
               task_type="webhook_analytics")

async def archive_processed_email(sender: str, subject: str, processing_id: str):
    """Background Task: Verarbeitete E-Mails archivieren."""
    logger.info("📦 E-Mail Processing Analytics",
               sender=sender,
               subject=subject[:50],
               processing_id=processing_id,
               task_type="email_analytics")

async def track_api_usage(fin: str, prozess_typ: str, source: str, processing_id: str):
    """Background Task: API-Nutzung tracken."""
    logger.info("📈 API Usage Analytics",
               fin=fin,
               prozess_typ=prozess_typ,
               source=source,
               processing_id=processing_id,
               task_type="api_analytics")