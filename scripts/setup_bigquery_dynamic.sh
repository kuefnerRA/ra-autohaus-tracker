#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "$DIR/../common.sh"

check_cmd bq

echo "🛠  BigQuery setup"
echo "Project: ${PROJECT_ID}"
echo "Region : ${REGION}"

# Dataset (idempotent)
bq --location="${REGION}" --project_id="${PROJECT_ID}" \
   mk -d --default_table_expiration 0 autohaus || true

echo "✅ BigQuery setup completed"
