#!/bin/bash
# RA Autohaus Tracker - Log Monitoring Tools

export RA_PROJECT="${RA_PROJECT:-ra-autohaus-tracker}"
export RA_SERVICE="${RA_SERVICE:-ra-autohaus-tracker}"
export RA_API_URL="${RA_API_URL:-https://ra-autohaus-tracker-p6yblocfea-ey.a.run.app}"
export PYTHONWARNINGS="ignore::SyntaxWarning"

# Helper function for table output
__fin_to_table() {
  local ONLY_ERRORS="$1"
  jq -r '
    .[] |
    (.timestamp | sub("\\..*Z$"; "Z")) as $ts |
    (.severity // "") as $sev |
    ($sev | ascii_upcase) as $SEV |
    ( .textPayload // "" ) as $TP |
    ( .jsonPayload.message? // "" ) as $JM |
    select(
      "'"${ONLY_ERRORS}"'" != "1" or
      $SEV == "ERROR" or
      ($TP | test("(?i)\\berror\\b")) or
      ($JM | test("(?i)\\berror\\b"))
    ) |
    [$ts, (if $TP != "" then $TP else (if $JM != "" then $JM else "-" end) end), $SEV] | @tsv
  ' | awk -F'\t' '
    function color(s, c) { return c s "\033[0m" }
    {
      ts=$1; msg=$2; sev=$3
      red="\033[31m"; yellow="\033[33m"
      if (sev=="ERROR" || msg ~ /(^|[^A-Za-z])ERROR([^A-Za-z]|$)/) msg=color(msg, red)
      else if (sev=="WARNING" || msg ~ /(^|[^A-Za-z])WARNING([^A-Za-z]|$)/) msg=color(msg, yellow)
      printf "%s\t%s\n", ts, msg
    }
  ' | column -t -s $'\t'
}

# Live monitoring
monitor() {
  echo "📡 Live Monitoring: $RA_API_URL"
  echo "──────────────────────────────────────"
  gcloud beta logging tail \
    "resource.labels.service_name=\"$RA_SERVICE\"" \
    --project=$RA_PROJECT \
    --format="value(timestamp,httpRequest.requestMethod,httpRequest.requestUrl,httpRequest.status,jsonPayload.message,textPayload)"
}

# Monitor with FIN filter
monitor_fin() {
  local FIN="$1"
  if [ -z "$FIN" ]; then
    echo "Usage: $0 monitor-fin <FIN>"
    exit 1
  fi
  echo "📡 Monitoring FIN: $FIN"
  echo "──────────────────────────────────────"
  gcloud beta logging tail \
    "resource.labels.service_name=\"$RA_SERVICE\" AND (jsonPayload.fin=\"$FIN\" OR textPayload:\"$FIN\")" \
    --project=$RA_PROJECT \
    --format="value(timestamp,httpRequest.requestUrl,jsonPayload)"
}

# Pretty monitoring with JQ
monitor_pretty() {
  echo "📡 Pretty Monitoring: $RA_API_URL"
  echo "──────────────────────────────────────"
  gcloud beta logging tail \
    "resource.labels.service_name=\"$RA_SERVICE\"" \
    --project=$RA_PROJECT \
    --format=json | jq -r '
      (.timestamp | split(".")[0]) + " | " +
      if .httpRequest then
        "HTTP: " + .httpRequest.requestMethod + " " + .httpRequest.requestUrl + " [" + (.httpRequest.status | tostring) + "]"
      elif .jsonPayload then
        "JSON: " + (.jsonPayload.message // .jsonPayload | tostring)
      else
        "LOG: " + (.textPayload // "no content")
      end'
}

# Show recent errors
errors() {
  echo "❌ Recent Errors:"
  gcloud logging read \
    "resource.labels.service_name=\"$RA_SERVICE\" AND severity>=ERROR" \
    --project=$RA_PROJECT \
    --limit=20 \
    --format=json | jq -r '.[] | 
      (.timestamp | split(".")[0]) + " | " + 
      .severity + " | " + 
      (.jsonPayload.message // .textPayload // "no message")'
}

# Show recent requests
requests() {
  local LIMIT="${1:-20}"
  echo "📜 Last $LIMIT API Requests:"
  gcloud logging read \
    "resource.labels.service_name=\"$RA_SERVICE\" AND httpRequest.requestUrl!=\"\"" \
    --project=$RA_PROJECT \
    --limit=$LIMIT \
    --format=json | jq -r '.[] | 
      (.timestamp | split(".")[0]) + " | " + 
      .httpRequest.requestMethod + " " + 
      .httpRequest.requestUrl + " | Status: " + 
      (.httpRequest.status | tostring)'
}

# Main command handler
case "${1:-monitor}" in
  monitor) monitor ;;
  monitor-fin) monitor_fin "$2" ;;
  pretty) monitor_pretty ;;
  errors) errors ;;
  requests) requests "$2" ;;
  *)
    echo "Usage: $0 {monitor|monitor-fin <FIN>|pretty|errors|requests [limit]}"
    exit 1
    ;;
esac
