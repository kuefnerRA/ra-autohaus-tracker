#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "$DIR/../common.sh"

# Optional venv
[[ -d "$DIR/../venv" ]] && source "$DIR/../venv/bin/activate" || true

echo "🧪 Lint & Tests"

if command -v flake8 >/dev/null 2>&1; then
  echo "• flake8"
  flake8 src || echo "⚠️ flake8 Fehler (weiter)"
fi

if command -v black >/dev/null 2>&1; then
  echo "• black --check"
  black --check src || echo "⚠️ black Check fehlgeschlagen (weiter)"
fi

if command -v isort >/dev/null 2>&1; then
  echo "• isort --check-only"
  isort --check-only src || echo "⚠️ isort Check fehlgeschlagen (weiter)"
fi

if ls "$DIR/../tests"/test_*.py >/dev/null 2>&1; then
  if command -v pytest >/dev/null 2>&1; then
    echo "• pytest"
    pytest -q || echo "⚠️ pytest fehlgeschlagen"
  else
    echo "ℹ️ pytest nicht installiert"
  fi
else
  echo "ℹ️ keine Tests gefunden"
fi
