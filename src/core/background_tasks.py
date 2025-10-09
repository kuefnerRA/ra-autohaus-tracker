"""
Background Tasks Management
Verwaltet wiederkehrende Hintergrund-Jobs
"""

import asyncio
import logging
from typing import Optional
from src.core.dependencies import get_cleanup_job

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """Manager für Hintergrund-Tasks"""
    
    def __init__(self):
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    async def start_cleanup_job(self, interval_minutes: int = 10):
        """Startet den periodischen Cleanup-Job"""
        cleanup_job = get_cleanup_job()
        if not cleanup_job:  # None-Check ist jetzt korrekt
            logger.warning("⚠️ Cleanup-Job nicht verfügbar (Mock-Modus)")
            return
            
        if self.is_running:
            logger.info("ℹ️ Cleanup-Job läuft bereits")
            return
            
        self.is_running = True
        logger.info(f"🔄 Starte Cleanup-Job (alle {interval_minutes} Minuten)")
        
        try:
            self.cleanup_task = asyncio.create_task(
                cleanup_job.run_periodic(interval_minutes)
            )
            await self.cleanup_task
        except asyncio.CancelledError:
            logger.info("🛑 Cleanup-Job wurde gestoppt")
        except Exception as e:
            logger.error(f"❌ Cleanup-Job Fehler: {e}")
        finally:
            self.is_running = False
            
    async def stop_cleanup_job(self):
        """Stoppt den Cleanup-Job"""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("✅ Cleanup-Job gestoppt")

# Globale Instanz
background_manager = BackgroundTaskManager()