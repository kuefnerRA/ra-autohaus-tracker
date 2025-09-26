-- Migration: Add prozess_id to cleanup_queue
-- Date: 2025-09-25

ALTER TABLE `ra-autohaus-tracker.autohaus.cleanup_queue`
ADD COLUMN IF NOT EXISTS prozess_id STRING 
  OPTIONS(description="Prozess-ID die beendet werden soll");

-- Optional: Zusatz-Daten für flexible Erweiterungen
ALTER TABLE `ra-autohaus-tracker.autohaus.cleanup_queue`
ADD COLUMN IF NOT EXISTS zusatz_daten STRING
  OPTIONS(description="JSON mit zusätzlichen Daten");