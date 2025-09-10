#!/bin/bash
# RA Autohaus Tracker - BigQuery Funktionstest-Suite
# Testet alle Services und deren BigQuery-Integration

# Konfiguration
API_URL="http://localhost:8080"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================="
echo "RA Autohaus Tracker - BigQuery Test Suite"
echo "============================================="
echo ""

# Funktion für formatierte Ausgabe
test_endpoint() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    
    echo -e "${YELLOW}Test: $test_name${NC}"
    echo "Endpoint: $method $endpoint"
    
    if [ "$method" = "POST" ] || [ "$method" = "PUT" ]; then
        response=$(curl -s -X $method "$API_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" \
            -w "\nHTTP_STATUS:%{http_code}")
    else
        response=$(curl -s -X $method "$API_URL$endpoint" \
            -w "\nHTTP_STATUS:%{http_code}")
    fi
    
    http_status=$(echo "$response" | grep "HTTP_STATUS" | cut -d':' -f2)
    body=$(echo "$response" | sed '/HTTP_STATUS/d')
    
    if [ "$http_status" = "200" ] || [ "$http_status" = "201" ]; then
        echo -e "${GREEN}✓ Status: $http_status${NC}"
    else
        echo -e "${RED}✗ Status: $http_status${NC}"
    fi
    
    echo "Response: $body"
    echo "-------------------------------------------"
    echo ""
    
    # Kleine Pause zwischen Tests
    sleep 1
}

# 1. HEALTH CHECK
echo "========== 1. SYSTEM HEALTH CHECK =========="
test_endpoint "System Health" "GET" "/health" ""

# 2. FAHRZEUG ERSTELLEN - BMW X3 (Einkauf)
echo "========== 2. FAHRZEUG ERSTELLEN =========="
test_endpoint "BMW X3 - Neuer Einkauf" "POST" "/api/v1/fahrzeuge/" '{
    "fin": "WBAPB73516A123456",
    "marke": "BMW",
    "modell": "X3 xDrive30d",
    "antriebsart": "Diesel",
    "farbe": "Alpinweiß",
    "baujahr": 2023,
    "datum_erstzulassung": "2023-03-15",
    "kw_leistung": 210,
    "km_stand": 18500,
    "anzahl_fahrzeugschluessel": 2,
    "bereifungsart": "Sommer",
    "anzahl_vorhalter": 1,
    "ek_netto": 42500.00,
    "besteuerungsart": "Regel",
    "datenquelle_fahrzeug": "api"
}'

# 3. FAHRZEUG MIT PROZESS - Audi A6 (Anlieferung)
test_endpoint "Audi A6 - Mit Anlieferungsprozess" "POST" "/api/v1/fahrzeuge/" '{
    "fin": "WAUZZZ4G8KN123789",
    "marke": "Audi",
    "modell": "A6 Avant 45 TDI",
    "antriebsart": "Diesel",
    "farbe": "Navarrablau Metallic",
    "baujahr": 2024,
    "datum_erstzulassung": "2024-01-20",
    "kw_leistung": 170,
    "km_stand": 8900,
    "anzahl_fahrzeugschluessel": 2,
    "bereifungsart": "Winter",
    "anzahl_vorhalter": 1,
    "ek_netto": 48900.00,
    "besteuerungsart": "Regel",
    "datenquelle_fahrzeug": "api"
}'

# 4. FAHRZEUG MIT PROZESS - Mercedes C-Klasse (Aufbereitung)
test_endpoint "Mercedes C220d - Aufbereitung" "POST" "/api/v1/fahrzeuge/" '{
    "fin": "WDD2050091F999888",
    "marke": "Mercedes-Benz",
    "modell": "C 220 d T-Modell",
    "antriebsart": "Diesel",
    "farbe": "Obsidianschwarz",
    "baujahr": 2022,
    "datum_erstzulassung": "2022-06-10",
    "kw_leistung": 147,
    "km_stand": 45200,
    "anzahl_fahrzeugschluessel": 2,
    "bereifungsart": "Ganzjahr",
    "anzahl_vorhalter": 2,
    "ek_netto": 32800.00,
    "besteuerungsart": "Differenz",
    "datenquelle_fahrzeug": "api"
}'

