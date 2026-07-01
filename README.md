# LGTM Observability Stack

Two-VM LGTM observability stack for a small MSA-style demo workload.

The project is now fixed to this topology:

```text
Monitoring VM
  - Grafana
  - Loki
  - Mimir
  - Tempo
  - Prometheus
  - OpenTelemetry Collector
  - MinIO
  - Node Exporter

App VM
  - api-service
  - order-service
  - payment-service
  - Promtail
  - Node Exporter
```

## Data Flow

```text
User / Traffic
  -> api-service :8080
      -> order-service :8081
          -> payment-service :8082

Logs:
  App VM Docker logs -> Promtail -> Loki -> Grafana

Metrics:
  Prometheus -> App VM services / Node Exporter -> Mimir -> Grafana

Traces:
  api-service/order-service/payment-service -> OTel Collector -> Tempo -> Grafana

Storage:
  Mimir + Tempo -> MinIO
```

## Deployment

Monitoring VM:

```bash
cp .env.monitoring.example .env
# edit APP_VM_PRIVATE_IP, GRAFANA_ADMIN_PASSWORD, MINIO_ROOT_PASSWORD
docker compose up -d
docker compose ps
```

App VM:

```bash
cp .env.app.example .env
# edit MONITORING_VM_PRIVATE_IP and APP_HOST_LABEL
docker compose up -d --build
docker compose ps
```

See `docs/two-vm-deployment.md` for setup, security group rules, and validation steps.

## Key Services

| VM | Service | Port | Purpose |
| --- | --- | ---: | --- |
| Monitoring | Grafana | 3000 | External UI |
| Monitoring | Loki | 3100 | Log ingestion/query |
| Monitoring | Mimir | 9009 | Metrics storage/query |
| Monitoring | Tempo | 3200 | Trace query |
| Monitoring | OTel Collector | 4317, 4318 | Trace ingestion |
| Monitoring | Prometheus | 9090 | Scrape and remote write |
| Monitoring | MinIO | 9000, 9001 | Object storage |
| App | api-service | 8080 | MSA entrypoint |
| App | order-service | 8081 | Downstream order workflow |
| App | payment-service | 8082 | Downstream payment workflow |
| App | Node Exporter | 9100 | App VM system metrics |

Only Grafana should be exposed to the user's public IP. VM-to-VM traffic should use private IP security group rules.

## Generate Traffic

Short manual test on the App VM:

```bash
curl http://localhost:8080/checkout
curl http://localhost:8080/work
curl http://localhost:8080/error
```

Multi-day observation on the App VM:

```bash
chmod +x ./scripts/random-demo-traffic.sh
mkdir -p ./logs
./scripts/random-demo-traffic.sh
```

Cron example:

```cron
* * * * * cd /home/ubuntu/lgtm-observability-stack && DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh >> /home/ubuntu/lgtm-observability-stack/logs/random-demo-traffic.log 2>&1
```

## Useful Queries

PromQL:

```promql
up
sum by (service) (rate(demo_app_requests_total[5m]))
histogram_quantile(0.95, sum by (le, service) (rate(demo_app_request_duration_seconds_bucket[5m])))
```

LogQL:

```logql
{job="docker", host="app-vm"}
{job="docker", host="app-vm"} |= "payment authorization failed"
```

TraceQL:

```traceql
{ resource.service.name = "api-service" }
```

## Key Files

| Path | Description |
| --- | --- |
| `docker-compose.monitoring.yml` | Monitoring VM runtime definition |
| `docker-compose.app.yml` | App VM runtime definition |
| `.env.monitoring.example` | Monitoring VM environment template |
| `.env.app.example` | App VM environment template |
| `configs/prometheus/prometheus.two-vm.yml` | Prometheus scrape config for both VMs |
| `configs/promtail/promtail-app-config.yaml` | App VM Promtail config |
| `msa-demo` | Shared image used by api/order/payment services |
| `scripts/random-demo-traffic.sh` | Random traffic generator for long-running observation |

## Documentation

- `docs/architecture.md`
- `docs/two-vm-deployment.md`
- `docs/validation.md`
- `docs/troubleshooting.md`
- `docs/version-policy.md`
