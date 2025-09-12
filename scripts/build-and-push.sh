#!/bin/bash
# Docker Build und Push zu Artifact Registry

set -e

PROJECT_ID="ra-autohaus-tracker"
REGION="europe-west1"
REPOSITORY="ra-docker-repo"
IMAGE_NAME="ra-autohaus-tracker"
REGISTRY="${REGION}-docker.pkg.dev"

# Version aus Git-Hash oder Datum generieren
VERSION=$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d-%H%M%S)
FULL_IMAGE_PATH="${REGISTRY}/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}"

echo "🐳 Baue Docker Image..."
echo "   Version: ${VERSION}"

docker build -t ${IMAGE_NAME}:${VERSION} .
docker tag ${IMAGE_NAME}:${VERSION} ${FULL_IMAGE_PATH}:${VERSION}
docker tag ${IMAGE_NAME}:${VERSION} ${FULL_IMAGE_PATH}:latest

echo "📤 Pushe Image zu Artifact Registry..."
docker push ${FULL_IMAGE_PATH}:${VERSION}
docker push ${FULL_IMAGE_PATH}:latest

echo "✅ Image erfolgreich gepusht:"
echo "   ${FULL_IMAGE_PATH}:${VERSION}"
echo "   ${FULL_IMAGE_PATH}:latest"

# Speichere Image-Path für Deploy-Script
echo "${FULL_IMAGE_PATH}:${VERSION}" > .last-build-image
echo "VERSION=${VERSION}" >> .last-build-image
