#!/bin/bash
# scripts/fix_status_view.sh - Korrigierte Status-View

set -e

echo "🔧 Status-View korrigieren (ohne doppelte Spalten)"

# Korrigierte View für aktuellen Prozess-Status
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
  p.prozess_id,
  p.fin,
  p.prozess_typ,
  p.status as original_status,
  COALESCE(cs.aktueller_status, p.status) as effektiver_status,
  COALESCE(cs.letzter_bearbeiter, p.bearbeiter) as effektiver_bearbeiter,
  p.prioritaet,
  p.anlieferung_datum,
  p.start_timestamp,
  p.ende_timestamp,
  p.datenquelle,
  p.erstellt_am,
  p.aktualisiert_am,
  cs.letztes_update,
  cs.letzte_notizen as status_notizen,
  
  -- SLA-Berechnungen (eindeutige Namen)
  CASE p.prozess_typ
    WHEN 'Transport' THEN 7
    WHEN 'Aufbereitung' THEN 2
    WHEN 'Werkstatt' THEN 10
    WHEN 'Foto' THEN 3
    ELSE 5
  END as sla_tage_berechnet,
  
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
  END as sla_deadline_berechnet,
  
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
  END as tage_bis_sla_berechnet,
  
  CASE 
    WHEN p.anlieferung_datum IS NOT NULL 
    THEN DATE_DIFF(CURRENT_DATE(), p.anlieferung_datum, DAY)
    ELSE NULL
  END as standzeit_tage_berechnet

FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` p
LEFT JOIN current_status cs ON p.prozess_id = cs.prozess_id;
SQL_EOF

# GWA Warteschlange basierend auf korrigierter Status-View
echo "Creating gwa_warteschlange view..."
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.gwa_warteschlange` AS
SELECT 
  fin,
  prozess_id,
  effektiver_bearbeiter as bearbeiter,
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
  status_notizen as notizen
FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status`
WHERE prozess_typ = 'Werkstatt' 
  AND effektiver_status = 'warteschlange'
  AND anlieferung_datum IS NOT NULL
ORDER BY standzeit_tage_berechnet DESC, erstellt_am ASC;
SQL_EOF

# Foto Warteschlange
echo "Creating foto_warteschlange view..."
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.foto_warteschlange` AS
WITH gwa_abschluss AS (
  SELECT 
    fin,
    MAX(letztes_update) as gwa_fertig_am
  FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status`
  WHERE prozess_typ = 'Werkstatt' AND effektiver_status = 'abgeschlossen'
  GROUP BY fin
)
SELECT 
  fp.fin,
  fp.prozess_id,
  fp.effektiver_bearbeiter as bearbeiter,
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
  fp.status_notizen as notizen
FROM `ra-autohaus-tracker.autohaus.prozesse_aktueller_status` fp
LEFT JOIN gwa_abschluss gwa ON fp.fin = gwa.fin
WHERE fp.prozess_typ = 'Foto' 
  AND fp.effektiver_status = 'warteschlange'
ORDER BY tage_seit_gwa_fertig DESC, fp.erstellt_am ASC;
SQL_EOF

echo "✅ Status-Update-System korrigiert!"
echo ""
echo "📊 Views erstellt:"
echo "- prozesse_aktueller_status (Basis-View mit aktuellem Status)"
echo "- gwa_warteschlange (Werkstatt-Warteschlange)"
echo "- foto_warteschlange (Foto-Warteschlange)"
echo ""
echo "🧪 Tests:"
echo "SELECT * FROM \`ra-autohaus-tracker.autohaus.prozesse_aktueller_status\` LIMIT 5;"
echo "SELECT * FROM \`ra-autohaus-tracker.autohaus.gwa_warteschlange\`;"