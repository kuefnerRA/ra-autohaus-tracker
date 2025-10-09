# src/core/performance.py
"""
Einfache Performance-Messung für RA Autohaus Tracker
"""

import time
import functools
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


def measure_performance(operation_name: Optional[str] = None):
    """
    Einfacher Decorator für Performance-Messung.
    
    Verwendung:
    @measure_performance("meine_operation")
    async def meine_funktion():
        ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            start_time = time.perf_counter()
            
            try:
                # Funktion ausführen
                result = await func(*args, **kwargs)
                
                # Zeit messen
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                # Einfaches Logging - alle Werte als String
                logger.info(
                    f"✅ {op_name} erfolgreich",
                    operation=op_name,
                    duration_ms=str(round(duration_ms, 2)),
                    status="success"
                )
                
                return result
                
            except Exception as e:
                # Auch bei Fehler messen
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                logger.error(
                    f"❌ {op_name} fehlgeschlagen",
                    operation=op_name,
                    duration_ms=str(round(duration_ms, 2)),
                    status="error",
                    error=str(e)
                )
                raise
        
        return wrapper
    
    return decorator