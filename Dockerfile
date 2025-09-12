FROM python:3.12-slim

# Arbeitsverzeichnis setzen
WORKDIR /app

# System-Dependencies installieren (falls benötigt)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Requirements kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY . .

# Port für Cloud Run
EXPOSE 8080

# WICHTIG: src.main:app weil die App in src/main.py liegt!
CMD ["gunicorn", "src.main:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "0"]
