SELECT 
  'fahrzeuge_stamm' as tabelle, 
  COUNT(*) as anzahl,
  CAST(MAX(created_at) AS STRING) as letzte_aenderung
FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`
UNION ALL
SELECT 
  'fahrzeug_prozesse', 
  COUNT(*),
  CAST(MAX(erstellt_am) AS STRING)
FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
UNION ALL  
SELECT 
  'fahrzeug_aenderungen', 
  COUNT(*),
  CAST(MAX(changed_at) AS STRING)
FROM `ra-autohaus-tracker.autohaus.fahrzeug_aenderungen`
UNION ALL
SELECT 
  'cleanup_queue', 
  COUNT(*),
  CAST(MAX(created_at) AS STRING)
FROM `ra-autohaus-tracker.autohaus.cleanup_queue`
ORDER BY tabelle;