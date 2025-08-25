# scripts/test_docker.sh
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/../common.sh"

echo "🐳 Docker Build & Test"

# Build
docker build -t ra-autohaus-tracker-test .

# Container starten
CONTAINER_ID=$(docker run -d -p 8081:8080 \
  -e ENVIRONMENT=test \
  -e PROJECT_ID=test-project \
  ra-autohaus-tracker-test)

echo "Container gestartet: $CONTAINER_ID"

# Warten bis Service bereit
sleep 10

# Health Check
echo "• Health Check"
curl -f http://localhost:8081/health || {
  echo "❌ Health Check fehlgeschlagen"
  docker logs $CONTAINER_ID
  docker stop $CONTAINER_ID
  exit 1
}

# API Tests
echo "• API Tests"
curl -f http://localhost:8081/ || {
  echo "❌ Root Endpoint fehlgeschlagen"
  docker stop $CONTAINER_ID
  exit 1
}

docker stop $CONTAINER_ID
echo "✅ Docker Test erfolgreich"