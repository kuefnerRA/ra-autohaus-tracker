#!/bin/bash
set -e

echo "📋 Status-Update-Tabelle für RA Autohaus Tracker erstellen"

# Status-Updates Tabelle
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE TABLE IF NOT EXISTS `ra-autohaus-tracker.autohaus.prozess_status_updates` (
  update_id STRING NOT NULL,
  prozess_id STRING NOT NULL,
  alter_status STRING,
  neuer_status STRING NOT NULL,
  bearbeiter STRING,
  update_timestamp DATETIME DEFAULT CURRENT_DATETIME(),
  notizen STRING,
  datenquelle STRING DEFAULT 'api',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(update_timestamp)
CLUSTER BY prozess_id, neuer_status
OPTIONS(
  description="Status-Updates für Fahrzeugprozesse (umgeht Streaming Buffer Problem)"
);
SQL_EOF

# View für aktuellen Prozess-Status
echo "Creating prozesse_aktueller_status view..."
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.prozesse_aktueller_status` AS
WITH latest_updates AS (
  SELECT 
    prozess_id,
    neuer_status as aktueller_status,
    bearbeiter as letzter_bearbeiter,
    update_timestamp as letztes_update,
    notizen as letzte_notizen,
    ROW_NUMBER() OVER (PARTITION BY prozess_id ORDER BY update_timestamp DESC) as rn
  FROM `ra-autohaus-tracker.autohaus.prozess_status_updates`
),
current_status AS (
  SELECT 
    prozess_id,
    aktueller_status,
    letzter_bearbeiter,
    letztes_update,
    letzte_notizen
  FROM latest_updates
  WHERE rn = 1
)
SELECT 
  p.*,
  COALESCE(cs.aktueller_status, p.status) as effektiver_status,
  COALESCE(cs.letzter_bearbeiter, p.bearbeiter) as effektiver_bearbeiter,
  cs.letztes_update,
  cs.letzte_notizen as status_notizen,
  
  -- SLA-Berechnungen
  CASE p.prozess_typ
    WHEN 'Transport' THEN 7
    WHEN 'Aufbereitung' THEN 2
    WHEN 'Werkstatt' THEN 10
    WHEN 'Foto' THEN 3
    ELSE 5
  END as sla_tage,
  
  CASE 
    WHEN p.start_timestamp IS NOT NULL 
    THEN DATE_ADD(DATE(p.start_timestamp), INTERVAL 
      CASE p.prozess_typ
        WHEN 'Transport' THEN 7
        WHEN 'Aufbereitung' THEN 2
        WHEN 'Werkstatt' THEN 10
        WHEN 'Foto' THEN 3
        ELSE 5
      END DAY)
    ELSE NULL
  END as sla_deadline,
  
  CASE 
    WHEN p.start_timestamp IS NOT NULL 
    THEN DATE_DIFF(
      DATE_ADD(DATE(p.start_timestamp), INTERVAL 
        CASE p.prozess_typ
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
  END as tage_bis_sla,
  
  CASE 
    WHEN p.anlieferung_datum IS NOT NULL 
    THEN DATE_DIFF(CURRENT_DATE(), p.anlieferung_datum, DAY)
    ELSE NULL
  END as standzeit_tage

FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` p
LEFT JOIN current_status cs ON p.prozess_id = cs.prozess_id;
SQL_EOF

# GWA Warteschlange basierend auf Status-Updates
echo "Creating gwa_warteschlange view..."
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.gwa_warteschlange` AS
SELECT 
  fin,
  prozess_id,
  effektiver_bearbeiter as bearbeiter,
  standzeit_tage,
  tage_bis_sla as tage_bis_sla_deadline,
  sla_deadline,
  CASE 
    WHEN tage_bis_sla <= 0 THEN 'KRITISCH - SLA überschritten'
    WHEN tage_bis_sla <= 2 THEN 'URGENT - SLA in 2 Tagen'
    WHEN tage_bis_sla <= 5 THEN 'WARNUNG - SLA in 5 Tagen'
    ELSE 'NORMAL'
  END as sla_status,
  prioritaet,
  erstellt_am as warteschlange_seit,
  status_notizen as notizen
FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status`
WHERE prozess_typ = 'Werkstatt' 
  AND effektiver_status = 'warteschlange'
  AND anlieferung_datum IS NOT NULL
ORDER BY standzeit_tage DESC, erstellt_am ASC;
SQL_EOF

echo "✅ Status-Update-System erstellt!"
echo ""
echo "📊 Neue Struktur:"
echo "- prozess_status_updates (Tabelle für alle Status-Änderungen)"
echo "- prozesse_aktueller_status (View mit aktuellem Status)"
echo "- gwa_warteschlange (View basierend auf Status-Updates)"
