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
  catalog-service
  inventory-service
  cart-service
  order-service
  payment-service
  Promtail
  Node Exporter
```

## MSA Request Flow

```text
/browse
  api-service
    -> catalog-service /catalog
        -> inventory-service /inventory/check

/cart/add
  api-service
    -> cart-service /cart/add
        -> catalog-service /catalog/item
        -> inventory-service /inventory/reserve

/checkout
  api-service
    -> cart-service /cart/items
    -> order-service /orders
        -> inventory-service /inventory/reserve
        -> payment-service /payments
```

All six services share one codebase but run as separate containers with different `OTEL_SERVICE_NAME`, `SERVICE_ROLE`, and `PORT` values.

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
   - `catalog-service:8081/metrics`
   - `inventory-service:8082/metrics`
   - `cart-service:8083/metrics`
   - `order-service:8084/metrics`
   - `payment-service:8085/metrics`
   - Grafana, Loki, Mimir, Tempo, and Prometheus itself
3. Prometheus writes samples to Mimir with `remote_write`.
4. Grafana queries Mimir with PromQL.

## Traces

1. App services use OpenTelemetry Flask and Requests instrumentation.
2. Trace context is propagated across HTTP calls between MSA services.
3. Services export OTLP traces to the OpenTelemetry Collector on the Monitoring VM over gRPC `4317/tcp`.
4. The collector forwards traces to Tempo.
5. Tempo stores trace blocks in MinIO and exposes TraceQL query support to Grafana.

## Security Posture

Only Grafana `3000/tcp` is intended for user-facing access.

VM-to-VM traffic should be limited by private IP security group rules:

- App VM -> Monitoring VM: Loki `3100`, OTel `4317/4318`
- Monitoring VM -> App VM: app service metrics `8080-8085`, Node Exporter `9100`

Mimir, Tempo, Prometheus, MinIO, and Loki should not be publicly exposed.
