#!/usr/bin/env bash
set -euo pipefail

base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$base_dir"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

compose_file="${COMPOSE_FILE:-}"

echo "[1/4] Docker Compose service status"
docker compose ps

if [ "$compose_file" = "docker-compose.monitoring.yml" ]; then
  app_ip="${APP_VM_PRIVATE_IP:?APP_VM_PRIVATE_IP must be set in .env}"

  echo
  echo "[2/4] Monitoring VM local endpoints"
  curl -fsS http://localhost:3000/api/health
  curl -fsS http://localhost:3100/ready
  curl -fsS http://localhost:9009/ready
  curl -fsS http://localhost:3200/ready

  echo
  echo "[3/4] App VM scrape endpoints"
  curl -fsS "http://${app_ip}:8080/metrics" >/dev/null
  curl -fsS "http://${app_ip}:8081/metrics" >/dev/null
  curl -fsS "http://${app_ip}:8082/metrics" >/dev/null
  curl -fsS "http://${app_ip}:9100/metrics" >/dev/null

  echo
  echo "[4/4] Monitoring health checks passed."
elif [ "$compose_file" = "docker-compose.app.yml" ]; then
  monitoring_ip="${MONITORING_VM_PRIVATE_IP:?MONITORING_VM_PRIVATE_IP must be set in .env}"

  echo
  echo "[2/4] App VM local services"
  curl -fsS http://localhost:8080/ >/dev/null
  curl -fsS http://localhost:8080/checkout >/dev/null || true
  curl -fsS http://localhost:8081/metrics >/dev/null
  curl -fsS http://localhost:8082/metrics >/dev/null
  curl -fsS http://localhost:9100/metrics >/dev/null

  echo
  echo "[3/4] Monitoring VM ingestion endpoints"
  curl -fsS "http://${monitoring_ip}:3100/ready"
  curl -sS "http://${monitoring_ip}:4318/" >/dev/null || true

  echo
  echo "[4/4] App health checks passed."
else
  echo "COMPOSE_FILE must be docker-compose.monitoring.yml or docker-compose.app.yml in .env" >&2
  exit 1
fi
