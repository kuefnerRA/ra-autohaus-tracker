#!/bin/bash
# scripts/setup_bigquery_fixed.sh - BigQuery Setup ohne GENERATED Columns

set -e

PROJECT_ID="ra-autohaus-tracker"
DATASET_ID="autohaus"
REGION="europe-west3"

echo "🚀 BigQuery Setup für RA Autohaus Tracker (Fixed)"
echo "Project: $PROJECT_ID"
echo "Dataset: $DATASET_ID"

# Alle APIs aktivieren (jetzt mit Billing)
echo "🔧 Google Cloud APIs aktivieren..."
gcloud services enable \
    bigquery.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    logging.googleapis.com \
    secretmanager.googleapis.com

# Dataset existiert bereits, Tabellen erstellen
echo "🗃️  Tabellen erstellen..."

# 1. Fahrzeug-Stammdaten (funktioniert bereits)
echo "  Fahrzeuge Stammdaten bereits erstellt ✅"

# 2. Prozess-Tabelle OHNE GENERATED Columns
echo "  Creating fahrzeug_prozesse (fixed)..."
bq query --use_legacy_sql=false << 'EOF'
CREATE TABLE IF NOT EXISTS `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` (
  prozess_id STRING NOT NULL,
  fin STRING NOT NULL,
  prozess_typ STRING NOT NULL,
  status STRING NOT NULL,
  bearbeiter STRING,
  prioritaet INT64 DEFAULT 5,
  anlieferung_datum DATE,
  start_timestamp DATETIME,
  ende_timestamp DATETIME,
  dauer_minuten INT64,
  sla_tage INT64,
  sla_deadline_datum DATE,
  tage_bis_sla_deadline INT64,
  standzeit_tage INT64,
  datenquelle STRING DEFAULT 'api',
  notizen STRING,
  erstellt_am DATETIME DEFAULT CURRENT_DATETIME(),
  aktualisiert_am DATETIME DEFAULT CURRENT_DATETIME(),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(erstellt_am)
CLUSTER BY prozess_typ, status, fin
OPTIONS(
  description="Fahrzeugprozesse mit SLA-Informationen (berechnet in der Anwendung)"
);
EOF

# 3. Views mit berechneten SLA-Werten
echo "  Creating SLA calculation view..."
bq query --use_legacy_sql=false << 'EOF'
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
  
  -- Tage bis SLA
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
      CURRENT_DATE()
    )
    ELSE NULL
  END as tage_bis_sla_berechnet,
  
  -- Standzeit
  CASE 
    WHEN anlieferung_datum IS NOT NULL 
    THEN DATE_DIFF(CURRENT_DATE(), anlieferung_datum)
    ELSE NULL
  END as standzeit_tage_berechnet,
  
  -- Dauer in Minuten
  CASE 
    WHEN start_timestamp IS NOT NULL AND ende_timestamp IS NOT NULL 
    THEN DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)
    ELSE NULL
  END as dauer_minuten_berechnet

FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`;
EOF

# 4. SLA Alerts View
echo "  Creating sla_alerts view..."
bq query --use_legacy_sql=false << 'EOF'
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
EOF

# 5. GWA Warteschlange
echo "  Creating gwa_warteschlange view..."
bq query --use_legacy_sql=false << 'EOF'
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
  AND anlieferung_datum IS NOT NULL
ORDER BY standzeit_tage_berechnet DESC, erstellt_am ASC;
EOF

# 6. Foto Warteschlange
echo "  Creating foto_warteschlange view..."
bq query --use_legacy_sql=false << 'EOF'
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
  DATE_DIFF(CURRENT_DATE(), DATE(gwa.gwa_fertig_am)) as tage_seit_gwa_fertig,
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
EOF

echo "✅ BigQuery Setup komplett abgeschlossen!"
echo ""
echo "📊 Erstellt:"
echo "  ✅ fahrzeuge_stamm"
echo "  ✅ fahrzeug_prozesse" 
echo "  ✅ prozesse_mit_sla (View mit SLA-Berechnungen)"
echo "  ✅ sla_alerts (View)"
echo "  ✅ gwa_warteschlange (View)"
echo "  ✅ foto_warteschlange (View)"
echo ""
echo "🌐 BigQuery Console:"
echo "https://console.cloud.google.com/bigquery?project=ra-autohaus-tracker"
echo ""
echo "🧪 Test mit:"
echo "SELECT * FROM \`ra-autohaus-tracker.autohaus.fahrzeuge_stamm\` LIMIT 5;"