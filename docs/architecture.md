# Architecture

## Goal

Build a single-VM observability stack that collects logs, metrics, and traces, stores them durably, and exposes them through Grafana dashboards.

## Data Flows

### Logs

1. Applications and Docker containers write logs to stdout or host log files.
2. Promtail tails `/var/log/*.log` and Docker JSON log files.
3. Promtail pushes log streams to Loki.
4. Grafana queries Loki with LogQL.
5. JSON logs containing `trace_id` link back to Tempo traces through Grafana derived fields.

### Metrics

1. Prometheus scrapes itself, Node Exporter, Grafana, Loki, Mimir, Tempo, and the demo app.
2. Prometheus writes samples to Mimir through `remote_write`.
3. Mimir stores blocks in MinIO.
4. Grafana queries Mimir with PromQL.

### Traces

1. The demo app exports OTLP traces to the OpenTelemetry Collector.
2. The collector batches traces and exports them to Tempo.
3. Tempo stores traces in MinIO.
4. Tempo metrics-generator writes span metrics and service graph metrics to Mimir.
5. Grafana queries Tempo with TraceQL and correlates traces with logs and metrics.

## Security Posture

Only Grafana is intended for external access. All other ports are bound to `127.0.0.1` in `docker-compose.yml`, and services communicate through the private Docker bridge network named `observability`.

