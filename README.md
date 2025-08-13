# RA Autohaus Tracker

Ein internes Tool zur Erfassung, Analyse und Auswertung von Prozessen im Autohaus.  
Es ermöglicht die Erfassung von Fahrzeugprozessen, SLA-Überwachung und Bereitstellung von Daten über eine API, die auf **Google Cloud Run** gehostet wird.

## 🚀 Deployment

Für eine Schritt-für-Schritt-Anleitung zum Build, Test und Deployment siehe:

➡ [Deploy-Checkliste](docs/DEPLOY_CHECKLIST.md)

Diese Checkliste enthält:
- Vorbereitung der Google Cloud Authentifizierung
- Build & Push zu Artifact Registry
- Deployment in Test- und Produktionsumgebung
- Ausführung der SQL-Skripte
- Lokale Tests
- Nachbereitung & Commits

## 📦 Voraussetzungen

- [Python 3.11+](https://www.python.org/downloads/)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- Zugriff auf das GCP-Projekt `ra-autohaus-tracker`
- Docker installiert und lauffähig
- BigQuery-Berechtigungen (Lesen/Schreiben im Dataset `autohaus`)

## 🛠 Installation (lokal)

```bash
# Repository klonen
git clone git@github.com:kuefnerRA/ra-autohaus-tracker.git
cd ra-autohaus-tracker

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate   # oder .\venv\Scripts\activate auf Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# .env aus Vorlage erstellen und anpassen
cp .env.example .env
```

## ▶ Lokale Entwicklung starten

```bash
PORT=8080 ./scripts/start_dev.sh
```
Danach im Browser öffnen:  
- API-Dokumentation: `http://localhost:8080/docs`  
- Health-Check: `http://localhost:8080/health`

## 🧪 Tests

```bash
./scripts/test.sh
```

## 💾 SQL-Updates anwenden

Alle relevanten Tabellen, Views und Änderungen in BigQuery anwenden:
```bash
./scripts/sql_apply.sh
```

## 📜 Lizenz

Dieses Projekt ist proprietär und intern für **Reinhardt Automobile GmbH** bestimmt.  
Keine externe Nutzung oder Weitergabe ohne ausdrückliche Genehmigung.
