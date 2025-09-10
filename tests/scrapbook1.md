# Nutze die prozess_id aus der vorherigen Response
curl -X PUT http://localhost:8080/api/v1/fahrzeuge/WBAPB73516A123456/prozess/PRO_123456_20250909_194202 \
  -H "Content-Type: application/json" \
  -d '{
    "prozess_typ": "Foto",
    "status": "In Bearbeitung",
    "bearbeiter": "Maximilian Reinhardt",
    "prioritaet": "2",
    "notizen": "Fotoshooting läuft"
  }'