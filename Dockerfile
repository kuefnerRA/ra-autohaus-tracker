FROM python:3.11-slim

# Arbeitsverzeichnis setzen
WORKDIR /app

# System-Dependencies installieren
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY src/ ./src/
COPY . .

# Port für Cloud Run
ENV PORT=8080
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production
ENV GCP_PROJECT_ID=ra-autohaus-tracker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# User für Sicherheit
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# FastAPI starten
CMD exec uvicorn src.main:app --host 0.0.0.0 --port $PORT --workers 1
