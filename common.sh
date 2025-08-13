#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
trap 'echo "❌ ${BASH_SOURCE[0]}:$LINENO: $BASH_COMMAND" >&2' ERR

# Load .env if present
if [[ -f "$(dirname "$0")/../.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$(dirname "$0")/../.env"
  set +a
elif [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

: "${PROJECT_ID:?PROJECT_ID required}"
: "${REGION:=europe-west3}"
: "${SERVICE_NAME:?SERVICE_NAME required}"
: "${REPO:=apps}"
: "${TAG:=latest}"
: "${ENVIRONMENT:=dev}"

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE_NAME}"

# Backward compatibility for legacy code that still expects GCP_PROJECT_ID
export GCP_PROJECT_ID="${PROJECT_ID}"

check_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "❌ '$1' ist nicht installiert oder nicht im PATH"; exit 1; }
}
