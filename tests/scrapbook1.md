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


  FIN: WAUZZZ8V9LA123456
Marke: Audi
Modell: A4 Avant 40 TDI
Datum Erstzulassung: 15.08.2021
Antriebsart: Diesel
KW-Leistung: 150
KM-Stand: 68.900
Anzahl Fahrzeugschlüssel: 2
Bereifungsart: Ganzjahr
Anzahl Vorhalter: 2
EK netto: 29.750,00
Besteuerungsart: Regel
Farbe: Gletscherweiß Metallic
Baujahr: 2021
Bearbeiter: Thomas Küfner

FIN: W0L0AHM7512345678
Marke: Opel
Modell: Corsa-e Edition
Datum Erstzulassung: 22.03.2023
Antriebsart: Elektro
KW-Leistung: 100
KM-Stand: 12.300
Anzahl Fahrzeugschlüssel: 2
Bereifungsart: Sommer
Anzahl Vorhalter: 1
EK netto: 21.500,00
Besteuerungsart: Regel
Farbe: Voltgrün
Baujahr: 2023

FIN: VF3MCBHYULS123456
Marke: Peugeot
Modell: 3008 GT Hybrid
Datum Erstzulassung: 10.11.2022
Antriebsart: Plugin-Hybrid
KW-Leistung: 165
KM-Stand: 34.200
Anzahl Fahrzeugschlüssel: 3
Bereifungsart: Winter
Anzahl Vorhalter: 1
EK netto: 38.900,00
Besteuerungsart: Differenz
Farbe: Perlmutt Weiß
Baujahr: 2022
Bearbeiter: Maximilian Reinhardt

FIN: WBAWV510X0P123456
Marke: BMW
Modell: X1 xDrive20i
Datum Erstzulassung: 05.06.2020
Antriebsart: Benzin
KW-Leistung: 131
KM-Stand: 89.500
Anzahl Fahrzeugschlüssel: 2
Bereifungsart: Sommer
Anzahl Vorhalter: 3
EK netto: 26.200,00
Besteuerungsart: Regel
Farbe: Saphirschwarz Metallic
Baujahr: 2020
Bearbeiter: Thomas Küfner

FIN: TMBJJ7NE6L0123456
Marke: Skoda
Modell: Octavia Combi RS
Datum Erstzulassung: 18.01.2024
Antriebsart: Benzin
KW-Leistung: 180
KM-Stand: 8.100
Anzahl Fahrzeugschlüssel: 2
Bereifungsart: Ganzjahr
Anzahl Vorhalter: 0
EK netto: 41.300,00
Besteuerungsart: Regel
Farbe: Mondweiß Metallic
Baujahr: 2024

FIN: ZFAER000005123459
Marke: Alfa Romeo
Modell: Giulia 2.2 Diesel
Datum Erstzulassung: 28.02.2022
Antriebsart: Diesel
KW-Leistung: 140
KM-Stand: 52.400
Anzahl Fahrzeugschlüssel: 2
Bereifungsart: Winter
Anzahl Vorhalter: 2
EK netto: 31.200,00
Besteuerungsart: Differenz
Farbe: Rosso Competizione
Baujahr: 2022

Betreff: Einkauf abgeschlossen

FIN: WBAYF8C55DD123456
Marke: BMW
Modell: 320d Touring
Datum Erstzulassung: 12.06.2022
Antriebsart: Diesel
KW-Leistung: 140
KM-Stand: 45.300
Anzahl Fahrzeugschlüssel: 2
Bereifungsart: Ganzjahr
Anzahl Vorhalter: 1
EK netto: 28.500,00
Besteuerungsart: Regel
Farbe: Alpinweiß
Baujahr: 2022
Bearbeiter: Thomas Küfner

Betreff: Aufbereitung gestartet

FIN: WBAYF8C55DD123456
KM-Stand: 45.320
Farbe: Alpinweiß III
Bearbeiter: Maximilian Reinhardt


Testreihe:
# Fahrzeug via Zapier mit Einkauf-Prozess
curl -X POST http://localhost:8080/api/v1/integration/zapier/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "fahrzeug_fin": "WBAYF8C55DD123456",
    "prozess_name": "einkauf",
    "neuer_status": "AKTIV",
    "bearbeiter_name": "Thomas K.",
    "prioritaet": "2",
    "notizen": "Fahrzeug angekauft",
    "marke": "BMW",
    "modell": "320d"
  }'

