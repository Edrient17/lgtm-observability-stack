# 3. 네트워크 및 포트 정책

## 3.1 Security Group Inbound 정책

Inbound는 기본적으로 암시적 거부 정책을 적용하며, 필요한 포트만 허용합니다.
Outbound는 기본적으로 모두 허용 정책을 적용합니다. 실무에서는 필요 시 outbound도 제한합니다.

Monitoring VM inbound:

| Port | Source | 용도 |
| ---: | --- | --- |
| `22/tcp` | 관리자 IP | SSH 접속, 개발 완료 후 제거 |
| `3000/tcp` | 관리자 IP | Grafana Web UI |
| `3100/tcp` | App VM private IP | Alloy -> Loki 로그 전송 |
| `4317/tcp` | App VM private IP | Alloy -> OTel Collector OTLP gRPC trace 전송 |
| `9009/tcp` | App VM private IP | Alloy `prometheus.remote_write` -> Mimir `/api/v1/push` |

App VM inbound:

| Port | Source | 용도 |
| ---: | --- | --- |
| `22/tcp` | 관리자 IP | SSH 접속, 개발 완료 후 제거 |

## 3.2 서비스 포트

| VM | 서비스 | 포트 | 용도 | 외부 공개 여부 |
| --- | --- | ---: | --- | --- |
| Monitoring | Grafana | `3000` | Web UI | 관리자 IP에 공개 |
| Monitoring | Loki | `3100` | 로그 수신 API | App VM private IP만 허용 |
| Monitoring | Mimir | `9009` | metric remote_write `/api/v1/push` 및 query API | App VM private IP만 허용 |
| Monitoring | Tempo | `3200` | trace query API | 외부 공개 X |
| Monitoring | OTel Collector | `4317`, `4318` | trace 수신 | App VM private IP만 허용 |
| Monitoring | Prometheus | `9090` | backend metric scrape 및 alert rule 평가 | 외부 공개 X |
| Monitoring | Alertmanager | `9093` | Slack alert routing | 외부 공개 X |
| Monitoring | MinIO | `9000`, `9001` | object storage | 외부 공개 X |
| App | api-service | `8080` | App 진입점 | 외부 공개 X |
| App | catalog-service | `8081` | 카탈로그 서비스 | 외부 공개 X |
| App | inventory-service | `8082` | 재고 서비스 | 외부 공개 X |
| App | cart-service | `8083` | 장바구니 서비스 | 외부 공개 X |
| App | order-service | `8084` | 주문 서비스 | 외부 공개 X |
| App | payment-service | `8085` | 결제 서비스 | 외부 공개 X |
| App | Node Exporter | `9100` | App VM 시스템 메트릭 | 외부 공개 X |
