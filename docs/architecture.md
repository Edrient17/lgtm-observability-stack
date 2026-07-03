# Architecture

## Goal

별도 LGTM backend VM에서 소규모 MSA 스타일 App VM을 관측하는 2-VM observability 환경을 구성한다.

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

6개 서비스는 하나의 코드베이스를 공유하지만, 컨테이너별로 `OTEL_SERVICE_NAME`, `SERVICE_ROLE`, `PORT` 값을 다르게 받아 서로 다른 서비스처럼 실행된다.

## Logs

1. App 서비스는 JSON 로그를 stdout으로 출력한다.
2. Docker는 컨테이너 로그를 App VM에 저장한다.
3. Promtail은 Docker JSON 로그와 `/var/log/*.log`를 tail 한다.
4. Promtail은 로그 stream을 Monitoring VM의 Loki로 push 한다.
5. Grafana는 LogQL로 Loki를 조회한다.
6. JSON 로그에는 `trace_id`, `span_id`가 포함되어 Tempo trace와 연계할 수 있다.

## Metrics

1. Prometheus는 Monitoring VM에서 실행된다.
2. Prometheus는 다음 대상을 scrape 한다.
   - Monitoring VM Node Exporter
   - App VM Node Exporter
   - `api-service:8080/metrics`
   - `catalog-service:8081/metrics`
   - `inventory-service:8082/metrics`
   - `cart-service:8083/metrics`
   - `order-service:8084/metrics`
   - `payment-service:8085/metrics`
   - Grafana, Loki, Mimir, Tempo, Prometheus 자체 메트릭
3. Prometheus는 `remote_write`로 샘플을 Mimir에 기록한다.
4. Grafana는 PromQL로 Mimir를 조회한다.

## Traces

1. App 서비스는 OpenTelemetry Flask/Requests instrumentation을 사용한다.
2. Trace context는 MSA 서비스 간 HTTP 호출을 따라 전파된다.
3. 각 서비스는 OTLP trace를 Monitoring VM의 OpenTelemetry Collector로 gRPC `4317/tcp`를 통해 전송한다.
4. Collector는 trace를 Tempo로 전달한다.
5. Tempo는 trace block을 MinIO에 저장하고, Grafana에서 TraceQL로 조회할 수 있게 한다.

## Security Posture

사용자에게 직접 노출되는 포트는 Grafana `3000/tcp`만 의도한다.

VM 간 통신은 private IP 기반 보안그룹 규칙으로 제한한다.

- App VM -> Monitoring VM: Loki `3100`, OTel `4317`
- Monitoring VM -> App VM: app service metrics `8080-8085`, Node Exporter `9100`

Mimir, Tempo, Prometheus, MinIO, Loki는 외부에 공개하지 않는 것을 기준으로 한다.
