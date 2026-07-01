# Architecture

## Goal

Build a two-VM observability environment that monitors a small MSA-style app from a separate LGTM backend VM.

## Topology

```text
Monitoring VM
  Grafana
  Loki
  Mimir
  Tempo
  Prometheus
  OpenTelemetry Collector
  MinIO
  Node Exporter

App VM
  api-service
  order-service
  payment-service
  Promtail
  Node Exporter
```

## MSA Request Flow

```text
api-service /checkout
  -> order-service /orders
      -> payment-service /payments
```

The three services share one codebase but run as separate containers with different `OTEL_SERVICE_NAME`, `SERVICE_ROLE`, and `PORT` values.

## Logs

1. App services write JSON logs to stdout.
2. Docker stores container logs on the App VM.
3. Promtail tails Docker JSON logs and `/var/log/*.log`.
4. Promtail pushes streams to Loki on the Monitoring VM.
5. Grafana queries Loki with LogQL.
6. JSON logs include `trace_id` and `span_id` so logs can be correlated with Tempo traces.

## Metrics

1. Prometheus runs on the Monitoring VM.
2. It scrapes:
   - Monitoring VM Node Exporter
   - App VM Node Exporter
   - `api-service:8080/metrics`
   - `order-service:8081/metrics`
   - `payment-service:8082/metrics`
   - Grafana, Loki, Mimir, Tempo, and Prometheus itself
3. Prometheus writes samples to Mimir with `remote_write`.
4. Grafana queries Mimir with PromQL.

## Traces

1. App services use OpenTelemetry Flask and Requests instrumentation.
2. Trace context is propagated across `api-service -> order-service -> payment-service`.
3. Services export OTLP traces to the OpenTelemetry Collector on the Monitoring VM.
4. The collector forwards traces to Tempo.
5. Tempo stores trace blocks in MinIO and exposes TraceQL query support to Grafana.

## Security Posture

Only Grafana `3000/tcp` is intended for user-facing access.

VM-to-VM traffic should be limited by private IP security group rules:

- App VM -> Monitoring VM: Loki `3100`, OTel `4317/4318`
- Monitoring VM -> App VM: app service metrics `8080/8081/8082`, Node Exporter `9100`

Mimir, Tempo, Prometheus, MinIO, and Loki should not be publicly exposed.
