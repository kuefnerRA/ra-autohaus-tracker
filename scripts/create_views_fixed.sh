#!/bin/bash
set -e

echo "📈 BigQuery Views für RA Autohaus Tracker erstellen (Fixed)"

# 1. Prozesse mit SLA-Berechnungen View (korrigiert)
echo "Creating prozesse_mit_sla view..."
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.prozesse_mit_sla` AS
SELECT 
  *,
  -- SLA-Tage basierend auf Prozesstyp
  CASE prozess_typ
    WHEN 'Transport' THEN 7
    WHEN 'Aufbereitung' THEN 2
    WHEN 'Werkstatt' THEN 10
    WHEN 'Foto' THEN 3
    ELSE 5
  END as sla_tage_berechnet,
  
  -- SLA Deadline
  CASE 
    WHEN start_timestamp IS NOT NULL 
    THEN DATE_ADD(DATE(start_timestamp), INTERVAL 
      CASE prozess_typ
        WHEN 'Transport' THEN 7
        WHEN 'Aufbereitung' THEN 2
        WHEN 'Werkstatt' THEN 10
        WHEN 'Foto' THEN 3
        ELSE 5
      END DAY)
    ELSE NULL
  END as sla_deadline_berechnet,
  
  -- Tage bis SLA (KORRIGIERT: 3 Parameter für DATE_DIFF)
  CASE 
    WHEN start_timestamp IS NOT NULL 
    THEN DATE_DIFF(
      DATE_ADD(DATE(start_timestamp), INTERVAL 
        CASE prozess_typ
          WHEN 'Transport' THEN 7
          WHEN 'Aufbereitung' THEN 2
          WHEN 'Werkstatt' THEN 10
          WHEN 'Foto' THEN 3
          ELSE 5
        END DAY),
      CURRENT_DATE(),
      DAY
    )
    ELSE NULL
  END as tage_bis_sla_berechnet,
  
  -- Standzeit (KORRIGIERT: 3 Parameter)
  CASE 
    WHEN anlieferung_datum IS NOT NULL 
    THEN DATE_DIFF(CURRENT_DATE(), anlieferung_datum, DAY)
    ELSE NULL
  END as standzeit_tage_berechnet,
  
  -- Dauer in Minuten
  CASE 
    WHEN start_timestamp IS NOT NULL AND ende_timestamp IS NOT NULL 
    THEN DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)
    ELSE NULL
  END as dauer_minuten_berechnet

FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`;
SQL_EOF

# 2. GWA Warteschlange View
echo "Creating gwa_warteschlange view..."
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.gwa_warteschlange` AS
WITH prozesse_mit_sla AS (
  SELECT * FROM `ra-autohaus-tracker.autohaus.prozesse_mit_sla`
)
SELECT 
  fin,
  prozess_id,
  bearbeiter,
  standzeit_tage_berechnet as standzeit_tage,
  tage_bis_sla_berechnet as tage_bis_sla_deadline,
  sla_deadline_berechnet as sla_deadline,
  CASE 
    WHEN tage_bis_sla_berechnet <= 0 THEN 'KRITISCH - SLA überschritten'
    WHEN tage_bis_sla_berechnet <= 2 THEN 'URGENT - SLA in 2 Tagen'
    WHEN tage_bis_sla_berechnet <= 5 THEN 'WARNUNG - SLA in 5 Tagen'
    ELSE 'NORMAL'
  END as sla_status,
  prioritaet,
  erstellt_am as warteschlange_seit,
  notizen
FROM prozesse_mit_sla
WHERE prozess_typ = 'Werkstatt' 
  AND status = 'warteschlange'
ORDER BY standzeit_tage_berechnet DESC, erstellt_am ASC;
SQL_EOF

echo "✅ Views erstellt!"
echo "Test mit: SELECT * FROM \`ra-autohaus-tracker.autohaus.gwa_warteschlange\`;"
