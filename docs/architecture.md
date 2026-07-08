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
  Alloy
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
2. K3S/containerd는 Pod stdout/stderr 로그를 App VM에 저장한다.
3. Alloy는 K3S pod 로그 파일을 tail 하고 JSON 필드를 추출한다.
4. Alloy는 로그 stream을 Monitoring VM의 Loki로 push 한다.
5. Grafana는 LogQL로 Loki를 조회한다.
6. JSON 로그에는 `trace_id`, `span_id`가 포함되어 Tempo trace와 연계할 수 있다.

## Metrics

1. App VM의 Alloy는 K3S 내부 Service DNS를 통해 demo MSA `/metrics`와 App VM Node Exporter를 scrape 한다.
2. Alloy는 App VM metric sample을 Monitoring VM의 Mimir로 `remote_write` 한다.
3. Monitoring VM의 Prometheus는 Grafana, Loki, Mimir, Tempo, Prometheus, Monitoring VM Node Exporter 같은 backend metric만 scrape 한다.
4. Prometheus도 backend metric sample을 Mimir로 `remote_write` 한다.
5. Grafana는 PromQL로 Mimir를 조회한다.

## Alerts

1. Monitoring backend alert는 Prometheus가 직접 scrape한 backend metric으로 평가한다.
2. App VM과 MSA alert는 Mimir Ruler가 Mimir에 저장된 App metric으로 평가한다.
3. Prometheus와 Mimir Ruler는 firing alert를 Alertmanager로 전달한다.
4. Alertmanager는 Slack Incoming Webhook으로 firing/resolved 알림을 전송한다.

## Traces

1. App 서비스는 OpenTelemetry Flask/Requests instrumentation을 사용한다.
2. Trace context는 MSA 서비스 간 HTTP 호출을 따라 전파된다.
3. 각 서비스는 OTLP trace를 App VM의 Alloy Service로 gRPC `4317/tcp`를 통해 전송한다.
4. Alloy는 trace를 Monitoring VM의 OpenTelemetry Collector로 전달한다.
5. Collector는 trace를 Tempo로 전달한다.
6. Tempo는 trace block을 MinIO에 저장하고, Grafana에서 TraceQL로 조회할 수 있게 한다.

## Security Posture

사용자에게 직접 노출되는 포트는 Grafana `3000/tcp`만 의도한다.

VM 간 통신은 private IP 기반 보안그룹 규칙으로 제한한다.

- App VM -> Monitoring VM: Loki `3100`, OTel Collector `4317`, Mimir `9009`

Mimir, Tempo, Prometheus, MinIO, Loki는 외부에 공개하지 않는 것을 기준으로 한다.
