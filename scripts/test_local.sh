# scripts/test_local.sh erstellen
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/../common.sh"

[[ -d "$DIR/../venv" ]] && source "$DIR/../venv/bin/activate" || true

echo "🧪 Lokale Tests mit Coverage"

export PYTHONPATH="${PYTHONPATH:-$(cd "$DIR/.."; pwd)}"
export ENVIRONMENT="test"

# Unit Tests
echo "• Unit Tests"
pytest tests/ -m "unit" -v

# Integration Tests  
echo "• Integration Tests"
pytest tests/ -m "integration" -v

# Alle Tests mit Coverage
echo "• Coverage Report"
pytest tests/ --cov=src --cov-report=html --cov-report=term

echo "✅ Tests abgeschlossen - Coverage Report: htmlcov/index.html"