# End-to-End-Tests für Fahrzeugprozesse

## Voraussetzungen
- Lokale Entwicklungsumgebung auf WSL/Ubuntu mit Python 3.12.3
- Zugriff auf Google Cloud CLI (`gcloud`) sowie auf das gewünschte BigQuery-Projekt und -Dataset
- Laufende FastAPI-Anwendung (lokal oder Remote-Endpoint)
- Service-Account-Credentials und Umgebungsvariablen konfiguriert (z. B. `GOOGLE_APPLICATION_CREDENTIALS`, `GCP_PROJECT`, `BQ_DATASET`)
- Optional: Ein separates Testprojekt in BigQuery, um Produktivdaten nicht zu verändern

## Vorbereitung
1. **Backend starten**
   ```bash
   uvicorn src.main:app --reload
   ```
2. **GCloud Authentifizierung sicherstellen**
   ```bash
   gcloud auth application-default login
   ```
   Alternativ kannst du Workload Identity verwenden, sofern sie im Projekt hinterlegt ist.
3. **BigQuery-Setup prüfen**
   ```bash
   bq ls --project_id=${GCP_PROJECT} ${BQ_DATASET}
   ```
   Bestätige, dass die Tabellen `fahrzeuge_stamm` und `fahrzeug_prozesse` existieren. Leere die Tabellen vorab, wenn du mit einem sauberen Datenbestand starten möchtest.

## Teststrategie
1. **Testdaten isolieren**
   - Verwende für jeden Testlauf eindeutige Fahrzeug-IDs (z. B. `E2E-<DATUM>-<ZAHL>`) und Prozesskombinationen.
   - Dokumentiere die verwendeten IDs in einer Tabelle oder einem Notizdokument, um sie später gezielt in BigQuery abfragen zu können.

2. **Statusübergänge je Prozess prüfen**
   - Für jeden Prozess (Einkauf, Werkstatt, Aufbereitung, Gewährleistung) werden nacheinander die Stati `START`, `AKTIV`, `BEENDET` aufgerufen.
   - Wiederhole den Ablauf pro Prozess in separaten Blöcken und protokolliere die API-Responses (z. B. per `tee` oder `jq`).

3. **Validierung in BigQuery**
   - Nach jedem API-Aufruf prüfst du, ob genau ein neuer Eintrag bzw. Update geschrieben wurde:
     ```bash
     bq query --use_legacy_sql=false "
       SELECT status, kommentar, updated_at, prozess_typ
       FROM `${GCP_PROJECT}.${BQ_DATASET}.fahrzeug_prozesse`
       WHERE fahrzeug_id = '<FAHRZEUG_ID>'
       ORDER BY updated_at DESC
     "
     ```
   - Achte auf konsistente Zeitstempel, korrekte Prozess-Typen und darauf, dass der Status immer nur einen Schritt weitergeschaltet wird (keine Sprünge von `START` direkt zu `BEENDET`).
   - Dokumentiere Abweichungen sofort mit Screenshot oder Query-Resultat.

## Referenz der relevanten Endpunkte

| Aktion | HTTP-Methode | Pfad | Body-relevante Felder |
| --- | --- | --- | --- |
| Fahrzeug anlegen | `POST` | `/api/v1/fahrzeuge` | `fahrzeug_id`, `fin`, Stammdaten |
| Prozess starten | `POST` | `/api/v1/fahrzeuge/{fahrzeug_id}/prozesse` | `prozess_typ`, `status`, `kommentar` |
| Statuswechsel | `PATCH` | `/api/v1/fahrzeuge/{fahrzeug_id}/prozesse/{prozess_typ}/status` | `status`, optional `kommentar` |
| Prozesshistorie abfragen | `GET` | `/api/v1/fahrzeuge/{fahrzeug_id}/prozesse/{prozess_typ}` | – |

## Beispiel-Ablauf
1. **Fahrzeug anlegen (falls nötig)**
   ```bash
   curl -sS -X POST \
     http://localhost:8000/api/v1/fahrzeuge \
     -H 'Content-Type: application/json' \
     -d '{
       "fahrzeug_id": "E2E-20240101-01",
       "fin": "WVWZZZ1JZXW000001",
       "marke": "VW",
       "modell": "Golf",
       "baujahr": 2020
     }' | jq
   ```

2. **Status-Transition pro Prozess durchspielen**
   ```bash
   FAHRZEUG_ID="E2E-20240101-01"
   for PROZESS in EINKAUF WERKSTATT AUFBEREITUNG GEWAEHRLEISTUNG; do
     echo "\n===> Prozess: ${PROZESS}"
     curl -sS -X POST \
       "http://localhost:8000/api/v1/fahrzeuge/${FAHRZEUG_ID}/prozesse" \
       -H 'Content-Type: application/json' \
       -d "{
         \"prozess_typ\": \"${PROZESS}\",
         \"status\": \"START\",
         \"kommentar\": \"${PROZESS} gestartet\"
       }" | jq '.status'

     for STATUS in AKTIV BEENDET; do
       curl -sS -X PATCH \
         "http://localhost:8000/api/v1/fahrzeuge/${FAHRZEUG_ID}/prozesse/${PROZESS}/status" \
         -H 'Content-Type: application/json' \
         -d "{
           \"status\": \"${STATUS}\",
           \"kommentar\": \"${PROZESS} => ${STATUS}\"
         }" | jq '.status'
     done
   done
   ```

3. **BigQuery-Validierung**
   ```bash
   bq query --use_legacy_sql=false "
     SELECT prozess_typ, status, kommentar, updated_at
     FROM `${GCP_PROJECT}.${BQ_DATASET}.fahrzeug_prozesse`
     WHERE fahrzeug_id = '${FAHRZEUG_ID}'
     ORDER BY prozess_typ, updated_at
   "
   ```
   Vergleiche die Reihenfolge pro Prozess: `START` → `AKTIV` → `BEENDET`. Kontrolliere, dass keine zusätzlichen Statuswerte oder Duplikate vorhanden sind.

4. **API-Historie gegentesten**
   ```bash
   curl -sS "http://localhost:8000/api/v1/fahrzeuge/${FAHRZEUG_ID}/prozesse/EINKAUF" | jq
   ```
   Stelle sicher, dass die API dieselben Schritte wie BigQuery widerspiegelt.

## Zusätzliche Hinweise
- Wiederhole den Ablauf mit einem neuen `FAHRZEUG_ID`, wenn du Regressionen testen willst, ohne alte Daten zu löschen.
- Nutze `pytest -k process` oder vorhandene Tests, um automatisierte Checks zu ergänzen.
- Prüfe die Logs der Anwendung (`uvicorn`-Output oder strukturierte Logs), um Fehler frühzeitig zu erkennen.
- Setze vor dem Testlauf das System zurück, falls Skripte wie `scripts/reset_services.py` oder Datenbank-Reset-Utilities verfügbar sind.
- Dokumentiere Besonderheiten (z. B. fehlerhafte Statuswechsel) sofort in einem Testprotokoll, um später gezielt Tickets zu erstellen.

