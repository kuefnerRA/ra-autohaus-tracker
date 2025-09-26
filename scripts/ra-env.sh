#!/bin/bash
# RA Autohaus Tracker - Environment Management

export RA_PROJECT="ra-autohaus-tracker"
export RA_SERVICE="ra-autohaus-tracker"
export API_URL_LOCAL="http://localhost:8080"
export API_URL_PROD=$(gcloud run services describe ra-autohaus-tracker \
  --region=europe-west3 \
  --project=ra-autohaus-tracker \
  --format="value(status.url)" 2>/dev/null)

# Switch to local API
use_local() {
  export RA_API_URL="$API_URL_LOCAL"
  echo "🏠 Using local API: $RA_API_URL"
}

# Switch to production API
use_prod() {
  export RA_API_URL="$API_URL_PROD"
  echo "☁️ Using production API: $RA_API_URL"
}

# Show current API configuration
show_config() {
  echo "📍 Current Configuration:"
  echo "   Project: $RA_PROJECT"
  echo "   Service: $RA_SERVICE"
  echo "   Current API: ${RA_API_URL:-Not set}"
  echo "   Local: $API_URL_LOCAL"
  echo "   Prod: $API_URL_PROD"
}

# Health check
health() {
  local URL="${1:-$RA_API_URL}"
  echo "🧪 Testing: $URL/health"
  curl -s "$URL/health" | jq '.'
}

# Main command handler
case "${1:-show}" in
  local) use_local ;;
  prod) use_prod ;;
  show) show_config ;;
  health) health "$2" ;;
  *)
    echo "Usage: $0 {local|prod|show|health [url]}"
    exit 1
    ;;
esac
