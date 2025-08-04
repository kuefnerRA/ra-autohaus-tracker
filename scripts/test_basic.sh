#!/bin/bash
set -e

echo "🧪 Basis-Tests für RA Autohaus Tracker"

# Virtual Environment aktivieren
source venv/bin/activate

# Code Quality Checks
echo "1. Code-Qualität prüfen..."
echo "  - Flake8 Linting..."
flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics || echo "⚠️  Linting-Fehler gefunden"

echo "  - Black Formatierung prüfen..."
black --check src || echo "⚠️  Formatierung erforderlich (black src)"

echo "  - Import-Sortierung prüfen..."
isort --check-only src || echo "⚠️  Import-Sortierung erforderlich (isort src)"

# Unit Tests (falls vorhanden)
echo "2. Unit Tests..."
if [ -f "tests/test_basic.py" ]; then
    pytest tests/ -v
else
    echo "⚠️  Keine Tests gefunden - tests/test_basic.py erstellen"
fi

echo "✅ Basis-Tests abgeschlossen!"
