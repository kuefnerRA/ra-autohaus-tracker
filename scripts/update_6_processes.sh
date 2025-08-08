#!/bin/bash
set -e

echo "🔧 Prozesstyp-Normalisierung: 6 Hauptprozesse"
echo "Einkauf | Anlieferung | Aufbereitung | Foto | Werkstatt | Verkauf"

# SLA-View für 6 Hauptprozesse
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.prozesse_6_haupttypen` AS
SELECT
    *,
    -- SLA-Tage für die 6 Hauptprozesse
    CASE prozess_typ
        WHEN 'Einkauf' THEN 14
        WHEN 'Anlieferung' THEN 7  
        WHEN 'Aufbereitung' THEN 2
        WHEN 'Foto' THEN 3
        WHEN 'Werkstatt' THEN 10
        WHEN 'Verkauf' THEN 30
        ELSE 5
    END as sla_tage_berechnet,
    
    -- SLA Deadline
    CASE
        WHEN start_timestamp IS NOT NULL
        THEN DATE_ADD(DATE(start_timestamp), INTERVAL
            CASE prozess_typ
                WHEN 'Einkauf' THEN 14
                WHEN 'Anlieferung' THEN 7
                WHEN 'Aufbereitung' THEN 2
                WHEN 'Foto' THEN 3
                WHEN 'Werkstatt' THEN 10
                WHEN 'Verkauf' THEN 30
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
    END as tage_bis_sla_berechnet,
    
    -- Standzeit
    CASE
        WHEN anlieferung_datum IS NOT NULL
        THEN DATE_DIFF(CURRENT_DATE(), anlieferung_datum, DAY)
        ELSE NULL
    END as standzeit_tage_berechnet
    
FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
WHERE prozess_typ IN ('Einkauf', 'Anlieferung', 'Aufbereitung', 'Foto', 'Werkstatt', 'Verkauf');
SQL_EOF

echo "✅ 6 Hauptprozesse View erstellt"

# Prozesstyp-Übersicht
bq query --use_legacy_sql=false << 'SQL_EOF'
CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.hauptprozesse_übersicht` AS
SELECT
    prozess_typ,
    COUNT(*) as total_prozesse,
    SUM(CASE WHEN status = 'warteschlange' THEN 1 ELSE 0 END) as in_warteschlange,
    SUM(CASE WHEN status = 'in_bearbeitung' THEN 1 ELSE 0 END) as in_bearbeitung,
    SUM(CASE WHEN status = 'abgeschlossen' THEN 1 ELSE 0 END) as abgeschlossen,
    CASE prozess_typ
        WHEN 'Einkauf' THEN 14
        WHEN 'Anlieferung' THEN 7
        WHEN 'Aufbereitung' THEN 2
        WHEN 'Foto' THEN 3
        WHEN 'Werkstatt' THEN 10
        WHEN 'Verkauf' THEN 30
    END as sla_tage
FROM `ra-autohaus-tracker.autohaus.prozesse_6_haupttypen`
GROUP BY prozess_typ
ORDER BY 
    CASE prozess_typ 
        WHEN 'Einkauf' THEN 1
        WHEN 'Anlieferung' THEN 2
        WHEN 'Aufbereitung' THEN 3
        WHEN 'Foto' THEN 4
        WHEN 'Werkstatt' THEN 5
        WHEN 'Verkauf' THEN 6
    END;
SQL_EOF

echo "✅ Hauptprozesse-Übersicht erstellt"
echo ""
echo "📊 6 Hauptprozesse konfiguriert:"
echo "1. Einkauf (14 Tage SLA)"
echo "2. Anlieferung (7 Tage SLA)"  
echo "3. Aufbereitung (2 Tage SLA)"
echo "4. Foto (3 Tage SLA)"
echo "5. Werkstatt (10 Tage SLA)"
echo "6. Verkauf (30 Tage SLA)"
