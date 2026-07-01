# LGTM Observability Stack

Loki, Grafana, Mimir에 Tempo까지 포함한 단일 VM용 관측성 스택입니다. 요구사항서의 필수 범위인 로그와 메트릭 파이프라인을 충족하면서, OpenTelemetry 기반 trace 수집과 로그-트레이스 연결까지 확장하는 것을 목표로 합니다.

## Architecture

```text
Demo App
  | logs                         | metrics                     | traces / OTLP
  v                              v                           v
Promtail -> Loki          Prometheus -> Mimir        OTel Collector -> Tempo
                              | remote_write                 |
                              v                              |
                            MinIO <--------------------------+
                              ^
                              |
Grafana <- Loki / Mimir / Prometheus / Tempo datasources
```

## Services

| Service | Port | Purpose | Exposure |
| --- | ---: | --- | --- |
| Grafana | 3000 | Web UI, dashboards, datasources | External |
| Loki | 3100 | Log storage/query API | Localhost only |
| Mimir | 9009 | Metrics remote write/query API | Localhost only |
| Tempo | 3200 | Trace query API | Localhost only |
| OTel Collector | 4317, 4318 | OTLP gRPC/HTTP receiver | Localhost only |
| Prometheus | 9090 | Scrape and remote write | Localhost only |
| Node Exporter | 9100 | VM metrics | Localhost only |
| MinIO Console | 9001 | Object storage console | Localhost only |
| Demo App | 8080 | Synthetic app for logs/metrics/traces | Localhost only |

## Prerequisites

- Ubuntu 22.04 LTS
- Docker Engine 26.x or later
- Docker Compose v2 plugin
- 4 GB RAM minimum, 8 GB recommended
- 30 GB SSD minimum, 50 GB recommended

Container image versions are pinned for reproducibility. See `docs/version-policy.md` before upgrading any component.

For single-VM deployment, follow `docs/deployment.md`. For a more production-like
two-VM layout that separates the monitored app from the observability backend,
follow `docs/two-vm-deployment.md`.

## Quick Start

This starts the original single-VM validation stack.

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Grafana:

- URL: `http://<VM_PUBLIC_IP>:3000`
- Default user: `admin`
- Default password: `admin`

MinIO, Prometheus, Loki, Mimir, Tempo, OTel Collector, Node Exporter, and Demo App are bound to `127.0.0.1` by default. On the VM security group, open Grafana `3000/tcp` only unless you have a specific debugging reason.

## Production-Like Two-VM Mode

Use this mode when the Demo App runs on a separate App VM and the LGTM backend
runs on a Monitoring VM.

Monitoring VM:

```bash
cp .env.monitoring.example .env
# edit APP_VM_PRIVATE_IP and passwords
docker compose up -d
```

App VM:

```bash
cp .env.app.example .env
# edit MONITORING_VM_PRIVATE_IP and APP_HOST_LABEL
docker compose up -d --build
```

See `docs/two-vm-deployment.md` for the full network flow and validation steps.

## Generate Sample Data

```bash
bash ./scripts/generate-load.sh
```

Then open Grafana and check:

- `LGTM Observability / Logs Overview`
- `LGTM Observability / VM Metrics`
- `LGTM Observability / Traces Overview`

## Validation

```bash
bash ./scripts/healthcheck.sh
```

Manual queries:

```promql
up
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
rate(demo_app_requests_total[5m])
```

```logql
{job="docker"} |= "demo-app"
{job="docker"} |= "intentional demo error"
```

```traceql
{ resource.service.name = "demo-app" }
```

## Key Files

| Path | Description |
| --- | --- |
| `docker-compose.yml` | Single-command runtime definition |
| `docker-compose.monitoring.yml` | Monitoring VM runtime definition |
| `docker-compose.app.yml` | App VM runtime definition |
| `configs/loki/loki-config.yaml` | Loki filesystem storage and retention |
| `configs/promtail/promtail-config.yaml` | System and Docker log scraping |
| `configs/promtail/promtail-app-config.yaml` | App VM log scraping and Loki push config |
| `configs/prometheus/prometheus.yml` | Scrape jobs and Mimir remote write |
| `configs/prometheus/prometheus.two-vm.yml` | Two-VM scrape jobs for Monitoring VM and App VM |
| `configs/prometheus/rules/node-alerts.yml` | CPU, disk, and pipeline alert rules |
| `configs/mimir/mimir-config.yaml` | Mimir monolithic mode with MinIO object storage |
| `configs/tempo/tempo-config.yaml` | Tempo OTLP receiver and MinIO trace storage |
| `configs/otel-collector/otel-collector-config.yaml` | OTLP receiver to Tempo exporter pipeline |
| `grafana/provisioning` | Datasource and dashboard provisioning |
| `grafana/dashboards` | Exportable dashboard JSON files |
| `demo-app` | Instrumented sample app for demos |

## Alert Rules

Prometheus rules are stored in `configs/prometheus/rules/node-alerts.yml`.

- `HighCpuUsage`: CPU usage above 80% for 5 minutes
- `HighDiskUsage`: disk usage above 85% for 5 minutes
- `LokiTargetDown`: Loki scrape target down for 2 minutes
- `TempoTargetDown`: Tempo scrape target down for 2 minutes

Contact point delivery is intentionally left for the deployment environment because email and Slack webhook secrets should not be committed. During final validation, configure a Grafana contact point or Prometheus Alertmanager integration and record the send-test screenshot in the report.

## Troubleshooting Log

See `docs/troubleshooting.md` for the project troubleshooting record. Add real incidents as they happen during VM deployment so the final report has evidence instead of reconstructed notes.
