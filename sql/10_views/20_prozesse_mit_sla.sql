CREATE OR REPLACE VIEW `ra-autohaus-tracker.autohaus.prozesse_mit_sla` AS
SELECT
  p.*,
  r.sla_tage,
  CASE 
    WHEN p.start_timestamp IS NOT NULL 
    THEN DATE_ADD(DATE(p.start_timestamp), INTERVAL r.sla_tage DAY)
    ELSE NULL
  END AS sla_faellig_am,
  CASE 
    WHEN p.start_timestamp IS NOT NULL
    THEN DATE_DIFF(CURRENT_DATE(), DATE(p.start_timestamp), DAY)
    ELSE NULL
  END AS standzeit_tage
FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` p
LEFT JOIN `ra-autohaus-tracker.autohaus.sla_ref` r USING (prozess_typ);
