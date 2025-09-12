# RA Autohaus Tracker - Deployment Guide

## Übersicht
Diese Dokumentation beschreibt den vollständigen Deployment-Prozess für den RA Autohaus Tracker auf Google Cloud Run.

## Architektur
- **Runtime**: Google Cloud Run (Serverless Container)
- **Container Registry**: Google Artifact Registry
- **Datenbank**: BigQuery
- **Secrets**: Google Secret Manager
- **Region**: europe-west1

## Voraussetzungen

### 1. Google Cloud Projekt
- Projekt ID: `ra-autohaus-tracker`
- Aktivierte APIs:
  - Cloud Run API
  - Artifact Registry API
  - BigQuery API
  - Secret Manager API

### 2. Service Accounts
```
# Lokale Entwicklung (mit Impersonation)
ra-dev-local@ra-autohaus-tracker.iam.gserviceaccount.com

# Cloud Run Production
ra-dev-cloud-run@ra-autohaus-tracker.iam.gserviceaccount.com
```

### 3. IAM Berechtigungen
Der Cloud Run Service Account benötigt:
- `roles/bigquery.dataEditor` - BigQuery Datenzugriff
- `roles/bigquery.jobUser` - BigQuery Query-Ausführung
- `roles/secretmanager.secretAccessor` - Secret-Zugriff

### 4. Lokale Tools
- Google Cloud SDK (`gcloud`)
- Docker
- Python 3.12+
- Git

## Projekt-Struktur

```
ra-autohaus-tracker/
├── src/                    # Anwendungscode
│   ├── main.py            # FastAPI Hauptanwendung
│   ├── api/routes/        # API Endpoints
│   ├── services/          # Business Logic
│   └── handlers/          # Integration Handler
├── scripts/               # Deployment & Utility Scripts
│   ├── setup-env.sh       # Umgebung einrichten
│   ├── manage-secrets.sh  # Secrets verwalten
│   ├── build-and-push.sh # Docker Build & Push
│   └── deploy-cloud-run.sh # Cloud Run Deployment
├── Dockerfile             # Container Definition
├── requirements.txt       # Python Dependencies
└── .env.secrets          # Lokale Secrets (nicht in Git!)
```

## Deployment-Prozess

### Phase 1: Initiale Einrichtung

#### 1.1 Google Cloud CLI konfigurieren
```bash
# Projekt setzen
gcloud config set project ra-autohaus-tracker
gcloud config set run/region europe-west1

# Authentifizierung
gcloud auth login
gcloud auth application-default login
```

#### 1.2 Service Accounts erstellen
```bash
# Cloud Run Service Account
gcloud iam service-accounts create ra-dev-cloud-run \
  --display-name="RA Cloud Run Service Account"

# Berechtigungen vergeben
gcloud projects add-iam-policy-binding ra-autohaus-tracker \
  --member="serviceAccount:ra-dev-cloud-run@ra-autohaus-tracker.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding ra-autohaus-tracker \
  --member="serviceAccount:ra-dev-cloud-run@ra-autohaus-tracker.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

gcloud projects add-iam-policy-binding ra-autohaus-tracker \
  --member="serviceAccount:ra-dev-cloud-run@ra-autohaus-tracker.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### 1.3 Artifact Registry einrichten
```bash
# Docker Repository erstellen
gcloud artifacts repositories create ra-docker-repo \
  --repository-format=docker \
  --location=europe-west1 \
  --description="Docker Repository für RA Autohaus Tracker"

# Docker konfigurieren
gcloud auth configure-docker europe-west1-docker.pkg.dev
```

### Phase 2: Secrets Management

#### 2.1 Secrets vorbereiten
```bash
# .env.secrets erstellen (aus Template)
cp .env.secrets.template .env.secrets

# Editieren und ausfüllen:
# EMAIL_ADDRESS=email@reinhardtautomobile.de
# EMAIL_PASSWORD=app-spezifisches-passwort
# IMAP_SERVER=imap.gmail.com
```

#### 2.2 Secrets zu Google Cloud hochladen
```bash
./scripts/manage-secrets.sh

# Erstellt folgende Secrets:
# - email-address
# - email-password
# - imap-server
```

### Phase 3: Build & Deploy

#### 3.1 Docker Image bauen und pushen
```bash
./scripts/build-and-push.sh

# Ablauf:
# 1. Baut Docker Image aus Dockerfile
# 2. Tagged mit Git-Hash oder Timestamp
# 3. Pusht zu Artifact Registry
# 4. Speichert Image-URL in .last-build-image
```

#### 3.2 Zu Cloud Run deployen
```bash
./scripts/deploy-cloud-run.sh

# Konfiguration:
# - Min Instances: 0 (Cold Start erlaubt)
# - Max Instances: 3 (Kostenkontrolle)
# - Memory: 512Mi
# - CPU: 1
# - Timeout: 300s
```

#### 3.3 Deployment verifizieren
```bash
# Service Status prüfen
gcloud run services describe ra-autohaus-tracker --region=europe-west1

