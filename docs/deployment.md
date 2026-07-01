# Deployment Guide

This guide targets the project VM: Ubuntu 22.04 LTS with Docker Engine 26.x or later and Docker Compose v2.

## 1. Prepare the VM

Install Docker and clone the repository on the VM.

```bash
git clone <REPOSITORY_URL>
cd lgtm-observability-stack
cp .env.single-vm.example .env
```

Open only Grafana externally:

| Port | Scope |
| ---: | --- |
| `3000/tcp` | External access allowed |
| `3100`, `3200`, `4317`, `4318`, `9001`, `9009`, `9090`, `9100` | Keep closed externally |

The compose file binds non-Grafana service ports to `127.0.0.1`, but the cloud security group should still keep those ports closed.

## 2. Start the Stack

```bash
docker compose up -d --build
docker compose ps
```

Expected long-running services:

- `grafana`
- `loki`
- `promtail`
- `prometheus`
- `mimir`
- `node-exporter`
- `minio`
- `tempo`
- `otel-collector`
- `demo-app`

`minio-init` should show as completed successfully.

If Docker reports a permission error, grant the VM user Docker group access and refresh the shell session:

```bash
sudo usermod -aG docker $USER
newgrp docker
docker info
```

If `newgrp docker` does not refresh the permission cleanly, log out of SSH and log back in.

## 3. Generate Demo Traffic

```bash
bash scripts/generate-load.sh
```

This produces:

- demo app HTTP metrics
- JSON logs with `trace_id`
- OTLP traces through the OpenTelemetry Collector

## 4. Validate Health

```bash
bash scripts/healthcheck.sh
```

Then open Grafana:

```text
http://<VM_PUBLIC_IP>:3000
```

Default credentials:

```text
admin / admin
```

## 5. Capture Evidence

For weekly reporting, capture screenshots of:

- `docker compose ps`
- Grafana login and home page
- Loki datasource health
- Mimir datasource health
- Tempo datasource health
- `Logs Overview` dashboard
- `VM Metrics` dashboard
- `Traces Overview` dashboard
- alert rule list and contact point send test
