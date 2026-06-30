#!/usr/bin/env bash
set -euo pipefail

base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$base_dir"

echo "[1/5] Docker Compose service status"
docker compose ps

echo
echo "[2/5] Grafana health"
curl -fsS http://localhost:3000/api/health

echo
echo "[3/5] Loki ready"
curl -fsS http://localhost:3100/ready

echo
echo "[4/5] Mimir ready"
curl -fsS http://localhost:9009/ready

echo
echo "[5/5] Tempo ready"
curl -fsS http://localhost:3200/ready

echo
echo "Core health checks passed."

