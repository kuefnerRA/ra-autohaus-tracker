# src/core/logging_config.py
"""
Zentrale Logging-Konfiguration mit Performance-Support
"""

import os
import logging
from typing import Any, Dict, Optional
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from structlog import configure, get_logger
from structlog.processors import JSONRenderer, TimeStamper
from structlog.stdlib import filter_by_level, add_logger_name, add_log_level


def setup_logging() -> structlog.BoundLogger:
    """
    Konfiguriert strukturiertes Logging für die gesamte Anwendung.
    
    Returns:
        Konfigurierter Logger
    """
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    is_production = os.getenv('ENVIRONMENT') == 'production'
    
    processors = [
        # Context-Vars automatisch hinzufügen (request_id, etc.)
        structlog.contextvars.merge_contextvars,
        filter_by_level,
        add_logger_name,
        add_log_level,
        TimeStamper(fmt="ISO", utc=True),
        # Performance-Processor
        add_performance_context,
    ]
    
    # Renderer basierend auf Environment
    if is_production:
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback
        ))
    
    configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True
    )
    
    # Standard Python Logging Level
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(message)s'
    )
    
    # Root Logger
    logger = get_logger(__name__)
    logger.info("🔧 Logging konfiguriert", 
               environment="production" if is_production else "development",
               log_level=log_level)
    
    return logger


def add_performance_context(logger, log_method, event_dict):
    """
    Processor der Performance-Context zu Logs hinzufügt.
    """
    # Performance-Daten extrahieren wenn vorhanden
    if "duration_ms" in event_dict:
        duration = event_dict["duration_ms"]
        
        # Performance-Kategorisierung
        if duration < 100:
            event_dict["performance"] = "fast"
        elif duration < 500:
            event_dict["performance"] = "normal"
        elif duration < 2000:
            event_dict["performance"] = "slow"
        else:
            event_dict["performance"] = "critical"
    
    return event_dict


class LoggerMixin:
    """
    Mixin für Services mit strukturiertem Logging.
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def log_operation(
        self, 
        operation: str, 
        success: bool = True,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """
        Einheitliche Operation-Logging-Methode.
        
        Args:
            operation: Name der Operation
            success: Ob erfolgreich
            duration_ms: Dauer in Millisekunden
            **kwargs: Zusätzliche Context-Daten
        """
        context = {
            "operation": operation,
            "success": success,
            **kwargs
        }
        
        if duration_ms is not None:
            context["duration_ms"] = round(duration_ms, 2)
        
        if success:
            self.logger.info(f"✅ {operation}", **context)
        else:
            self.logger.error(f"❌ {operation} fehlgeschlagen", **context)


# Request-Context-Management
class RequestContext:
    """Verwaltet Request-spezifischen Context."""
    
    @staticmethod
    def set(request_id: str, **kwargs):
        """Setzt Request-Context."""
        clear_contextvars()
        bind_contextvars(
            request_id=request_id,
            **kwargs
        )
    
    @staticmethod
    def add(**kwargs):
        """Fügt zum bestehenden Context hinzu."""
        bind_contextvars(**kwargs)
    
    @staticmethod
    def clear():
        """Löscht den Context."""
        clear_contextvars()


# Beispiel-Integration in Services:
"""
from src.core.logging_config import LoggerMixin

class VehicleService(LoggerMixin):
    def __init__(self, bigquery_service: BigQueryService):
        super().__init__()  # Initialisiert Logger
        self.bigquery_service = bigquery_service
        
    async def get_vehicles(self, ...):
        # Automatisches Logging über Mixin
        self.log_operation(
            "get_vehicles",
            success=True,
            duration_ms=150.5,
            vehicle_count=25
        )
"""