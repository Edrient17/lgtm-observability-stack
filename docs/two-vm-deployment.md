# Two-VM Deployment

This deployment mode separates the observability backend from the monitored application VM.

## Topology

```text
User
  |
  | http://monitoring-vm:3000
  v
Monitoring VM
  - Grafana
  - Loki
  - Mimir
  - Tempo
  - Prometheus
  - MinIO
  - OpenTelemetry Collector
  - Node Exporter for monitoring VM metrics

App VM
  - Demo App
  - Node Exporter for app VM metrics
  - Promtail for app VM logs
```

## Network Flow

```text
App VM -> Monitoring VM
  - 3100/tcp: Promtail pushes logs to Loki
  - 4317/tcp: Demo App exports OTLP traces to OTel Collector
  - 4318/tcp: Optional OTLP HTTP receiver

Monitoring VM -> App VM
  - 8080/tcp: Prometheus scrapes Demo App metrics
  - 9100/tcp: Prometheus scrapes Node Exporter metrics

User -> Monitoring VM
  - 3000/tcp: Grafana Web UI
```

Use private IPs for all VM-to-VM traffic when the cloud network supports it.

## Files

| File | VM | Purpose |
| --- | --- | --- |
| `.env.monitoring.example` | Monitoring VM | Environment template for backend stack |
| `docker-compose.monitoring.yml` | Monitoring VM | Grafana, Loki, Mimir, Tempo, Prometheus, MinIO |
| `configs/prometheus/prometheus.two-vm.yml` | Monitoring VM | Scrapes both Monitoring VM and App VM targets |
| `.env.app.example` | App VM | Environment template for monitored app stack |
| `docker-compose.app.yml` | App VM | Demo App, Node Exporter, Promtail |
| `configs/promtail/promtail-app-config.yaml` | App VM | Pushes App VM logs to Monitoring VM Loki |

The original `docker-compose.yml` remains available for single-VM local validation.

## Monitoring VM Setup

Copy the repository to the Monitoring VM, then create the environment file:

```bash
cp .env.monitoring.example .env.monitoring
```

Edit `.env.monitoring`:

```bash
APP_VM_PRIVATE_IP=<app-vm-private-ip>
GRAFANA_ADMIN_PASSWORD=<strong-password>
MINIO_ROOT_PASSWORD=<strong-password>
```

Start the Monitoring VM stack:

```bash
make monitoring-up
make monitoring-ps
```

Grafana should be available at:

```text
http://<monitoring-vm-public-ip>:3000
```

## App VM Setup

Copy the repository to the App VM, then create the environment file:

```bash
cp .env.app.example .env.app
```

Edit `.env.app`:

```bash
MONITORING_VM_PRIVATE_IP=<monitoring-vm-private-ip>
APP_HOST_LABEL=app-vm
```

Start the App VM stack:

```bash
make app-up
make app-ps
```

## Validation

From the Monitoring VM, check whether Prometheus can reach the App VM:

```bash
curl http://<app-vm-private-ip>:9100/metrics
curl http://<app-vm-private-ip>:8080/metrics
```

From the App VM, check whether Loki and the OTel Collector are reachable:

```bash
curl http://<monitoring-vm-private-ip>:3100/ready
curl http://<monitoring-vm-private-ip>:4318/
```

Generate sample app traffic on the App VM:

```bash
curl http://localhost:8080/
curl http://localhost:8080/work
curl http://localhost:8080/error
```

Then check Grafana:

- Metrics: `up`, `rate(demo_app_requests_total[5m])`
- VM metrics: CPU, disk, filesystem, and network panels in the VM Metrics dashboard
- Logs: `{job="docker", host="app-vm"}`
- Traces: `{ resource.service.name = "demo-app" }`

## Security Group Checklist

Monitoring VM inbound:

- `3000/tcp` from your IP
- `3100/tcp` from App VM private IP
- `4317/tcp` from App VM private IP
- `4318/tcp` from App VM private IP if OTLP HTTP is needed
- `22/tcp` from your IP

App VM inbound:

- `8080/tcp` from Monitoring VM private IP
- `9100/tcp` from Monitoring VM private IP
- `22/tcp` from your IP

Keep Mimir, Tempo query API, Prometheus, and MinIO console private unless a debugging session specifically requires temporary access.
