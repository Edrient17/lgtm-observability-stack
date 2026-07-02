#!/usr/bin/env bash
set -euo pipefail

target="${1:-${DEMO_APP_URL:-http://localhost:8080}}"
max_requests="${MAX_REQUESTS_PER_RUN:-12}"
idle_chance="${IDLE_CHANCE_PERCENT:-25}"
error_chance="${ERROR_CHANCE_PERCENT:-10}"
burst_chance="${BURST_CHANCE_PERCENT:-12}"
curl_timeout="${CURL_TIMEOUT_SECONDS:-5}"

if [ "$max_requests" -lt 1 ]; then
  echo "MAX_REQUESTS_PER_RUN must be greater than 0" >&2
  exit 1
fi

rand_percent() {
  echo $((RANDOM % 100))
}

request() {
  local endpoint="$1"
  local url="${target}${endpoint}"
  local status

  status="$(curl -sS -o /dev/null -m "$curl_timeout" -w "%{http_code}" "$url" || true)"
  printf '%s endpoint=%s status=%s\n' "$(date -Is)" "$endpoint" "$status"
}

if [ "$(rand_percent)" -lt "$idle_chance" ]; then
  echo "$(date -Is) idle=true"
  exit 0
fi

request_count=$((1 + RANDOM % max_requests))

if [ "$(rand_percent)" -lt "$burst_chance" ]; then
  request_count=$((request_count + max_requests + RANDOM % max_requests))
fi

echo "$(date -Is) target=${target} requests=${request_count}"

for _ in $(seq 1 "$request_count"); do
  if [ "$(rand_percent)" -lt "$error_chance" ]; then
    request "/error"
  else
    case $((RANDOM % 10)) in
      0)
        request "/"
        ;;
      1 | 2 | 3 | 4)
        request "/browse"
        ;;
      5 | 6 | 7)
        request "/cart/add"
        ;;
      8)
        request "/checkout"
        ;;
      *)
        request "/work"
        ;;
    esac
  fi

  sleep "0.$((RANDOM % 9 + 1))"
done
