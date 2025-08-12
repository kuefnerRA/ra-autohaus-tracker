#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "$DIR/../common.sh"

check_cmd bq

shopt -s nullglob
files=( "$DIR/../sql/00_schema/"*.sql "$DIR/../sql/10_views/"*.sql )
for f in "${files[@]}"; do
  echo "➡  Apply: $f"
  bq query --use_legacy_sql=false < "$f"
done
echo "✅ SQL apply fertig"
