#!/bin/bash
# scripts/create_views_fixed.sh - BigQuery Views mit korrekter DATE_DIFF Syntax

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
      DAY  -- WICHTIG: Dritten Parameter hinzugefügt!
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

# 2. SLA Alerts View
echo "Creating sla_alerts view..."
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.sla_alerts` AS
WITH prozesse_mit_sla AS (
  SELECT * FROM `ra-autohaus-tracker.autohaus.prozesse_mit_sla`
)
SELECT 
  prozess_typ,
  COUNT(*) as anzahl_ueberschreitungen,
  AVG(ABS(tage_bis_sla_berechnet)) as avg_tage_ueberschritten,
  ARRAY_AGG(
    STRUCT(
      fin, 
      bearbeiter, 
      ABS(tage_bis_sla_berechnet) as tage_ueberschritten,
      standzeit_tage_berechnet as standzeit_tage,
      erstellt_am
    ) 
    ORDER BY tage_bis_sla_berechnet ASC 
    LIMIT 10
  ) as kritische_faelle
FROM prozesse_mit_sla
WHERE status IN ('warteschlange', 'in_bearbeitung') 
  AND tage_bis_sla_berechnet <= 0
GROUP BY prozess_typ
ORDER BY anzahl_ueberschreitungen DESC;
SQL_EOF

# 3. GWA Warteschlange View
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

# 4. Foto Warteschlange View
echo "Creating foto_warteschlange view..."
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.foto_warteschlange` AS
WITH prozesse_mit_sla AS (
  SELECT * FROM `ra-autohaus-tracker.autohaus.prozesse_mit_sla`
),
gwa_abschluss AS (
  SELECT 
    fin,
    MAX(ende_timestamp) as gwa_fertig_am
  FROM prozesse_mit_sla
  WHERE prozess_typ = 'Werkstatt' AND status = 'abgeschlossen'
  GROUP BY fin
)
SELECT 
  fp.fin,
  fp.prozess_id,
  fp.bearbeiter,
  DATE_DIFF(CURRENT_DATE(), DATE(gwa.gwa_fertig_am), DAY) as tage_seit_gwa_fertig,
  fp.tage_bis_sla_berechnet as tage_bis_sla_deadline,
  CASE 
    WHEN fp.tage_bis_sla_berechnet <= 0 THEN 'KRITISCH - SLA überschritten'
    WHEN fp.tage_bis_sla_berechnet <= 1 THEN 'URGENT - SLA morgen'
    WHEN fp.tage_bis_sla_berechnet <= 2 THEN 'WARNUNG - SLA in 2 Tagen'
    ELSE 'NORMAL'
  END as sla_status,
  fp.prioritaet,
  fp.erstellt_am as warteschlange_seit,
  fp.notizen
FROM prozesse_mit_sla fp
LEFT JOIN gwa_abschluss gwa ON fp.fin = gwa.fin
WHERE fp.prozess_typ = 'Foto' 
  AND fp.status = 'warteschlange'
ORDER BY tage_seit_gwa_fertig DESC, fp.erstellt_am ASC;
SQL_EOF

echo "✅ Alle Views erfolgreich erstellt!"
echo ""
echo "📊 Verfügbare Views:"
echo "- prozesse_mit_sla (Basis-View mit SLA-Berechnungen)"
echo "- sla_alerts (SLA-Verletzungen)"
echo "- gwa_warteschlange (Werkstatt-Warteschlange)"
echo "- foto_warteschlange (Foto-Warteschlange)"
echo ""
echo "🧪 Test-Queries:"
echo "SELECT * FROM \`ra-autohaus-tracker.autohaus.prozesse_mit_sla\` LIMIT 5;"
echo "SELECT * FROM \`ra-autohaus-tracker.autohaus.gwa_warteschlange\`;"