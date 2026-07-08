# LGTM Observability Stack

소규모 MSA 스타일 데모 워크로드를 관측하기 위한 2-VM 기반 LGTM observability stack

![LGTM two-VM MSA architecture](docs/lgtm-architecture.jpg)

## Data Flow

- Logs: App VM K3S pod logs -> Alloy -> Loki -> Grafana 순서로 전달
- Metrics: App VM Alloy가 MSA 서비스와 Node Exporter를 scrape하고 Mimir로 remote_write
- Alerts: Prometheus는 Monitoring backend alert를 평가하고, Mimir Ruler는 App/MSA alert를 평가한 뒤 Alertmanager로 전달
- Traces: MSA 서비스가 App VM Alloy로 trace를 보내고, Alloy가 Monitoring VM OTel Collector를 거쳐 Tempo로 전달
- Storage: Mimir와 Tempo는 block 데이터를 MinIO에 저장

## Demo Request Flows

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
```

## Deployment

Monitoring VM:

```bash
cp .env.example .env
# edit GRAFANA_ADMIN_PASSWORD, MINIO_ROOT_PASSWORD
docker compose up -d
docker compose ps
```

기존 `.env`를 재사용한다면 `COMPOSE_FILE=docker-compose.monitoring.yml` 줄은 삭제한다.

App VM:

```bash
cp k3s/app-vm/configmap.example.yaml k3s/app-vm/configmap.yaml
# edit k3s/app-vm/configmap.yaml monitoring VM private IP
./scripts/k3s-load-demo-image.sh
kubectl apply -k ./k3s/app-vm
kubectl -n msa-demo get pods,svc,daemonset
```

자세한 절차는 `docs/app-vm-k3s.md`를 참고

설치 절차, 보안그룹 규칙, 검증 단계는 `docs/two-vm-deployment.md`를 참고

## Key Services

| VM | Service | Port | Purpose |
| --- | --- | ---: | --- |
| Monitoring | Grafana | 3000 | 외부 Web UI |
| Monitoring | Loki | 3100 | 로그 수집 및 조회 |
| Monitoring | Mimir | 9009 | 메트릭 저장 및 조회 |
| Monitoring | Tempo | 3200 | 트레이스 조회 |
| Monitoring | OTel Collector | 4317, 4318 | 트레이스 수집 및 Tempo 전달 |
| Monitoring | Prometheus | 9090 | Monitoring VM backend 메트릭 scrape 및 remote write |
| Monitoring | Alertmanager | 9093 | Monitoring backend alert Slack 알림 전송 |
| Monitoring | MinIO | 9000, 9001 | 오브젝트 스토리지 |
| App | Alloy | 4317, 12345 | App VM 로그, 메트릭, 트레이스 수집 |
| App | api-service | 8080 | 데모 서비스 진입점 |
| App | catalog-service | 8081 | 상품 카탈로그 |
| App | inventory-service | 8082 | 재고 조회 및 예약 |
| App | cart-service | 8083 | 장바구니 처리 |
| App | order-service | 8084 | 주문 처리 |
| App | payment-service | 8085 | 결제 승인 |
| App | Node Exporter | 9100 | App VM 시스템 메트릭 |

## Security Group Inbound Allowed

Monitoring VM inbound:

| Port | Source | Purpose |
| ---: | --- | --- |
| 22/tcp | Your IP | SSH 접속 |
| 3000/tcp | Your IP | Grafana Web UI |
| 3100/tcp | App VM private IP | Alloy -> Loki 로그 전송 |
| 4317/tcp | App VM private IP | Alloy -> OTel Collector OTLP gRPC |
| 9009/tcp | App VM private IP | Alloy -> Mimir remote_write |

App VM inbound:

| Port | Source | Purpose |
| ---: | --- | --- |
| 22/tcp | Your IP | SSH 접속 |

## Generate Traffic

(1) App VM에서 짧게 수동 테스트할 때 사용

```bash
curl http://localhost:8080/browse
curl http://localhost:8080/cart/add
curl http://localhost:8080/checkout
curl http://localhost:8080/error
```

(2) 여러 날 동안 관찰할 트래픽을 만들 때 사용

```bash
chmod +x ./scripts/random-demo-traffic.sh
mkdir -p ./logs
./scripts/random-demo-traffic.sh
```

기본값은 정상 트래픽 위주로 생성하며, `/error` 요청은 포함하지 않는다.
오류율 관찰이 필요할 때는 `./scripts/k3s-fault-injection.sh error-burst`로 별도 생성한다.

Cron example:

```cron
* * * * * cd /home/ubuntu/lgtm-observability-stack && DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh >> /home/ubuntu/lgtm-observability-stack/logs/random-demo-traffic.log 2>&1
```

## Useful Queries

PromQL:

```promql
up
sum by (service) (rate(demo_app_requests_total[5m]))
histogram_quantile(0.95, sum by (le, service) (rate(demo_app_request_duration_seconds_bucket[5m])))
```

LogQL:

```logql
{job="k3s-pods", host="app-vm"}
{job="k3s-pods", host="app-vm"} |= "payment authorization failed"
```

TraceQL:

```traceql
{ resource.service.name = "api-service" }
{ resource.service.name = "api-service" || resource.service.name = "cart-service" || resource.service.name = "order-service" }
```

## Key Files

| Path | Description |
| --- | --- |
| `docker-compose.yml` | Monitoring VM 실행 정의 |
| `.env.example` | Monitoring VM용 환경변수 템플릿 |
| `k3s/app-vm` | App VM demo MSA K3S manifest |
| `configs/prometheus/prometheus.two-vm.yml` | Monitoring VM backend를 scrape하는 Prometheus 설정 |
| `configs/prometheus/rules/backend-alerts.yml` | Monitoring VM backend alert rule |
| `configs/mimir/rules/app-alerts.yml` | Mimir Ruler가 평가하는 App VM 및 MSA alert rule |
| `configs/alertmanager/alertmanager.yml` | Slack alert routing 설정 |
| `msa-demo` | 6개 MSA 데모 서비스가 공유하는 이미지 소스 |
| `scripts/random-demo-traffic.sh` | 장기 관찰용 랜덤 트래픽 생성 스크립트 |
| `scripts/k3s-fault-injection.sh` | K3S 배포용 장애 주입 및 복구 스크립트 |

## Documentation

- `docs/architecture.md` # LGTM observability stack 아키텍처
- `docs/two-vm-deployment.md` # 두 VM 배포 및 검증
- `docs/app-vm-k3s.md` # App VM K3S 선택 배포
- `docs/validation.md` # Grafana, Loki, Tempo, Mimir, Alloy 검증
- `docs/troubleshooting.md` # 문제 해결
- `docs/version-policy.md` # 버전 정책
