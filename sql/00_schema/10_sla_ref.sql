CREATE TABLE IF NOT EXISTS `ra-autohaus-tracker.autohaus.sla_ref` (
  prozess_typ STRING,
  sla_tage INT64
);

MERGE `ra-autohaus-tracker.autohaus.sla_ref` T
USING (
  SELECT 'Einkauf' AS prozess_typ, 14 AS sla_tage UNION ALL
  SELECT 'Anlieferung', 7 UNION ALL
  SELECT 'Aufbereitung', 2 UNION ALL
  SELECT 'Foto', 3 UNION ALL
  SELECT 'Werkstatt', 10 UNION ALL
  SELECT 'Verkauf', 30
) S
ON T.prozess_typ = S.prozess_typ
WHEN NOT MATCHED THEN
  INSERT (prozess_typ, sla_tage) VALUES (S.prozess_typ, S.sla_tage)
WHEN MATCHED THEN
  UPDATE SET sla_tage = S.sla_tage;
