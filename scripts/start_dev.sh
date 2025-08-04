#!/bin/bash
set -e

echo "🚀 RA Autohaus Tracker Development Server"

# Virtual Environment aktivieren
source venv/bin/activate

# Environment Variables
export PYTHONPATH=$(pwd)
export ENVIRONMENT=development
export GCP_PROJECT_ID=ra-autohaus-tracker

echo "🌐 Starting server on http://localhost:8080"
echo "📖 API Docs: http://localhost:8080/docs"

uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
