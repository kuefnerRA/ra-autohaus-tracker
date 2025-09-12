#!/bin/bash
# Secret Management für Cloud Run

set -e

PROJECT_ID="ra-autohaus-tracker"
SERVICE_ACCOUNT="ra-dev-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com"

function create_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2
    
    echo "🔐 Erstelle Secret: ${SECRET_NAME}..."
    
    # Prüfe ob Secret existiert
    if gcloud secrets describe ${SECRET_NAME} >/dev/null 2>&1; then
        echo "   Secret existiert bereits. Erstelle neue Version..."
        echo -n "${SECRET_VALUE}" | gcloud secrets versions add ${SECRET_NAME} --data-file=-
    else
        echo "   Erstelle neues Secret..."
        echo -n "${SECRET_VALUE}" | gcloud secrets create ${SECRET_NAME} \
            --data-file=- \
            --replication-policy="automatic"
        
        # Gewähre Service Account Zugriff
        gcloud secrets add-iam-policy-binding ${SECRET_NAME} \
            --member="serviceAccount:${SERVICE_ACCOUNT}" \
            --role="roles/secretmanager.secretAccessor"
    fi
}

# Secrets aus .env.secrets lesen (falls vorhanden)
if [ -f .env.secrets ]; then
    echo "📋 Lade Secrets aus .env.secrets..."
    source .env.secrets
    
    # Email Address (Username)
    if [ ! -z "${EMAIL_ADDRESS}" ]; then
        create_secret "email-address" "${EMAIL_ADDRESS}"
    fi
    
    # Email Password
    if [ ! -z "${EMAIL_PASSWORD}" ]; then
        create_secret "email-password" "${EMAIL_PASSWORD}"
    fi
    
    # IMAP Server
    if [ ! -z "${IMAP_SERVER}" ]; then
        create_secret "imap-server" "${IMAP_SERVER}"
    fi
    
    echo "✅ Alle Email-Secrets verarbeitet"
else
    echo "⚠️  Keine .env.secrets gefunden"
    echo "   Erstelle eine .env.secrets Datei mit:"
    echo "   EMAIL_ADDRESS=deine-email@domain.de"
    echo "   EMAIL_PASSWORD=dein-passwort"
    echo "   IMAP_SERVER=imap.gmail.com"
fi

# Liste alle Secrets
echo ""
echo "📋 Verfügbare Secrets:"
gcloud secrets list --limit=10
