# RA Autohaus Tracker

Dieses Projekt wurde aufgeräumt und modernisiert. Die wichtigsten Änderungen:

- **Zentrale Konfiguration** in `.env` (Projekt, Region, Service, Registry, Umgebung, Tag)
- **Gemeinsame Variablen & Defaults** in `common.sh`
- **Einheitliches Deployment** über `scripts/deploy.sh` (statt mehrere Einzelskripte)
- **SLA-Logik DRY**: Ausgelagert in `sql/00_schema/10_sla_ref.sql` und `sql/10_views/20_prozesse_mit_sla.sql`
- **Robuste Tests & Linting** über `scripts/test.sh`
- **Entwicklung lokal** über `scripts/start_dev.sh`
- **SQL-Einspielung** über `scripts/sql_apply.sh`

## Setup

```bash
# Repo klonen
git clone <repo-url>
cd ra-autohaus-tracker

# .env anpassen
cp .env.example .env
nano .env
```

## Deployment

```bash
# Build & Push & Deploy (Artifact Registry)
TAG=test ./scripts/deploy.sh build
./scripts/deploy.sh push
ENVIRONMENT=test ./scripts/deploy.sh run

# Oder direkt aus Source deployen
./scripts/deploy.sh source
```

## SQL anwenden

```bash
./scripts/sql_apply.sh
```

## Lint & Tests

```bash
./scripts/test.sh
```

## Lokal entwickeln

```bash
PORT=8080 ./scripts/start_dev.sh
```
