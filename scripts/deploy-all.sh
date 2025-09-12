#!/bin/bash
# Komplettes Deployment von A bis Z

set -e

echo "🚀 RA Autohaus Tracker - Vollständiges Deployment"
echo "=================================================="

# 1. Setup
echo ""
echo "1️⃣ Setup Umgebung..."
./scripts/setup-env.sh

# 2. Secrets
echo ""
echo "2️⃣ Manage Secrets..."
./scripts/manage-secrets.sh

# 3. Build & Push
echo ""
echo "3️⃣ Build und Push Docker Image..."
./scripts/build-and-push.sh

# 4. Deploy
echo ""
echo "4️⃣ Deploy zu Cloud Run..."
./scripts/deploy-cloud-run.sh

echo ""
echo "🎉 Deployment komplett abgeschlossen!"
