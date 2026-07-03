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
action="${1:-}"
error_burst_count="${ERROR_BURST_COUNT:-30}"
demo_app_url="${DEMO_APP_URL:-http://localhost:8080}"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/fault-injection.sh <action>

App VM actions:
  api-down | api-up
  catalog-down | catalog-up
  inventory-down | inventory-up
  cart-down | cart-up
  order-down | order-up
  payment-down | payment-up
  node-exporter-down | node-exporter-up
  promtail-down | promtail-up
  error-burst

Monitoring VM actions:
  loki-down | loki-up
  tempo-down | tempo-up
  mimir-down | mimir-up

Common actions:
  status
  recover-all

Environment:
  ERROR_BURST_COUNT=30
  DEMO_APP_URL=http://localhost:8080
USAGE
}

stack_name() {
  case "$compose_file" in
    docker-compose.app.yml)
      echo "app"
      ;;
    docker-compose.monitoring.yml)
      echo "monitoring"
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

require_stack() {
  local expected="$1"
  local current
  current="$(stack_name)"

  if [ "$current" != "$expected" ]; then
    echo "This action must be run on the ${expected} VM." >&2
    echo "Current COMPOSE_FILE: ${compose_file:-unset}" >&2
    echo "Create .env from the correct template or run the command on the correct VM." >&2
    exit 1
  fi
}

compose_stop() {
  local service="$1"
  echo "$(date -Is) action=stop service=${service}"
  docker compose stop "$service"
}

compose_start() {
  local service="$1"
  echo "$(date -Is) action=start service=${service}"
  docker compose start "$service"
}

error_burst() {
  require_stack app

  echo "$(date -Is) action=error-burst target=${demo_app_url} requests=${error_burst_count}"
  for _ in $(seq 1 "$error_burst_count"); do
    status="$(curl -sS -o /dev/null -m 5 -w "%{http_code}" "${demo_app_url}/error" || true)"
    printf '%s endpoint=/error status=%s\n' "$(date -Is)" "$status"
    sleep 0.2
  done
}

recover_all() {
  case "$(stack_name)" in
    app)
      echo "$(date -Is) action=recover-all stack=app"
      docker compose up -d api-service catalog-service inventory-service cart-service order-service payment-service node-exporter promtail
      ;;
    monitoring)
      echo "$(date -Is) action=recover-all stack=monitoring"
      docker compose up -d minio minio-init loki mimir tempo otel-collector prometheus node-exporter grafana
      ;;
    *)
      echo "Cannot detect stack. COMPOSE_FILE must be set in .env." >&2
      exit 1
      ;;
  esac
}

if [ -z "$action" ]; then
  usage
  exit 1
fi

case "$action" in
  api-down) require_stack app; compose_stop api-service ;;
  api-up) require_stack app; compose_start api-service ;;
  catalog-down) require_stack app; compose_stop catalog-service ;;
  catalog-up) require_stack app; compose_start catalog-service ;;
  inventory-down) require_stack app; compose_stop inventory-service ;;
  inventory-up) require_stack app; compose_start inventory-service ;;
  cart-down) require_stack app; compose_stop cart-service ;;
  cart-up) require_stack app; compose_start cart-service ;;
  order-down) require_stack app; compose_stop order-service ;;
  order-up) require_stack app; compose_start order-service ;;
  payment-down) require_stack app; compose_stop payment-service ;;
  payment-up) require_stack app; compose_start payment-service ;;
  node-exporter-down) require_stack app; compose_stop node-exporter ;;
  node-exporter-up) require_stack app; compose_start node-exporter ;;
  promtail-down) require_stack app; compose_stop promtail ;;
  promtail-up) require_stack app; compose_start promtail ;;
  error-burst) error_burst ;;
  loki-down) require_stack monitoring; compose_stop loki ;;
  loki-up) require_stack monitoring; compose_start loki ;;
  tempo-down) require_stack monitoring; compose_stop tempo ;;
  tempo-up) require_stack monitoring; compose_start tempo ;;
  mimir-down) require_stack monitoring; compose_stop mimir ;;
  mimir-up) require_stack monitoring; compose_start mimir ;;
  status) docker compose ps ;;
  recover-all) recover_all ;;
  -h|--help|help) usage ;;
  *)
    echo "Unknown action: ${action}" >&2
    echo >&2
    usage
    exit 1
    ;;
esac
