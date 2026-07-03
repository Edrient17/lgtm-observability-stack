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
- [ ] `docker compose ps` shows `api-service`, `catalog-service`, `inventory-service`, `cart-service`, `order-service`, `payment-service`, `promtail`, and `node-exporter` running.

## Connectivity

From the Monitoring VM:

- [ ] `curl http://<app-vm-private-ip>:8080/metrics` succeeds.
- [ ] `curl http://<app-vm-private-ip>:8081/metrics` succeeds.
- [ ] `curl http://<app-vm-private-ip>:8082/metrics` succeeds.
- [ ] `curl http://<app-vm-private-ip>:8083/metrics` succeeds.
- [ ] `curl http://<app-vm-private-ip>:8084/metrics` succeeds.
- [ ] `curl http://<app-vm-private-ip>:8085/metrics` succeeds.
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
- [ ] `sum by (service) (rate(demo_app_requests_total[5m]))` returns traffic for all active MSA services.
- [ ] VM Metrics dashboard shows CPU, memory, disk, and network panels.

## Traces

- [ ] Tempo datasource is healthy in Grafana.
- [ ] `curl http://localhost:8080/browse` on the App VM generates traces.
- [ ] `curl http://localhost:8080/cart/add` on the App VM generates traces.
- [ ] `curl http://localhost:8080/checkout` on the App VM generates traces.
- [ ] `{ resource.service.name = "api-service" }` returns traces in Grafana Explore.
- [ ] Browse traces show `api-service -> catalog-service -> inventory-service`.
- [ ] Cart traces show `api-service -> cart-service -> catalog-service/inventory-service`.
- [ ] Checkout traces show `api-service -> cart-service/order-service -> inventory-service/payment-service`.

## Long-Running Observation

- [ ] `scripts/random-demo-traffic.sh` runs manually on the App VM.
- [ ] Cron is registered for multi-day traffic generation.
- [ ] `logs/random-demo-traffic.log` shows `/browse`, `/cart/add`, `/checkout`, `/work`, and `/error` requests.

## Alerts

- [ ] Prometheus loads `configs/prometheus/rules/node-alerts.yml`.
- [ ] Grafana shows the `Alerts Overview` dashboard.
- [ ] `MsaServiceDown` fires when one App VM service is stopped for about 1 minute.
- [ ] `MsaHighErrorRate` fires when repeated `/error` requests are generated.
- [ ] `AppVmNodeExporterDown` fires when App VM Node Exporter is stopped for about 1 minute.
- [ ] Alert recovery is confirmed after each stopped container is started again.
