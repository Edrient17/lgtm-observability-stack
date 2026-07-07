#!/usr/bin/env bash
set -euo pipefail

base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$base_dir"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a

  echo "[1/3] Monitoring VM Docker Compose service status"
  docker compose ps

  echo
  echo "[2/3] Monitoring VM local endpoints"
  curl -fsS http://localhost:3000/api/health
  curl -fsS http://localhost:3100/ready
  curl -fsS http://localhost:9009/ready
  curl -fsS http://localhost:3200/ready

  echo
  echo "[3/3] Monitoring health checks passed."
else
  echo "[1/4] App VM K3S resource status"
  kubectl -n msa-demo get pods,svc,daemonset

  echo
  echo "[2/4] App VM local demo endpoints"
  curl -fsS http://localhost:8080/ >/dev/null
  curl -fsS http://localhost:8080/browse >/dev/null
  curl -fsS http://localhost:8080/cart/add >/dev/null || true
  curl -fsS http://localhost:8080/checkout >/dev/null || true

  echo
  echo "[3/4] App VM local scrape endpoints"
  curl -fsS http://localhost:8080/metrics >/dev/null
  curl -fsS http://localhost:8081/metrics >/dev/null
  curl -fsS http://localhost:8082/metrics >/dev/null
  curl -fsS http://localhost:8083/metrics >/dev/null
  curl -fsS http://localhost:8084/metrics >/dev/null
  curl -fsS http://localhost:8085/metrics >/dev/null
  curl -fsS http://localhost:9100/metrics >/dev/null

  echo
  echo "[4/4] App K3S health checks passed."
fi
