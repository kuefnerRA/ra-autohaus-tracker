#!/usr/bin/env bash
# Unified deploy script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "$DIR/../common.sh"

cmd="${1:-}"
case "$cmd" in
  build)
    check_cmd docker
    echo "🐳 Build: ${IMAGE_URI}:${TAG}"
    docker build -t "${IMAGE_URI}:${TAG}" .
    ;;
  push)
    check_cmd gcloud
    check_cmd docker
    echo "🔐 Docker auth for Artifact Registry"
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" -q
    echo "📤 Push: ${IMAGE_URI}:${TAG}"
    docker push "${IMAGE_URI}:${TAG}"
    ;;
  run)
    check_cmd gcloud
    echo "🚀 Deploy to Cloud Run: ${SERVICE_NAME} (${ENVIRONMENT})"
    gcloud run deploy "${SERVICE_NAME}" \
      --image "${IMAGE_URI}:${TAG}" \
      --region "${REGION}" \
      --platform managed \
      --allow-unauthenticated \
      --set-env-vars "ENVIRONMENT=${ENVIRONMENT}"
    URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format='value(status.url)')
    echo "🌐 Service URL: ${URL}"
    if command -v curl >/dev/null 2>&1; then
      echo "🩺 Healthcheck: ${URL}/health"
      if curl -fsS "${URL}/health" >/dev/null; then
        echo "✅ Health OK"
      else
        echo "⚠️ Healthcheck fehlgeschlagen (optional)"
      fi
    fi
    ;;
  source)
    check_cmd gcloud
    echo "🚀 Deploy from source to Cloud Run"
    gcloud run deploy "${SERVICE_NAME}" \
      --source . \
      --region "${REGION}" \
      --platform managed \
      --allow-unauthenticated
    ;;
  *)
    echo "Usage: $0 {build|push|run|source}"
    exit 2
    ;;
esac
