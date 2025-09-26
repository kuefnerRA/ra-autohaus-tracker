SELECT 
  fin,
  marke,
  modell,
  baujahr,
  ek_netto,
  created_at
FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm` 
ORDER BY created_at DESC 
LIMIT 20;