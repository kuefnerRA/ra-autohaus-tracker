SELECT 
  prozess_id,
  fin,
  prozess_typ,
  status,
  bearbeiter,
  erstellt_am,
  aktualisiert_am
FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` 
ORDER BY aktualisiert_am DESC 
LIMIT 20;