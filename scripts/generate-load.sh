#!/usr/bin/env bash
set -euo pipefail

target="${1:-http://localhost:8080}"
iterations="${2:-60}"

echo "Generating demo traffic against ${target} (${iterations} iterations)"

for i in $(seq 1 "$iterations"); do
  curl -fsS "${target}/" >/dev/null
  curl -fsS "${target}/work" >/dev/null

  if [ $((i % 10)) -eq 0 ]; then
    curl -sS -o /dev/null -w "intentional error status=%{http_code}\n" "${target}/error"
  fi

  sleep 1
done

echo "Done. Check Grafana Logs Overview, VM Metrics, and Traces Overview dashboards."