# 5. ZAPIER WEBHOOK TEST - VW Golf (Foto-Prozess)
echo "========== 3. ZAPIER INTEGRATION TEST =========="
test_endpoint "Zapier Webhook - VW Golf Foto" "POST" "/api/v1/integration/zapier/webhook" '{
    "vin": "WVWZZZ1JZXW777666",
    "make": "Volkswagen",
    "model": "Golf VIII GTI",
    "process": "photos",
    "status": "In Bearbeitung",
    "assigned_to": "Thomas K.",
    "notes": "Fahrzeug wurde gewaschen, Foto-Session geplant für morgen",
    "mileage": 12500,
    "color": "Tornado Rot",
    "year": 2023,
    "purchase_price": 35500,
    "source": "zapier"
}'

# 6. FLOWERS EMAIL INTEGRATION - Porsche Cayenne (Werkstatt)
echo "========== 4. FLOWERS EMAIL TEST =========="
test_endpoint "Flowers Email - Porsche Cayenne Werkstatt" "POST" "/api/v1/integration/flowers/email" '{
    "subject": "Werkstattauftrag: Porsche Cayenne - TÜV Vorbereitung",
    "from": "werkstatt@reinhardtautomobile.de",
    "body": "FIN: WP1ZZZ9YZ8LA55555\nProzess: Werkstatt\nBearbeiter: Max R.\nStatus: TÜV-Vorbereitung\nNotizen: Bremsen prüfen, Ölwechsel durchführen",
    "fin": "WP1ZZZ9YZ8LA55555",
    "marke": "Porsche",
    "modell": "Cayenne S",
    "km_stand": 78900,
    "baujahr": 2021,
    "ek_netto": 68500,
    "prozess_typ": "Werkstatt",
    "status": "TÜV-Vorbereitung",
    "bearbeiter": "Maximilian Reinhardt"
}'

# 7. STATUS UPDATE - BMW X3
echo "========== 5. STATUS UPDATE TEST =========="
test_endpoint "Status Update - BMW X3 zu Aufbereitung" "PUT" "/api/v1/fahrzeuge/WBAPB73516A123456/status?new_status=Aufbereitung%20abgeschlossen&bearbeiter=Thomas%20K%C3%BCfner&notizen=Innenreinigung%20durchgef%C3%BChrt" ""
# 8. FAHRZEUGE ABRUFEN
echo "========== 6. FAHRZEUGE ABRUFEN =========="
test_endpoint "Alle Fahrzeuge" "GET" "/api/v1/fahrzeuge/?limit=10" ""

# 9. EINZELNES FAHRZEUG ABRUFEN
echo "========== 7. FAHRZEUG DETAILS =========="
test_endpoint "BMW X3 Details" "GET" "/api/v1/fahrzeuge/WBAPB73516A123456" ""

# 10. DASHBOARD KPIs
echo "========== 8. DASHBOARD KPIs =========="
test_endpoint "Dashboard KPIs" "GET" "/api/v1/dashboard/kpis" ""

# 11. WARTESCHLANGEN STATUS
test_endpoint "Warteschlangen" "GET" "/api/v1/dashboard/warteschlangen" ""

# 12. SLA ÜBERSICHT
test_endpoint "SLA Status" "GET" "/api/v1/dashboard/sla" ""

# 13. BEARBEITER WORKLOAD
test_endpoint "Bearbeiter Workload" "GET" "/api/v1/dashboard/bearbeiter" ""

# 14. PROZESS-DEFINITIONEN
echo "========== 9. INFO SERVICE =========="
test_endpoint "Prozess-Definitionen" "GET" "/api/v1/info/prozesse" ""

# 15. BEARBEITER INFO
test_endpoint "Bearbeiter Liste" "GET" "/api/v1/info/bearbeiter" ""

# ZUSAMMENFASSUNG
echo ""
echo "============================================="
echo "TEST-SUITE ABGESCHLOSSEN"
echo "============================================="
echo ""
echo "Prüfe jetzt in BigQuery:"
echo "1. SELECT * FROM \`ra-autohaus-tracker.autohaus.fahrzeuge_stamm\` ORDER BY created_at DESC LIMIT 10;"
echo "2. SELECT * FROM \`ra-autohaus-tracker.autohaus.fahrzeug_prozesse\` ORDER BY created_at DESC LIMIT 10;"
echo ""
echo "Erwartete Einträge:"
echo "- 5 neue Fahrzeuge in fahrzeuge_stamm"
echo "- Mindestens 3 Prozesse in fahrzeug_prozesse"
echo "- KPIs sollten die neuen Fahrzeuge reflektieren"