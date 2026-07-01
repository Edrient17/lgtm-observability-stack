# Validation Checklist

## Monitoring VM

- [ ] `.env` was created from `.env.monitoring.example`.
- [ ] `APP_VM_PRIVATE_IP` points to the App VM private IP.
- [ ] `docker compose up -d` completes.
- [ ] `docker compose ps` shows Grafana, Loki, Mimir, Tempo, Prometheus, OTel Collector, MinIO, and Node Exporter running.
- [ ] Grafana is reachable on `http://<monitoring-vm-public-ip>:3000`.

## App VM

- [ ] `.env` was created from `.env.app.example`.
- [ ] `MONITORING_VM_PRIVATE_IP` points to the Monitoring VM private IP.
- [ ] `docker compose up -d --build` completes.
- [ ] `docker compose ps` shows `api-service`, `order-service`, `payment-service`, `promtail`, and `node-exporter` running.

## Connectivity

From the Monitoring VM:

- [ ] `curl http://<app-vm-private-ip>:8080/metrics` succeeds.
- [ ] `curl http://<app-vm-private-ip>:8081/metrics` succeeds.
- [ ] `curl http://<app-vm-private-ip>:8082/metrics` succeeds.
- [ ] `curl http://<app-vm-private-ip>:9100/metrics` succeeds.

From the App VM:

- [ ] `curl http://<monitoring-vm-private-ip>:3100/ready` eventually returns `ready`.
- [ ] `curl http://<monitoring-vm-private-ip>:4318/` returns an HTTP response such as `404 page not found`.

## Logs

- [ ] Loki datasource is healthy in Grafana.
- [ ] `{job="docker", host="app-vm"}` returns app container logs.
- [ ] Logs include `service`, `trace_id`, and `span_id` fields.
- [ ] Error logs from `payment-service` can be found after `/checkout` traffic.

## Metrics

- [ ] Mimir datasource is healthy in Grafana.
- [ ] `up` shows both Monitoring VM and App VM targets.
- [ ] `sum by (service) (rate(demo_app_requests_total[5m]))` returns api/order/payment service traffic.
- [ ] VM Metrics dashboard shows CPU, memory, disk, and network panels.

## Traces

- [ ] Tempo datasource is healthy in Grafana.
- [ ] `curl http://localhost:8080/checkout` on the App VM generates traces.
- [ ] `{ resource.service.name = "api-service" }` returns traces in Grafana Explore.
- [ ] A checkout trace shows `api-service -> order-service -> payment-service`.

## Long-Running Observation

- [ ] `scripts/random-demo-traffic.sh` runs manually on the App VM.
- [ ] Cron is registered for multi-day traffic generation.
- [ ] `logs/random-demo-traffic.log` shows `/checkout`, `/work`, and `/error` requests.
