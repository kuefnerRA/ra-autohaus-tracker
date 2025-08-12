CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.prozesse_mit_sla` AS
SELECT
  p.*,  -- bestehende Spalten unverändert lassen
  COALESCE(r.sla_tage, p.sla_tage) AS sla_tage_berechnet,
  CASE 
    WHEN p.start_timestamp IS NOT NULL 
      THEN DATE_ADD(DATE(p.start_timestamp), INTERVAL COALESCE(r.sla_tage, p.sla_tage) DAY)
    ELSE NULL
  END AS sla_faellig_am_berechnet,
  CASE 
    WHEN p.start_timestamp IS NOT NULL
      THEN DATE_DIFF(CURRENT_DATE(), DATE(p.start_timestamp), DAY)
    ELSE NULL
  END AS standzeit_tage_berechnet
FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` AS p
LEFT JOIN `ra-autohaus-tracker.autohaus.sla_ref` AS r
USING (prozess_typ);