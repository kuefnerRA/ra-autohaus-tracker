#!/bin/bash
# RA Autohaus Tracker - Database Query Tool

SQL_DIR="$HOME/dev/ra-autohaus-tracker/scripts/sql"
PROJECT="ra-autohaus-tracker"

# Execute SQL file
execute_sql() {
  local sql_file="$1"
  local format="${2:-pretty}"
  
  if [ ! -f "$SQL_DIR/$sql_file" ]; then
    echo "❌ SQL file not found: $sql_file"
    return 1
  fi
  
  bq query \
    --use_legacy_sql=false \
    --format="$format" \
    --project_id="$PROJECT" \
    < "$SQL_DIR/$sql_file"
}

# Database status overview
db_status() {
  echo "📊 RA Autohaus Tracker - Database Status"
  echo "========================================="
  execute_sql "db_status.sql"
}

# List vehicles
db_vehicles() {
  echo "🚗 Fahrzeuge (Stammdaten)"
  echo "========================"
  execute_sql "vehicles_list.sql"
}

# List processes
db_processes() {
  echo "🔄 Prozesse (Aktuell)"
  echo "===================="
  execute_sql "processes_list.sql"
}

# Active processes with SLA
db_active() {
  echo "⚡ Aktive Prozesse mit SLA-Status"
  echo "================================="
  execute_sql "processes_active.sql"
}

# Execute custom SQL file
db_custom() {
  local file="$1"
  if [ -z "$file" ]; then
    echo "Usage: $0 custom <sql_filename>"
    echo "Available SQL files:"
    ls -1 "$SQL_DIR"/*.sql | xargs -n1 basename
    return 1
  fi
  execute_sql "$file"
}

# Export to JSON
db_export() {
  local query="$1"
  local output="${2:-export.json}"
  execute_sql "$query" "json" > "$output"
  echo "✅ Exported to $output"
}

# Main command handler
case "${1:-status}" in
  status)    db_status ;;
  vehicles)  db_vehicles ;;
  processes) db_processes ;;
  active)    db_active ;;
  custom)    db_custom "$2" ;;
  export)    db_export "$2" "$3" ;;
  list)      
    echo "📋 Available SQL queries:"
    ls -1 "$SQL_DIR"/*.sql | xargs -n1 basename | sed 's/\.sql$//'
    ;;
  *)
    echo "Usage: $0 {status|vehicles|processes|active|custom <file>|export <file> [output]|list}"
    exit 1
    ;;
esac
