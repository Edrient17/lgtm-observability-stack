# Troubleshooting

Use this file as a live build log. The final report should include real symptoms, root causes, fixes, and outcomes from the two-VM deployment.

## Case 1: Monitoring VM Node Exporter Port Conflict

- Symptom:
  - `docker compose up -d` fails with `Bind for 127.0.0.1:9100 failed: port is already allocated`.
- Root cause:
  - An older Docker container still had a `node-exporter` instance publishing `127.0.0.1:9100`.
- Fix:
  - Stop the older stack or remove the old container.
  - Re-run the Monitoring VM stack.
- Useful commands:
  - `sudo ss -ltnp | grep ':9100'`
  - `docker ps | grep node`
  - `docker stop <old-node-exporter-container>`
  - `docker rm <old-node-exporter-container>`

## Case 2: Demo Service Exits With Missing `pkg_resources`

- Symptom:
  - App VM service exits immediately with `ModuleNotFoundError: No module named 'pkg_resources'`.
- Root cause:
  - `python:3.12-slim` does not include `setuptools` by default, while OpenTelemetry instrumentation imports `pkg_resources`.
- Fix:
  - Add `setuptools` to `msa-demo/requirements.txt`.
  - Rebuild the App VM services with `docker compose up -d --build`.

## Case 3: App VM `8080` Connection Refused From Monitoring VM

- Symptom:
  - `curl http://<app-vm-private-ip>:8080/metrics` returns `Connection refused`, while `9100/metrics` works.
- Root cause:
  - The app container was not running or exited after startup.
- Fix:
  - Check `docker compose ps -a`.
  - Check `docker compose logs api-service`.
  - Rebuild and restart the App VM stack.

## Case 4: Loki `/ready` Temporarily Reports Ingester Not Ready

- Symptom:
  - `curl http://<monitoring-vm-private-ip>:3100/ready` returns `Ingester not ready: waiting for 15s after being ready`.
- Root cause:
  - Loki has started but is still passing its startup readiness delay.
- Fix:
  - Wait briefly and retry.
  - If it persists, inspect `docker compose logs loki`.

## Case 5: OTel Collector `4318/` Returns 404

- Symptom:
  - `curl http://<monitoring-vm-private-ip>:4318/` returns `404 page not found`.
- Root cause:
  - OTLP HTTP receiver is reachable, but `/` is not a data ingestion path.
- Fix:
  - Treat this as a connectivity success.
  - Validate traces by generating `/checkout` traffic and checking Tempo.

## Case 6: Dashboard Has No Data

- Symptom:
  - Grafana dashboard loads but panels show `No data`.
- Root cause:
  - App VM traffic has not been generated, Prometheus targets are down, or Mimir remote write is not ready.
- Fix:
  - Run `./scripts/random-demo-traffic.sh` on the App VM.
  - Query `up` and `sum by (service) (rate(demo_app_requests_total[5m]))`.
  - Check Prometheus targets from Grafana Explore or Prometheus UI.
