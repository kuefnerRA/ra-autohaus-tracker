#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "$DIR/../common.sh"

# Optional venv
[[ -d "$DIR/../venv" ]] && source "$DIR/../venv/bin/activate" || true

export PYTHONPATH="${PYTHONPATH:-$(cd "$DIR/.."; pwd)}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export GCP_PROJECT_ID="${PROJECT_ID}"
PORT="${PORT:-8080}"

echo "🚀 Dev-Server http://localhost:${PORT} (ENV=${ENVIRONMENT})"
echo "📖 Docs: http://localhost:${PORT}/docs"

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "ℹ️ uvicorn nicht gefunden – versuche Installation"
  pip install -q uvicorn || true
fi

uvicorn src.main:app --reload --host 0.0.0.0 --port "${PORT}"
