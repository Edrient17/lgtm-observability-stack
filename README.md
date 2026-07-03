# LGTM Observability Stack

Two-VM LGTM observability stack for a small MSA-style demo workload.

The project is fixed to a two-VM topology:

![LGTM two-VM MSA architecture](docs/lgtm-architecture.jpg)

## Data Flow

- Logs: App VM Docker logs -> Promtail -> Loki -> Grafana
- Metrics: Prometheus pulls App VM services and Node Exporter -> Mimir -> Grafana
- Traces: MSA services -> OTel Collector over OTLP gRPC -> Tempo -> Grafana
- Storage: Mimir and Tempo store blocks in MinIO

## Demo Request Flows

```text
/browse
  api-service -> catalog-service -> inventory-service

/cart/add
  api-service -> cart-service -> catalog-service
                              -> inventory-service

/checkout
  api-service -> cart-service
              -> order-service -> inventory-service
                               -> payment-service
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
| App | api-service | 8080 | Public demo entrypoint |
| App | catalog-service | 8081 | Product catalog |
| App | inventory-service | 8082 | Stock checks and reservation |
| App | cart-service | 8083 | Cart workflow |
| App | order-service | 8084 | Checkout orchestration |
| App | payment-service | 8085 | Payment authorization |
| App | Node Exporter | 9100 | App VM system metrics |

## Security Group Inbound Allowed

Monitoring VM inbound:

| Port | Source | Purpose |
| ---: | --- | --- |
| 22/tcp | Your IP | SSH access |
| 3000/tcp | Your IP | Grafana Web UI |
| 3100/tcp | App VM private IP | Promtail -> Loki log push |
| 4317/tcp | App VM private IP | MSA services -> OTel Collector OTLP gRPC |

App VM inbound:

| Port | Source | Purpose |
| ---: | --- | --- |
| 22/tcp | Your IP | SSH access |
| 8080/tcp | Monitoring VM private IP | API Service metrics scrape |
| 8081/tcp | Monitoring VM private IP | Catalog Service metrics scrape |
| 8082/tcp | Monitoring VM private IP | Inventory Service metrics scrape |
| 8083/tcp | Monitoring VM private IP | Cart Service metrics scrape |
| 8084/tcp | Monitoring VM private IP | Order Service metrics scrape |
| 8085/tcp | Monitoring VM private IP | Payment Service metrics scrape |
| 9100/tcp | Monitoring VM private IP | Node Exporter metrics scrape |

## Generate Traffic

Short manual test on the App VM:

```bash
curl http://localhost:8080/browse
curl http://localhost:8080/cart/add
curl http://localhost:8080/checkout
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
{ resource.service.name = "api-service" || resource.service.name = "cart-service" || resource.service.name = "order-service" }
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
| `msa-demo` | Shared image used by all six MSA demo services |
| `scripts/random-demo-traffic.sh` | Random traffic generator for long-running observation |
| `scripts/fault-injection.sh` | Controlled failure and recovery helper for alert testing |

## Documentation

- `docs/architecture.md`
- `docs/two-vm-deployment.md`
- `docs/validation.md`
- `docs/alert-scenarios.md`
- `docs/troubleshooting.md`
- `docs/version-policy.md`
