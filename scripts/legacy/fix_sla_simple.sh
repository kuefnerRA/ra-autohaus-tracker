#!/bin/bash
set -e

echo "🎯 SLA-Views korrigieren - ohne doppelte Spalten"

bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.prozesse_sla_einfach` AS
SELECT
    prozess_id,
    fin,
    prozess_typ,
    status,
    bearbeiter,
    prioritaet,
    anlieferung_datum,
    start_timestamp,
    ende_timestamp,
    dauer_minuten,
    datenquelle,
    notizen,
    erstellt_am,
    aktualisiert_am,
    
    -- SLA-Tage für die 6 Hauptprozesse
    CASE prozess_typ
        WHEN 'Einkauf' THEN 14
        WHEN 'Anlieferung' THEN 7
        WHEN 'Aufbereitung' THEN 2
        WHEN 'Foto' THEN 3
        WHEN 'Werkstatt' THEN 10
        WHEN 'Verkauf' THEN 30
        ELSE 5
    END as sla_tage,
    
    -- Tage bis SLA (positiv = noch Zeit, negativ = überschritten)
    CASE
        WHEN start_timestamp IS NOT NULL
        THEN DATE_DIFF(
            DATE_ADD(DATE(start_timestamp), INTERVAL
                CASE prozess_typ
                    WHEN 'Einkauf' THEN 14
                    WHEN 'Anlieferung' THEN 7
                    WHEN 'Aufbereitung' THEN 2
                    WHEN 'Foto' THEN 3
                    WHEN 'Werkstatt' THEN 10
                    WHEN 'Verkauf' THEN 30
                    ELSE 5
                END DAY),
            CURRENT_DATE(),
            DAY
        )
        ELSE NULL
    END as tage_bis_sla,
    
    -- SLA-Status (einfach und klar)
    CASE
        WHEN start_timestamp IS NULL THEN 'NICHT_GESTARTET'
        WHEN DATE_DIFF(
            DATE_ADD(DATE(start_timestamp), INTERVAL
                CASE prozess_typ
                    WHEN 'Einkauf' THEN 14
                    WHEN 'Anlieferung' THEN 7
                    WHEN 'Aufbereitung' THEN 2
                    WHEN 'Foto' THEN 3
                    WHEN 'Werkstatt' THEN 10
                    WHEN 'Verkauf' THEN 30
                    ELSE 5
                END DAY),
            CURRENT_DATE(),
            DAY
        ) <= 0 THEN 'SLA_VERLETZT'
        WHEN DATE_DIFF(
            DATE_ADD(DATE(start_timestamp), INTERVAL
                CASE prozess_typ
                    WHEN 'Einkauf' THEN 14
                    WHEN 'Anlieferung' THEN 7
                    WHEN 'Aufbereitung' THEN 2
                    WHEN 'Foto' THEN 3
                    WHEN 'Werkstatt' THEN 10
                    WHEN 'Verkauf' THEN 30
                    ELSE 5
                END DAY),
            CURRENT_DATE(),
            DAY
        ) <= 2 THEN 'SLA_RISIKO'
        ELSE 'SLA_OK'
    END as sla_status,
    
    -- Standzeit (Tage seit Anlieferung)
    CASE
        WHEN anlieferung_datum IS NOT NULL
        THEN DATE_DIFF(CURRENT_DATE(), anlieferung_datum, DAY)
        ELSE NULL
    END as standzeit_tage
    
FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
WHERE prozess_typ IN ('Einkauf', 'Anlieferung', 'Aufbereitung', 'Foto', 'Werkstatt', 'Verkauf');
SQL_EOF

echo "✅ Vereinfachte SLA-View ohne doppelte Spalten erstellt"
echo ""
echo "📊 SLA-Felder (vereinfacht):"
echo "- sla_tage: SLA-Definition pro Prozesstyp"
echo "- tage_bis_sla: Verbleibende Tage (positiv) oder Überschreitung (negativ)"
echo "- sla_status: SLA_OK | SLA_RISIKO | SLA_VERLETZT | NICHT_GESTARTET"
echo "- standzeit_tage: Tage seit Anlieferung (nur relevant für Priorisierung)"
