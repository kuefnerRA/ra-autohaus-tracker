#!/bin/bash
# RA Autohaus Tracker - API Testing Tools

export RA_API_URL="${RA_API_URL:-https://ra-autohaus-tracker-p6yblocfea-ey.a.run.app}"

# Test single endpoint
test_endpoint() {
  local ENDPOINT="${1:-/health}"
  echo "[TEST] Testing: $RA_API_URL$ENDPOINT"
  curl -s "$RA_API_URL$ENDPOINT" | jq .
  echo "[DONE]"
}

# Complete test suite - CORRECTED PATHS
test_suite() {
  echo "[TEST] RA Autohaus Tracker API Test Suite"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  # Health (no prefix)
  echo -e "\n1️⃣ Health Check:"
  curl -s "$RA_API_URL/health" | jq '{status, version}'
  
  # API v1 endpoints
  echo -e "\n2️⃣ Fahrzeuge (First 2):"
  curl -s "$RA_API_URL/api/v1/fahrzeuge?limit=2" | jq '.'
  
  echo -e "\n3️⃣ Dashboard KPIs:"
  curl -s "$RA_API_URL/api/v1/dashboard/kpis" | jq '.'
  
  echo -e "\n4️⃣ System Info:"
  curl -s "$RA_API_URL/api/v1/info/system" | jq '.'
  
  echo -e "\n5️⃣ Prozess-Typen:"
  curl -s "$RA_API_URL/api/v1/info/prozesse" | jq '.'
}

# Check single FIN
check_fin() {
  local FIN="${1:-WVWZZZ1JZ8W123456}"
  echo "🔍 Checking FIN: $FIN"
  curl -s "$RA_API_URL/api/v1/fahrzeuge/$FIN" | jq '.' || echo "❌ FIN not found"
}

# Test Zapier webhook
test_zapier() {
  local FIN="${1:-TESTWVW$(date +%s | tail -c 8)}"
  echo "📮 Sending Zapier Webhook for FIN: $FIN"
  
  curl -X POST "$RA_API_URL/api/v1/integration/zapier/webhook" \
    -H "Content-Type: application/json" \
    -d '{
      "fin": "'$FIN'",
      "status": "ANLIEFERUNG",
      "bearbeiter": "Thomas Küfner",
      "timestamp": "'$(date -Iseconds)'",
      "notizen": "Test via CLI"
    }' | jq '.'
}

# Test Email webhook  
test_email() {
  local FIN="${1:-TESTWVW$(date +%s | tail -c 8)}"
  echo "📧 Simulating Email for FIN: $FIN"
  
  curl -X POST "$RA_API_URL/api/v1/integration/email/webhook" \
    -H "Content-Type: application/json" \
    -d '{
      "from": "flowers@reinhardt-automobile.de",
      "subject": "Fahrzeug '$FIN' - Statusupdate",
      "body": "Status: AUFBEREITUNG\nBearbeiter: Maximilian Reinhardt\nNotiz: Test Email",
      "received_at": "'$(date -Iseconds)'"
    }' | jq '.'
}

# Show available endpoints
show_endpoints() {
  echo "📚 Available Endpoints:"
  curl -s "$RA_API_URL/health" | jq '.endpoints'
}

# Test all integrations
test_integrations() {
  echo "🔌 Testing Integration Endpoints:"
  
  echo -e "\n1. Zapier Webhook:"
  test_endpoint "/api/v1/integration/zapier/webhook"
  
  echo -e "\n2. Email Webhook:"
  test_endpoint "/api/v1/integration/email/process"
  
  echo -e "\n3. Dashboard KPIs:"
  test_endpoint "/api/v1/dashboard/kpis"
  
  echo -e "\n4. Warteschlangen:"
  test_endpoint "/api/v1/dashboard/warteschlangen"
}

# Main command handler
case "${1:-suite}" in
  endpoint) test_endpoint "$2" ;;
  suite) test_suite ;;
  fin) check_fin "$2" ;;
  zapier) test_zapier "$2" ;;
  email) test_email "$2" ;;
  endpoints) show_endpoints ;;
  integrations) test_integrations ;;
  *)
    echo "Usage: $0 {endpoint <path>|suite|fin <FIN>|zapier [FIN]|email [FIN]|endpoints|integrations}"
    exit 1
    ;;
esac