# Logs anzeigen
gcloud run services logs read ra-autohaus-tracker --region=europe-west1 --limit=50
```

## Endpoints nach Deployment

Nach erfolgreichem Deployment ist die Anwendung erreichbar unter:
```
https://ra-autohaus-tracker-[HASH].europe-west1.run.app
```

### Wichtige Endpoints:
- `/health` - Health Check
- `/docs` - Swagger API Dokumentation  
- `/api/vehicles` - Fahrzeugverwaltung
- `/api/process` - Prozessverwaltung
- `/api/integration/zapier` - Zapier Webhook
- `/api/email/import` - Email Import

## Production
Service URL: https://ra-autohaus-tracker-62067895551.europe-west1.run.app
API Docs: https://ra-autohaus-tracker-62067895551.europe-west1.run.app/docs

## Umgebungsvariablen

### In Cloud Run gesetzt:
```
PROJECT_ID=ra-autohaus-tracker
BIGQUERY_DATASET=autohaus
ENVIRONMENT=production
```

### Aus Secret Manager:
```
EMAIL_ADDRESS      # Email für IMAP
EMAIL_PASSWORD     # App-spezifisches Passwort
IMAP_SERVER       # IMAP Server Adresse
```

## Continuous Deployment

### Manuelles Deployment
```bash
# Alle Schritte auf einmal
./scripts/deploy-all.sh
```

### GitHub Actions (geplant)
Workflow für automatisches Deployment bei Push auf main Branch.
Siehe `.github/workflows/deploy.yml` (wenn implementiert).

## Monitoring & Debugging

### Logs abrufen
```bash
# Letzte 50 Einträge
gcloud run services logs read ra-autohaus-tracker \
  --region=europe-west1 --limit=50

# Live Logs
gcloud run services logs tail ra-autohaus-tracker \
  --region=europe-west1
```

### Metriken
- Cloud Console: https://console.cloud.google.com/run
- Metrics Explorer für detaillierte Metriken
- Cloud Logging für strukturierte Logs

### Häufige Probleme

#### BigQuery Streaming Buffer
**Problem**: Prozesse können wegen Streaming Buffer nicht sofort beendet werden.
**Lösung**: 90 Minuten warten oder alternative Update-Strategie implementieren.

#### Cold Starts
**Problem**: Erste Anfrage nach Inaktivität dauert länger.
**Lösung**: Min-Instances erhöhen oder Warm-up Requests implementieren.

#### Secret Access Fehler
**Problem**: Cloud Run kann nicht auf Secrets zugreifen.
**Lösung**: Service Account Berechtigungen prüfen:
```bash
gcloud secrets get-iam-policy email-password
```

## Rollback

### Zur vorherigen Version zurückkehren:
```bash
# Letzte Revisionen anzeigen
gcloud run revisions list --service=ra-autohaus-tracker \
  --region=europe-west1

# Traffic auf alte Version umleiten
gcloud run services update-traffic ra-autohaus-tracker \
  --to-revisions=ra-autohaus-tracker-[ALTE-REVISION]=100 \
  --region=europe-west1
```

## Kosten-Optimierung

### Aktuelle Einstellungen:
- **Min Instances: 0** - Keine Kosten bei Inaktivität
- **Max Instances: 3** - Begrenzt maximale Kosten
- **Memory: 512Mi** - Ausreichend für die Anwendung
- **CPU: 1** - Standard, kann bei Bedarf reduziert werden

### Kostenüberwachung:
```bash
# Budget Alert einrichten
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="RA Autohaus Tracker Budget" \
  --budget-amount=50EUR \
  --threshold-rule=percent=90
```

## Sicherheit

### Best Practices:
1. **Keine Secrets im Code** - Alles über Secret Manager
2. **Service Account Prinzip** - Minimale Berechtigungen
3. **HTTPS Only** - Cloud Run erzwingt HTTPS
4. **Keine API Keys im Repository** - .gitignore beachten

### Security Checklist:
- [ ] credentials/ in .gitignore
- [ ] .env.secrets in .gitignore  
- [ ] Service Account hat nur nötige Berechtigungen
- [ ] Secrets rotieren alle 90 Tage
- [ ] Cloud Audit Logs aktiviert

## Wartung & Updates

### Reguläre Updates:
```bash
# Dependencies aktualisieren
pip list --outdated
pip-compile --upgrade requirements.in

# Docker Base Image aktualisieren
docker pull python:3.12-slim

# Neues Deployment
./scripts/deploy-all.sh
```

### Backup:
- BigQuery Tabellen werden automatisch gesichert
- Code in Git Repository
- Container Images in Artifact Registry

## Quick Reference - Häufigste Befehle

### Komplettes Deployment (wenn Code geändert wurde)
```bash
./scripts/build-and-push.sh && ./scripts/deploy-cloud-run.sh
```

### Nur Umgebungsvariablen ändern
```bash
gcloud run services update ra-autohaus-tracker \
  --update-env-vars KEY=VALUE \
  --region=europe-west1
```

### Secrets aktualisieren
```bash
# Neue Secret-Version erstellen
echo -n "NEUER_WERT" | gcloud secrets versions add email-password --data-file=-

# Cloud Run neu starten, um neue Secrets zu laden
gcloud run services update ra-autohaus-tracker \
  --region=europe-west1 \
  --no-traffic
```

### Logs prüfen
```bash
# Letzte Fehler
gcloud run services logs read ra-autohaus-tracker \
  --region=europe-west1 \
  --limit=20 \
  --format="value(textPayload)" | grep ERROR

# Live Logs
gcloud run services logs tail ra-autohaus-tracker --region=europe-west1
```

### Service URL abrufen
```bash
gcloud run services describe ra-autohaus-tracker \
  --region=europe-west1 \
  --format='value(status.url)'
```

### Rollback zur vorherigen Version
```bash
gcloud run services update-traffic ra-autohaus-tracker \
  --to-revisions=PREV=100 \
  --region=europe-west1
```

## Support & Kontakt

Bei Problemen oder Fragen:
- Projektverantwortlicher: Maximilian Reinhardt
- Repository: github.com/[org]/ra-autohaus-tracker
- Cloud Console: console.cloud.google.com/run

---
*Letzte Aktualisierung: September 2025*
*Version: 1.0*