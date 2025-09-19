#!/usr/bin/env python3
"""
BigQuery View-Definitionen für RA Autohaus Tracker
Reinhardt Automobile GmbH

Zentrale Sammlung aller View-Definitionen.
Wird von setup_bigquery.py und create_views.py verwendet.
"""

from typing import Optional
from google.cloud import bigquery
from google.cloud.exceptions import Conflict

def create_or_update_view(client: bigquery.Client, view_id: str, view_query: str, description: Optional[str] = None):
    """Hilfsfunktion zum Erstellen oder Aktualisieren einer View."""
    try:
        view = bigquery.Table(view_id)
        view.view_query = view_query
        if description:
            view.description = description
        client.create_table(view)
        print(f"✅ View '{view_id.split('.')[-1]}' erstellt")
    except Conflict:
        view = client.get_table(view_id)
        view.view_query = view_query
        if description:
            view.description = description
        fields_to_update = ["view_query"]
        if description:
            fields_to_update.append("description")
        client.update_table(view, fields_to_update)
        print(f"✅ View '{view_id.split('.')[-1]}' aktualisiert")


def create_monitoring_views(client: bigquery.Client, dataset_id: str):
    """Erstellt alle Standard-Monitoring Views."""
    
    print("\n📊 Erstelle Standard-Monitoring Views...")
    
    # View 1: Aktuelle Fahrzeuge mit letztem Prozess
    view_id = f"{dataset_id}.v_fahrzeuge_aktuell"
    view_query = f"""
    WITH letzte_prozesse AS (
      SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY fin ORDER BY start_timestamp DESC) as rn
      FROM `{dataset_id}.fahrzeug_prozesse`
      WHERE ende_timestamp IS NULL  -- Nur offene Prozesse
    )
    SELECT 
      fs.fin,
      fs.marke,
      fs.modell,
      fs.baujahr,
      fs.farbe,
      fs.km_stand,
      fs.ek_netto,
      fp.prozess_typ,
      fp.status,
      fp.bearbeiter,
      fp.prioritaet,
      fp.start_timestamp,
      fp.sla_deadline_datum,
      DATETIME_DIFF(CURRENT_DATETIME(), fp.start_timestamp, DAY) as tage_im_prozess,
      DATE_DIFF(fp.sla_deadline_datum, CURRENT_DATE(), DAY) as tage_bis_deadline
    FROM `{dataset_id}.fahrzeuge_stamm` fs
    LEFT JOIN letzte_prozesse fp 
      ON fs.fin = fp.fin 
      AND fp.rn = 1  -- Nur der neueste Prozess
    WHERE fs.aktiv = TRUE
    """
    create_or_update_view(client, view_id, view_query, 
                         "Aktuelle Fahrzeuge mit letztem Prozess")
    
    # View 2: Prozess-Pipeline
    view_id = f"{dataset_id}.v_prozess_pipeline"
    view_query = f"""
    WITH letzte_prozesse AS (
      SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY fin ORDER BY start_timestamp DESC) as rn
      FROM `{dataset_id}.fahrzeug_prozesse`
      WHERE ende_timestamp IS NULL
    )
    SELECT 
      prozess_typ,
      CASE 
        WHEN UPPER(status) IN ('WARTESCHLANGE', 'GESTARTET', 'ANGELEGT', 'WARTEND', 'NEU') 
          THEN 'WARTESCHLANGE'
        WHEN UPPER(status) IN ('AKTIV', 'IN BEARBEITUNG', 'LAUFEND', 'IN ARBEIT')
          THEN 'AKTIV'
        WHEN UPPER(status) IN ('BEENDET', 'ABGESCHLOSSEN', 'FERTIG', 'ERLEDIGT')
          THEN 'BEENDET'
        ELSE UPPER(status)
      END as status_normalisiert,
      COUNT(DISTINCT fin) as anzahl_fahrzeuge,
      COUNT(DISTINCT CASE WHEN bearbeiter IS NOT NULL THEN fin END) as mit_bearbeiter,
      COUNT(DISTINCT CASE WHEN bearbeiter IS NULL THEN fin END) as ohne_bearbeiter,
      AVG(DATE_DIFF(CURRENT_DATE(), DATE(start_timestamp), DAY)) as avg_tage_im_prozess,
      COUNT(CASE WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) < 0 THEN 1 END) as sla_verletzt,
      COUNT(CASE WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) BETWEEN 0 AND 1 THEN 1 END) as sla_kritisch
    FROM letzte_prozesse
    WHERE rn = 1  -- Nur der neueste Prozess pro Fahrzeug
    GROUP BY prozess_typ, status_normalisiert
    ORDER BY prozess_typ, status_normalisiert
    """
    create_or_update_view(client, view_id, view_query,
                         "Prozess-Pipeline mit Status-Übersicht")
    
    # View 3: Prozesslaufzeiten
    view_id = f"{dataset_id}.v_prozesslaufzeiten"
    view_query = f"""
    SELECT 
      prozess_typ,
      CASE 
        WHEN UPPER(status) IN ('WARTESCHLANGE', 'GESTARTET', 'ANGELEGT', 'WARTEND') 
          THEN 'WARTESCHLANGE'
        WHEN UPPER(status) IN ('AKTIV', 'IN BEARBEITUNG', 'LAUFEND')
          THEN 'AKTIV'
        WHEN UPPER(status) IN ('BEENDET', 'ABGESCHLOSSEN', 'FERTIG', 'ERLEDIGT')
          THEN 'BEENDET'
        ELSE UPPER(status)
      END as status_normalisiert,
      
      -- Zeitraum-Kategorisierung
      CASE 
        WHEN DATE(start_timestamp) = CURRENT_DATE() THEN 'Heute'
        WHEN DATE(start_timestamp) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) THEN 'Gestern'
        WHEN DATE_TRUNC(start_timestamp, WEEK) = DATE_TRUNC(CURRENT_DATE(), WEEK) THEN 'Diese Woche'
        WHEN DATE_TRUNC(start_timestamp, WEEK) = DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 WEEK), WEEK) THEN 'Letzte Woche'
        WHEN DATE_TRUNC(start_timestamp, MONTH) = DATE_TRUNC(CURRENT_DATE(), MONTH) THEN 'Dieser Monat'
        ELSE 'Älter'
      END as zeitraum,
      
      -- Laufzeit-Metriken (nur für abgeschlossene Prozesse)
      AVG(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)) as avg_laufzeit_minuten,
      MIN(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)) as min_laufzeit_minuten,
      MAX(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)) as max_laufzeit_minuten,
      APPROX_QUANTILES(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE), 100)[OFFSET(50)] as median_laufzeit_minuten,
      COUNT(*) as anzahl_messungen
      
    FROM `{dataset_id}.fahrzeug_prozesse`
    WHERE ende_timestamp IS NOT NULL
      AND start_timestamp IS NOT NULL
      AND status IN ('BEENDET', 'Abgeschlossen', 'Fertig', 'Erledigt')
    GROUP BY prozess_typ, status_normalisiert, zeitraum
    """
    create_or_update_view(client, view_id, view_query,
                         "Prozesslaufzeiten-Analyse für abgeschlossene Prozesse")
    
    # View 4: Prozess-Gesamtlaufzeiten
    view_id = f"{dataset_id}.v_prozess_gesamtlaufzeiten"
    view_query = f"""
    WITH prozess_laufzeiten AS (
      SELECT 
        fin,
        prozess_typ,
        SUM(DATETIME_DIFF(ende_timestamp, start_timestamp, MINUTE)) as gesamt_laufzeit_minuten,
        MIN(start_timestamp) as prozess_start,
        MAX(ende_timestamp) as prozess_ende,
        COUNT(*) as anzahl_teilprozesse
      FROM `{dataset_id}.fahrzeug_prozesse`
      WHERE ende_timestamp IS NOT NULL
        AND status IN ('BEENDET', 'Abgeschlossen', 'Fertig', 'Erledigt')
      GROUP BY fin, prozess_typ
    )
    SELECT 
      prozess_typ,
      DATE_TRUNC(prozess_start, WEEK) as woche,
      AVG(gesamt_laufzeit_minuten) as avg_gesamtlaufzeit_minuten,
      AVG(gesamt_laufzeit_minuten/60.0) as avg_gesamtlaufzeit_stunden,
      APPROX_QUANTILES(gesamt_laufzeit_minuten, 100)[OFFSET(50)] as median_laufzeit_minuten,
      COUNT(*) as anzahl_prozesse
    FROM prozess_laufzeiten
    GROUP BY prozess_typ, woche
    ORDER BY prozess_typ, woche DESC
    """
    create_or_update_view(client, view_id, view_query,
                         "Aggregierte Prozess-Gesamtlaufzeiten nach Woche")
    
    # View 5: SLA-Monitoring
    view_id = f"{dataset_id}.v_sla_monitoring"
    view_query = f"""
    WITH letzte_prozesse AS (
      SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY fin ORDER BY start_timestamp DESC) as rn
      FROM `{dataset_id}.fahrzeug_prozesse`
      WHERE ende_timestamp IS NULL
    ),
    prozess_metriken AS (
      SELECT 
        fin,
        prozess_typ,
        status,
        bearbeiter,
        start_timestamp,
        sla_deadline_datum,
        DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) as tage_bis_deadline,
        CASE 
          WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) < 0 THEN 'VERLETZT'
          WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) <= 1 THEN 'KRITISCH'
          WHEN DATE_DIFF(sla_deadline_datum, CURRENT_DATE(), DAY) <= 3 THEN 'WARNUNG'
          ELSE 'OK'
        END as sla_status
      FROM letzte_prozesse
      WHERE rn = 1
    )
    SELECT 
      pm.*,
      fs.marke,
      fs.modell,
      fs.ek_netto,
      DATETIME_DIFF(CURRENT_DATETIME(), pm.start_timestamp, DAY) as tage_im_prozess
    FROM prozess_metriken pm
    JOIN `{dataset_id}.fahrzeuge_stamm` fs ON pm.fin = fs.fin
    WHERE pm.sla_status IN ('VERLETZT', 'KRITISCH', 'WARNUNG')
    ORDER BY pm.tage_bis_deadline ASC
    """
    create_or_update_view(client, view_id, view_query,
                         "SLA-Monitoring für kritische Prozesse")


