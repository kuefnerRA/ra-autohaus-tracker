# Deploy-Checkliste – RA Autohaus Tracker

## 1. Vorbereitung
```bash
# Falls noch nicht eingeloggt:
gcloud auth login --no-browser
gcloud config set account kuefner@reinhardtautomobile.de
gcloud config set project ra-autohaus-tracker

# Artifact Registry Zugriff konfigurieren
gcloud auth configure-docker europe-west3-docker.pkg.dev
```

## 2. Test-Deployment
```bash
TAG=test ./scripts/deploy.sh build
./scripts/deploy.sh push
ENVIRONMENT=test ./scripts/deploy.sh run
```
- Ausgabe-URL im Browser öffnen (`/health` prüfen).  

## 3. SQL-Struktur anwenden
```bash
./scripts/sql_apply.sh
```
- Prüfen in BigQuery, ob Views/Tables aktualisiert sind.

## 4. Lokaler Test
```bash
PORT=8080 ./scripts/start_dev.sh
```
- Browser: `http://localhost:8080/docs` und `/health`.

## 5. Production-Deployment
```bash
TAG=prod ./scripts/deploy.sh build
./scripts/deploy.sh push
ENVIRONMENT=prod ./scripts/deploy.sh run
```

## 6. Nachbereitung
- **Git-Commit** für Änderungen (inkl. +x-Rechte):
```bash
git add --chmod=+x scripts/*.sh common.sh
git commit -m "chore: set executable bit for shell scripts"
```
- Eventuell `.env.example` anpassen.
