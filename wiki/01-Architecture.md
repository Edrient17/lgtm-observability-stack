# 1. 프로젝트 아키텍처

![Architecture Diagram](https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/architecture_diagram.jpg)

Docker Compose로 구성한 Monitoring VM 서비스는 다음과 같습니다.

| 서비스 | 컨테이너명 | 역할 |
| --- | --- | --- |
| `grafana` | `grafana` | LGTM 통합 대시보드 및 Explore Web UI |
| `loki` | `loki` | App VM K3S Pod 로그 저장 및 LogQL 조회 |
| `mimir` | `mimir` | App/Monitoring VM 메트릭 저장, PromQL 조회, Mimir Ruler 기반 App/MSA 알람 평가 |
| `tempo` | `tempo` | MSA trace 저장 및 TraceQL 조회 |
| `prometheus` | `prometheus` | Monitoring VM backend 메트릭 scrape 및 backend alert rule 평가 |
| `alertmanager` | `alertmanager` | Prometheus와 Mimir Ruler alert를 수신하여 Slack으로 전송 |
| `otel-collector` | `otel-collector` | App VM Alloy가 보낸 trace를 Tempo로 전달 |
| `minio` | `minio` | Mimir, Tempo block 저장용 S3 호환 object storage |
| `minio-init` | `minio-init` | Mimir, Tempo용 MinIO bucket 초기 생성 |
| `mimir-rules-init` | `mimir-rules-init` | `configs/mimir/rules/app-alerts.yml`을 Mimir Ruler API에 등록 |
| `node-exporter` | `node-exporter-monitoring` | Monitoring VM 시스템 메트릭 노출 |

K3S로 구성한 App VM 리소스는 다음과 같습니다.

| 리소스 | 종류 | 역할 |
| --- | --- | --- |
| `api-service` | Deployment, Service | 외부 요청의 진입점 역할을 하며 `/browse`, `/cart/add`, `/checkout`, `/work` 엔드포인트 제공 |
| `catalog-service` | Deployment, Service | 상품 카탈로그 조회 및 catalog 관련 내부 API 제공 |
| `inventory-service` | Deployment, Service | 재고 조회 및 재고 예약 처리 |
| `cart-service` | Deployment, Service | 장바구니 담기 및 장바구니 항목 조회 처리 |
| `order-service` | Deployment, Service | 주문 생성 처리 및 inventory/payment downstream 호출 |
| `payment-service` | Deployment, Service | 결제 승인 처리 |
| `alloy` | DaemonSet, Service | K3S Pod 로그 수집, MSA/Node Exporter 메트릭 scrape, OTLP trace 수신 및 Monitoring VM으로 전달 |
| `node-exporter` | DaemonSet, Service | App VM 시스템 메트릭 노출 |
| `msa-demo-config` | ConfigMap | Monitoring VM private IP, Loki/Mimir/OTel Collector endpoint, log/label 설정 |

## 1.1 Telemetry Flow

| 구분 | 흐름 |
| --- | --- |
| Logs | K3S Pod stdout/stderr -> `/var/log/containers/*.log` -> Alloy -> Loki -> Grafana |
| Metrics (App VM) | App VM의 Alloy가 App `/metrics`와 Node Exporter를 scrape하고, Prometheus remote_write 방식으로 Mimir `/api/v1/push`에 전송 -> Grafana |
| Metrics (Monitoring VM) | Prometheus가 Grafana, Loki, Mimir, Tempo, Alertmanager, Monitoring VM Node Exporter `/metrics`를 scrape -> Mimir remote_write -> Grafana |
| Traces | App 서비스 -> OTLP gRPC -> Alloy -> OTel Collector -> Tempo -> Grafana |
| Backend Alerts | Prometheus -> Alertmanager -> Slack |
| App/MSA Alerts | Alloy -> Mimir -> Mimir Ruler -> Alertmanager -> Slack |
| Storage | Mimir, Tempo -> MinIO object storage |

자세한 수집 경로는 [`docs/set-up-details.md`](https://github.com/Edrient17/lgtm-observability-stack/blob/main/docs/set-up-details.md)를 참고합니다.

## 1.2 Application Request Flow

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

/work
  api-service internal work simulation
```