def create_werkstatt_views(client: bigquery.Client, dataset_id: str):
    """Erstellt alle Werkstatt-spezifischen Views."""
    
    print("\n🔧 Erstelle Werkstatt-spezifische Views...")
    
    # View 1: Aktive Werkstatt-Prozesse
    view_id = f"{dataset_id}.v_werkstatt_prozesse_aktiv"
    view_query = f"""
    WITH aktive_werkstatt_prozesse AS (
      SELECT 
        p.fin,
        p.prozess_id,
        p.prozess_typ,
        p.status,
        p.bearbeiter,
        p.prioritaet,
        p.start_timestamp,
        p.sla_tage,
        p.sla_deadline_datum,
        p.standzeit_tage,
        p.notizen,
        p.aktualisiert_am,
        COALESCE(
          p.sla_deadline_datum,
          DATE_ADD(
            DATE(COALESCE(p.start_timestamp, p.erstellt_am)), 
            INTERVAL 7 DAY
          )
        ) AS deadline,
        DATE_DIFF(
          COALESCE(
            p.sla_deadline_datum,
            DATE_ADD(
              DATE(COALESCE(p.start_timestamp, p.erstellt_am)), 
              INTERVAL 7 DAY
            )
          ),
          CURRENT_DATE(),
          DAY
        ) AS tage_bis_deadline,
        CASE 
          WHEN DATE_DIFF(
            COALESCE(
              p.sla_deadline_datum,
              DATE_ADD(DATE(COALESCE(p.start_timestamp, p.erstellt_am)), INTERVAL 7 DAY)
            ),
            CURRENT_DATE(),
            DAY
          ) < 0 THEN 'Überfällig'
          WHEN DATE_DIFF(
            COALESCE(
              p.sla_deadline_datum,
              DATE_ADD(DATE(COALESCE(p.start_timestamp, p.erstellt_am)), INTERVAL 7 DAY)
            ),
            CURRENT_DATE(),
            DAY
          ) <= 1 THEN 'Kritisch'
          WHEN DATE_DIFF(
            COALESCE(
              p.sla_deadline_datum,
              DATE_ADD(DATE(COALESCE(p.start_timestamp, p.erstellt_am)), INTERVAL 7 DAY)
            ),
            CURRENT_DATE(),
            DAY
          ) <= 3 THEN 'Warnung'
          ELSE 'OK'
        END AS sla_status,
        ROW_NUMBER() OVER (PARTITION BY p.fin ORDER BY p.aktualisiert_am DESC) AS rn
      FROM `{dataset_id}.fahrzeug_prozesse` p
      WHERE 
        p.prozess_typ = 'Werkstatt'
        AND UPPER(p.status) NOT IN ('ABGESCHLOSSEN', 'STORNIERT', 'BEENDET', 'FERTIG', 'ERLEDIGT')
    )
    SELECT 
      f.fin,
      f.marke,
      f.modell AS typ,
      f.farbe,
      f.baujahr,
      f.km_stand,
      f.ek_netto,
      p.prozess_id,
      p.status AS prozess_status,
      CASE 
        WHEN p.bearbeiter IN ('Thomas K.', 'T. Küfner', 'TK') THEN 'Thomas Küfner'
        WHEN p.bearbeiter IN ('Max R.', 'M. Reinhardt', 'MR') THEN 'Maximilian Reinhardt'
        ELSE p.bearbeiter
      END AS bearbeiter,
      p.start_timestamp AS prozess_start,
      p.deadline,
      p.tage_bis_deadline,
      p.sla_status,
      p.standzeit_tage,
      CASE p.prioritaet
        WHEN 1 THEN '1 - Sehr hoch'
        WHEN 2 THEN '2 - Hoch'
        WHEN 3 THEN '3 - Mittel'
        WHEN 4 THEN '4 - Niedrig'
        WHEN 5 THEN '5 - Sehr niedrig'
        ELSE CAST(p.prioritaet AS STRING)
      END AS prioritaet_text,
      p.prioritaet AS prioritaet_nummer,
      p.notizen,
      p.aktualisiert_am AS letzte_aktualisierung,
      CURRENT_DATE() AS heute,
      CURRENT_TIMESTAMP() AS letzter_refresh,
      CASE 
        WHEN p.sla_status = 'Überfällig' THEN 1
        WHEN p.sla_status = 'Kritisch' THEN 2
        WHEN p.sla_status = 'Warnung' THEN 3
        ELSE 4
      END AS sla_sort_order,
      CASE 
        WHEN p.tage_bis_deadline < 0 THEN CONCAT(ABS(p.tage_bis_deadline), ' Tage überfällig')
        WHEN p.tage_bis_deadline = 0 THEN 'Heute fällig'
        WHEN p.tage_bis_deadline = 1 THEN 'Morgen fällig'
        ELSE CONCAT(p.tage_bis_deadline, ' Tage verbleibend')
      END AS deadline_text,
      CASE 
        WHEN p.sla_status = 'Überfällig' THEN '#FF0000'
        WHEN p.sla_status = 'Kritisch' THEN '#FFA500'
        WHEN p.sla_status = 'Warnung' THEN '#FFFF00'
        ELSE '#00FF00'
      END AS ampel_farbe
    FROM `{dataset_id}.fahrzeuge_stamm` f
    INNER JOIN aktive_werkstatt_prozesse p 
      ON f.fin = p.fin 
      AND p.rn = 1
    WHERE f.aktiv = TRUE
    ORDER BY 
      sla_sort_order ASC,
      p.tage_bis_deadline ASC,
      p.prioritaet ASC
    """
    create_or_update_view(client, view_id, view_query,
                         "Aktive Werkstatt-Prozesse mit SLA-Überwachung für Looker Studio")
    
    # View 2: Werkstatt KPIs
    view_id = f"{dataset_id}.v_werkstatt_kpis"
    view_query = f"""
    WITH werkstatt_metriken AS (
      SELECT 
        COUNT(*) AS anzahl_gesamt,
        COUNT(CASE WHEN sla_status = 'Überfällig' THEN 1 END) AS anzahl_ueberfaellig,
        COUNT(CASE WHEN sla_status = 'Kritisch' THEN 1 END) AS anzahl_kritisch,
        COUNT(CASE WHEN sla_status = 'Warnung' THEN 1 END) AS anzahl_warnung,
        COUNT(CASE WHEN sla_status = 'OK' THEN 1 END) AS anzahl_ok,
        ROUND(AVG(standzeit_tage), 1) AS avg_standzeit_tage,
        ROUND(AVG(tage_bis_deadline), 1) AS avg_tage_bis_deadline,
        MIN(deadline) AS naechste_deadline,
        MAX(standzeit_tage) AS max_standzeit_tage,
        MIN(standzeit_tage) AS min_standzeit_tage,
        COUNT(DISTINCT bearbeiter) AS anzahl_bearbeiter,
        COUNT(CASE WHEN bearbeiter IS NULL THEN 1 END) AS ohne_bearbeiter,
        COUNT(CASE WHEN prioritaet_nummer = 1 THEN 1 END) AS prio_1_sehr_hoch,
        COUNT(CASE WHEN prioritaet_nummer = 2 THEN 1 END) AS prio_2_hoch,
        COUNT(CASE WHEN prioritaet_nummer = 3 THEN 1 END) AS prio_3_mittel,
        COUNT(CASE WHEN prioritaet_nummer = 4 THEN 1 END) AS prio_4_niedrig,
        COUNT(CASE WHEN prioritaet_nummer = 5 THEN 1 END) AS prio_5_sehr_niedrig,
        SUM(ek_netto) AS gesamt_ek_netto,
        ROUND(AVG(ek_netto), 2) AS avg_ek_netto
      FROM `{dataset_id}.v_werkstatt_prozesse_aktiv`
    )
    SELECT 
      anzahl_gesamt,
      anzahl_ueberfaellig,
      anzahl_kritisch,
      anzahl_warnung,
      anzahl_ok,
      ohne_bearbeiter,
      ROUND(SAFE_DIVIDE(anzahl_ueberfaellig, anzahl_gesamt) * 100, 1) AS prozent_ueberfaellig,
      ROUND(SAFE_DIVIDE(anzahl_kritisch, anzahl_gesamt) * 100, 1) AS prozent_kritisch,
      ROUND(SAFE_DIVIDE(anzahl_warnung, anzahl_gesamt) * 100, 1) AS prozent_warnung,
      ROUND(SAFE_DIVIDE(anzahl_ok, anzahl_gesamt) * 100, 1) AS prozent_ok,
      ROUND(SAFE_DIVIDE(ohne_bearbeiter, anzahl_gesamt) * 100, 1) AS prozent_ohne_bearbeiter,
      ROUND(SAFE_DIVIDE(anzahl_ok + anzahl_warnung, anzahl_gesamt) * 100, 1) AS sla_compliance_score,
      avg_standzeit_tage,
      avg_tage_bis_deadline,
      min_standzeit_tage,
      max_standzeit_tage,
      naechste_deadline,
      DATE_DIFF(naechste_deadline, CURRENT_DATE(), DAY) AS tage_bis_naechste_deadline,
      anzahl_bearbeiter,
      ROUND(SAFE_DIVIDE(anzahl_gesamt, anzahl_bearbeiter), 1) AS avg_prozesse_pro_bearbeiter,
      prio_1_sehr_hoch,
      prio_2_hoch,
      prio_3_mittel,
      prio_4_niedrig,
      prio_5_sehr_niedrig,
      gesamt_ek_netto,
      avg_ek_netto,
      CASE 
        WHEN SAFE_DIVIDE(anzahl_ueberfaellig, anzahl_gesamt) > 0.2 THEN 'Kritisch'
        WHEN SAFE_DIVIDE(anzahl_ueberfaellig, anzahl_gesamt) > 0.1 THEN 'Warnung'
        ELSE 'OK'
      END AS gesamt_status,
      CURRENT_TIMESTAMP() AS aktualisiert_am,
      CURRENT_DATE() AS datum
    FROM werkstatt_metriken
    """
    create_or_update_view(client, view_id, view_query,
                         "Aggregierte KPIs für Werkstatt-Dashboard")
    
    # View 3: Bearbeiter-Auslastung
    view_id = f"{dataset_id}.v_werkstatt_bearbeiter_auslastung"
    view_query = f"""
    WITH bearbeiter_details AS (
      SELECT 
        bearbeiter,
        fin,
        marke,
        typ,
        sla_status,
        tage_bis_deadline,
        deadline,
        prioritaet_nummer,
        ek_netto,
        standzeit_tage,
        notizen
      FROM `{dataset_id}.v_werkstatt_prozesse_aktiv`
      WHERE bearbeiter IS NOT NULL
    )
    SELECT 
      bearbeiter,
      COUNT(*) AS anzahl_prozesse,
      COUNT(CASE WHEN sla_status = 'Überfällig' THEN 1 END) AS ueberfaellige_prozesse,
      COUNT(CASE WHEN sla_status = 'Kritisch' THEN 1 END) AS kritische_prozesse,
      COUNT(CASE WHEN sla_status = 'Warnung' THEN 1 END) AS warnung_prozesse,
      COUNT(CASE WHEN sla_status = 'OK' THEN 1 END) AS ok_prozesse,
      COUNT(CASE WHEN sla_status IN ('Überfällig', 'Kritisch') THEN 1 END) AS dringende_prozesse,
      ROUND(SAFE_DIVIDE(
        COUNT(CASE WHEN sla_status = 'Überfällig' THEN 1 END), 
        COUNT(*)
      ) * 100, 1) AS prozent_ueberfaellig,
      ROUND(AVG(tage_bis_deadline), 1) AS avg_tage_bis_deadline,
      ROUND(AVG(standzeit_tage), 1) AS avg_standzeit_tage,
      MIN(deadline) AS naechste_deadline,
      MIN(CASE WHEN sla_status IN ('Überfällig', 'Kritisch') THEN deadline END) AS naechste_kritische_deadline,
      ROUND(AVG(prioritaet_nummer), 1) AS avg_prioritaet,
      COUNT(CASE WHEN prioritaet_nummer <= 2 THEN 1 END) AS hohe_prioritaet_anzahl,
      SUM(ek_netto) AS gesamt_ek_netto,
      ROUND(AVG(ek_netto), 2) AS avg_ek_netto,
      STRING_AGG(
        CASE WHEN sla_status IN ('Überfällig', 'Kritisch') 
        THEN CONCAT(fin, ' (', sla_status, ')') 
        END, ', ' 
        ORDER BY tage_bis_deadline 
        LIMIT 5
      ) AS kritische_fins,
      STRING_AGG(DISTINCT marke, ', ') AS bearbeitete_marken,
      COUNT(DISTINCT marke) AS anzahl_marken,
      ROUND(
        (COUNT(*) * 10) +
        (COUNT(CASE WHEN sla_status = 'Überfällig' THEN 1 END) * 20) +
        (COUNT(CASE WHEN sla_status = 'Kritisch' THEN 1 END) * 10),
        0
      ) AS auslastungs_score,
      CASE 
        WHEN COUNT(CASE WHEN sla_status = 'Überfällig' THEN 1 END) > 2 THEN 'Überlastet'
        WHEN COUNT(CASE WHEN sla_status IN ('Überfällig', 'Kritisch') THEN 1 END) > 3 THEN 'Hoch ausgelastet'
        WHEN COUNT(*) > 5 THEN 'Normal ausgelastet'
        ELSE 'Kapazität verfügbar'
      END AS auslastungs_status,
      CASE 
        WHEN COUNT(CASE WHEN sla_status = 'Überfällig' THEN 1 END) > 0 
          THEN CONCAT('⚠️ ', COUNT(CASE WHEN sla_status = 'Überfällig' THEN 1 END), ' überfällige Prozesse priorisieren')
        WHEN COUNT(CASE WHEN sla_status = 'Kritisch' THEN 1 END) > 0 
          THEN CONCAT('⏰ ', COUNT(CASE WHEN sla_status = 'Kritisch' THEN 1 END), ' kritische Prozesse heute/morgen fällig')
        ELSE '✅ Alle Prozesse im grünen Bereich'
      END AS handlungsempfehlung
    FROM bearbeiter_details
    GROUP BY bearbeiter
    ORDER BY 
      ueberfaellige_prozesse DESC, 
      dringende_prozesse DESC, 
      anzahl_prozesse DESC
    """
    create_or_update_view(client, view_id, view_query,
                         "Bearbeiter-Auslastung und Workload-Analyse für Werkstatt")


def create_all_views(client: bigquery.Client, dataset_id: str):
    """Erstellt alle Views (wird von setup_bigquery.py und create_views.py verwendet)."""
    
    print("\n📊 Erstelle alle Views...")
    
    # Standard-Monitoring Views
    create_monitoring_views(client, dataset_id)
    
    # Werkstatt-spezifische Views
    create_werkstatt_views(client, dataset_id)
    
    print("\n✅ Alle Views erfolgreich erstellt/aktualisiert")
    
    # Zusammenfassung ausgeben
    print("\n📋 Verfügbare Views:")
    print("   Standard-Monitoring:")
    print("   • v_fahrzeuge_aktuell")
    print("   • v_prozess_pipeline")
    print("   • v_prozesslaufzeiten")
    print("   • v_prozess_gesamtlaufzeiten")
    print("   • v_sla_monitoring")
    print("   Werkstatt-Dashboard:")
    print("   • v_werkstatt_prozesse_aktiv")
    print("   • v_werkstatt_kpis")
    print("   • v_werkstatt_bearbeiter_auslastung")