-- In BigQuery Console
SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`;
SELECT * FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`;

curl -X POST http://localhost:8080/api/v1/integration/zapier/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "fahrzeug_fin": "WBAYF8C55DD123456",
    "prozess_name": "anlieferung",
    "neuer_status": "WARTESCHLANGE",
    "prioritaet": "3",
    "notizen": "Warte auf Spediteur"
  }'

  -- Sollte 2 Einträge zeigen
SELECT 
  prozess_id,
  prozess_typ,
  status,
  start_timestamp,
  ende_timestamp,
  notizen
FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
WHERE fin = 'WBAYF8C55DD123456'
ORDER BY start_timestamp;

curl -X POST http://localhost:8080/api/v1/integration/zapier/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "fahrzeug_fin": "WBAYF8C55DD123456",
    "prozess_name": "gwa",
    "neuer_status": "AKTIV",
    "bearbeiter_name": "Max R.",
    "prioritaet": "2",
    "notizen": "Reinigung läuft"
  }'

  -- Tabellen leeren (behält Schema)
TRUNCATE TABLE `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`;
TRUNCATE TABLE `ra-autohaus-tracker.autohaus.fahrzeug_aenderungen`;
TRUNCATE TABLE `ra-autohaus-tracker.autohaus.fahrzeuge_stamm`;

# Audi Q5 - Neues Fahrzeug mit Einkauf
curl -X POST http://localhost:8080/api/v1/integration/zapier/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "fahrzeug_fin": "WAUZZZ8V6KA123451",
    "prozess_name": "einkauf",
    "neuer_status": "AKTIV",
    "bearbeiter_name": "Max R.",
    "prioritaet": "1",
    "notizen": "Neuer Audi Q5 eingekauft",
    "marke": "Audi",
    "modell": "Q5 40 TDI"
  }'
#2. Prozesswechsel zu Anlieferung
 
curl -X POST http://localhost:8080/api/v1/integration/zapier/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "fahrzeug_fin": "WAUZZZ8V6KA123451",
    "prozess_name": "anlieferung",
    "neuer_status": "WARTESCHLANGE",
    "bearbeiter_name": "Thomas K.",
    "prioritaet": "2",
    "notizen": "Anlieferung für Montag geplant"
  }'
#3. Prozesswechsel zu Aufbereitung
 
curl -X POST http://localhost:8080/api/v1/integration/zapier/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "fahrzeug_fin": "WAUZZZ8V6KA123451",
    "prozess_name": "gwa",
    "neuer_status": "AKTIV",
    "bearbeiter_name": "Thomas K.",
    "prioritaet": "3",
    "notizen": "Vollaufbereitung inkl. Politur"
  }'
#4. Prozesswechsel zu Foto
 
curl -X POST http://localhost:8080/api/v1/integration/zapier/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "fahrzeug_fin": "WAUZZZ8V6KA123451",
    "prozess_name": "foto",
    "neuer_status": "AKTIV",
    "bearbeiter_name": "Max R.",
    "prioritaet": "2",
    "notizen": "360 Grad Aufnahmen"
  }'
#5. Prozesswechsel zu Verkauf
 
curl -X POST http://localhost:8080/api/v1/integration/zapier/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "fahrzeug_fin": "WAUZZZ8V6KA123451",
    "prozess_name": "verkauf",
    "neuer_status": "AKTIV",
    "bearbeiter_name": "Max R.",
    "prioritaet": "1",
    "notizen": "Online auf mobile.de und autoscout24"
  }'


Prüf-Queries nach jedem Schritt:
sql-- Alle Prozesse für dieses Fahrzeug
SELECT 
  prozess_typ,
  status,
  bearbeiter,
  start_timestamp,
  ende_timestamp,
  notizen
FROM `ra-autohaus-tracker.autohaus.fahrzeug_prozesse`
WHERE fin = 'WAUZZZ8V6KA123456'
ORDER BY start_timestamp DESC;

-- Nur offene Prozesse
SELECT * FROM `ra-autohaus-tracker.autohaus.v_fahrzeuge_aktuell`
WHERE fin = 'WAUZZZ8V6KA123456';