"""
Process Cleanup Service
Regelmäßiger Job der offene Prozesse mit Nachfolgeprozessen beendet
Umgeht das BigQuery Streaming Buffer Problem
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.cloud.exceptions import BadRequest

logger = logging.getLogger(__name__)

class ProcessCleanupJob:
    """
    Background Job der regelmäßig offene Prozesse beendet,
    die einen Nachfolgeprozess haben.
    """
    
    def __init__(self, bigquery_client: bigquery.Client, dataset_id: str):
        self.client = bigquery_client
        self.dataset_id = dataset_id
        self.min_age_minutes = 30  # Mindestens 30 Minuten alt
        logger.info("✅ ProcessCleanupJob initialisiert")
    
    async def run_cleanup(self) -> Dict[str, Any]:
        """
        Hauptmethode die den Cleanup durchführt.
        
        Returns:
            Dict mit Statistiken über die Bereinigung
        """
        logger.info("🧹 Starte Process Cleanup Job")
        
        stats = {
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 1. Finde alle offenen Prozesse mit Nachfolgeprozessen
            processes_to_close = await self._find_processes_to_close()
            stats["processed"] = len(processes_to_close)
            
            logger.info(f"📊 Gefundene Prozesse zum Schließen: {len(processes_to_close)}")
            
            # 2. Versuche jeden Prozess zu schließen
            for process in processes_to_close:
                success = await self._close_process(process)
                if success:
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            
            # 3. Verarbeite geplante Cleanups aus der Queue
            queue_stats = await self._process_cleanup_queue()
            stats["queue_processed"] = queue_stats
            
            logger.info(f"✅ Cleanup abgeschlossen: {stats['updated']} Prozesse geschlossen")
            
        except Exception as e:
            logger.error(f"❌ Fehler im Cleanup Job: {e}")
            stats["errors"] += 1
        
        return stats
    
    async def _find_processes_to_close(self) -> List[Dict[str, Any]]:
        """
        Findet alle offenen Prozesse die einen Nachfolgeprozess haben.
        """
        query = f"""
        WITH prozess_kette AS (
            SELECT 
                p1.prozess_id,
                p1.fin,
                p1.prozess_typ,
                p1.start_timestamp,
                p1.ende_timestamp,
                p1.created_at,
                -- Nachfolgeprozess
                p2.prozess_id as nachfolger_id,
                p2.prozess_typ as nachfolger_typ,
                p2.start_timestamp as nachfolger_start,
                -- Alter in Minuten (TIMESTAMP_DIFF für TIMESTAMP-Felder)
                TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), p1.created_at, MINUTE) as age_minutes
            FROM `{self.dataset_id}.fahrzeug_prozesse` p1
            INNER JOIN `{self.dataset_id}.fahrzeug_prozesse` p2
                ON p1.fin = p2.fin
                AND p2.start_timestamp > p1.start_timestamp
            WHERE p1.ende_timestamp IS NULL  -- Nur offene Prozesse
                AND p1.status != 'abgeschlossen'
                -- Mindestens 30 Minuten alt (um Streaming Buffer zu vermeiden)
                AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), p1.created_at, MINUTE) >= {self.min_age_minutes}
        )
        SELECT DISTINCT
            prozess_id,
            fin,
            prozess_typ,
            start_timestamp,
            MIN(nachfolger_start) as ende_timestamp,  -- Frühester Nachfolger
            age_minutes
        FROM prozess_kette
        GROUP BY prozess_id, fin, prozess_typ, start_timestamp, age_minutes
        ORDER BY age_minutes DESC
        LIMIT 100  -- Batch-Größe limitieren
        """
        
        try:
            query_job = self.client.query(query)
            results = query_job.result()
            
            processes = []
            for row in results:
                processes.append({
                    "prozess_id": row.prozess_id,
                    "fin": row.fin,
                    "prozess_typ": row.prozess_typ,
                    "start_timestamp": row.start_timestamp,
                    "ende_timestamp": row.ende_timestamp,
                    "age_minutes": row.age_minutes
                })
            
            return processes
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Finden offener Prozesse: {e}")
            return []
    
    async def _close_process(self, process: Dict[str, Any]) -> bool:
        """
        Schließt einen einzelnen Prozess durch Setzen des ende_timestamp.
        
        Args:
            process: Dict mit Prozessinformationen
            
        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        try:
            # Versuche UPDATE (kann fehlschlagen wenn noch im Streaming Buffer)
            update_query = f"""
            UPDATE `{self.dataset_id}.fahrzeug_prozesse`
            SET 
                ende_timestamp = DATETIME('{process['ende_timestamp']}'),
                status = 'abgeschlossen',
                updated_at = CURRENT_TIMESTAMP(),
                aktualisiert_am = CURRENT_DATETIME()
            WHERE prozess_id = '{process['prozess_id']}'
                AND fin = '{process['fin']}'
                AND ende_timestamp IS NULL
            """
            
            query_job = self.client.query(update_query)
            query_job.result()
            
            logger.info(f"✅ Prozess geschlossen: {process['prozess_id']} ({process['prozess_typ']})")
            return True
            
        except BadRequest as e:
            if "streaming buffer" in str(e).lower():
                # Noch im Streaming Buffer - später nochmal versuchen
                logger.debug(f"⏳ Prozess noch im Streaming Buffer: {process['prozess_id']} "
                           f"(Alter: {process['age_minutes']} Minuten)")
                return False
            else:
                logger.error(f"❌ Fehler beim Schließen von {process['prozess_id']}: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Unerwarteter Fehler beim Schließen von {process['prozess_id']}: {e}")
            return False
    
    async def _process_cleanup_queue(self) -> int:
        """
        Verarbeitet geplante Cleanups aus der cleanup_queue Tabelle.
        
        Returns:
            Anzahl verarbeiteter Queue-Einträge
        """
        query = f"""
        SELECT * FROM `{self.dataset_id}.cleanup_queue`
        WHERE processed = FALSE
          AND scheduled_for <= CURRENT_DATETIME()
        LIMIT 10
        """
        
        try:
            query_job = self.client.query(query)
            results = query_job.result()
            
            processed_count = 0
            for row in results:
                if await self._process_queue_entry(row):
                    processed_count += 1
            
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Verarbeiten der Cleanup-Queue: {e}")
            return 0
    
    async def _process_queue_entry(self, entry) -> bool:
        """
        Verarbeitet einen einzelnen Queue-Eintrag.
        """
        try:
            if entry.cleanup_type == 'VERKAUFSABSCHLUSS':
                # Beende alle offenen Prozesse für dieses Fahrzeug
                update_query = f"""
                UPDATE `{self.dataset_id}.fahrzeug_prozesse`
                SET 
                    ende_timestamp = CURRENT_DATETIME(),
                    status = 'abgeschlossen',
                    updated_at = CURRENT_TIMESTAMP(),
                    notizen = CONCAT(IFNULL(notizen, ''), ' | Cleanup nach Verkauf')
                WHERE fin = '{entry.fin}'
                  AND ende_timestamp IS NULL
                  AND created_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
                """
                
                self.client.query(update_query).result()
            
            # Markiere als verarbeitet
            mark_processed_query = f"""
            UPDATE `{self.dataset_id}.cleanup_queue`
            SET 
                processed = TRUE,
                processed_at = CURRENT_DATETIME()
            WHERE queue_id = '{entry.queue_id}'
            """
            
            self.client.query(mark_processed_query).result()
            
            logger.info(f"✅ Queue-Eintrag verarbeitet: {entry.cleanup_type} für {entry.fin}")
            return True
            
        except Exception as e:
            if "streaming buffer" not in str(e).lower():
                logger.error(f"❌ Fehler bei Queue-Verarbeitung: {e}")
            return False
    
    async def run_periodic(self, interval_minutes: int = 10):
        """
        Führt den Cleanup Job periodisch aus.
        
        Args:
            interval_minutes: Intervall zwischen den Durchläufen in Minuten
        """
        logger.info(f"🔄 Starte periodischen Cleanup Job (alle {interval_minutes} Minuten)")
        
        while True:
            try:
                stats = await self.run_cleanup()
                logger.info(f"📊 Cleanup-Statistik: {stats}")
                
                # Warte bis zum nächsten Durchlauf
                await asyncio.sleep(interval_minutes * 60)
                
            except asyncio.CancelledError:
                logger.info("🛑 Cleanup Job wurde gestoppt")
                break
            except Exception as e:
                logger.error(f"❌ Fehler im periodischen Cleanup: {e}")
                await asyncio.sleep(60)  # Bei Fehler kurz warten und nochmal versuchen


# Standalone Script für manuellen Run
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Setup
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_name = os.getenv("BIGQUERY_DATASET", "autohaus")
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT nicht gesetzt!")
        exit(1)
    
    dataset_id = f"{project_id}.{dataset_name}"
    
    try:
        client = bigquery.Client(project=project_id)
        cleanup_job = ProcessCleanupJob(client, dataset_id)
        
        # Einmaliger Run
        print("🧹 Führe manuellen Cleanup aus...")
        stats = asyncio.run(cleanup_job.run_cleanup())
        print(f"✅ Ergebnis: {stats}")
    except Exception as e:
        print(f"❌ Fehler: {e}")