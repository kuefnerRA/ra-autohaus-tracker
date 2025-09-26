SELECT 
  p.fin,
  f.marke,
  f.modell,
  p.prozess_typ,
  p.status,
  p.bearbeiter,
  p.tage_bis_sla_deadline,
  p.aktualisiert_am
FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse` p
LEFT JOIN `ra-autohaus-tracker.autohaus.fahrzeuge_stamm` f ON p.fin = f.fin
WHERE p.ende_timestamp IS NULL
ORDER BY p.tage_bis_sla_deadline ASC, p.aktualisiert_am DESC
LIMIT 50;