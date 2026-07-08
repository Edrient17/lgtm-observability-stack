# Two-VM Deployment

이 배포 방식은 관측 backend와 관측 대상 App VM을 분리한다.

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
  - Alertmanager
  - MinIO
  - OpenTelemetry Collector
  - Node Exporter for Monitoring VM metrics

App VM
  - K3S single-node cluster
  - API Service
  - Catalog Service
  - Inventory Service
  - Cart Service
  - Order Service
  - Payment Service
  - Node Exporter for App VM metrics
  - Alloy for App VM logs, metrics, traces
```

App VM의 demo MSA는 K3S로 실행한다.
K3S 배포 절차는 `docs/app-vm-k3s.md`를 참고한다.

## Network Flow

```text
App VM -> Monitoring VM
  - 3100/tcp: Alloy가 Loki로 로그를 push
  - 4317/tcp: Alloy가 OTel Collector로 OTLP gRPC trace 전송
  - 9009/tcp: Alloy가 Mimir로 metric remote_write

User -> Monitoring VM
  - 3000/tcp: Grafana Web UI
```

클라우드 네트워크에서 private IP 통신을 지원하면, VM 간 트래픽은 private IP를 기준으로 제한한다.

## Files

| File | VM | Purpose |
| --- | --- | --- |
| `.env.example` | Monitoring VM | backend stack용 `.env` 템플릿 |
| `docker-compose.yml` | Monitoring VM | Grafana, Loki, Mimir, Tempo, Prometheus, MinIO 구성 |
| `configs/prometheus/prometheus.two-vm.yml` | Monitoring VM | Monitoring VM backend target scrape 설정 |
| `k3s/app-vm` | App VM | demo MSA, Alloy, Node Exporter K3S manifest |

## Monitoring VM Setup

Repository를 Monitoring VM에 복사한 뒤 환경 파일을 생성한다.

```bash
cp .env.example .env
```

`.env`를 수정합니다.

```bash
GRAFANA_ADMIN_PASSWORD=<strong-password>
MINIO_ROOT_PASSWORD=<strong-password>
```

Monitoring VM stack을 기동한다.

```bash
docker compose up -d
docker compose ps
```

Grafana는 아래 주소로 접속할 수 있다.

```text
http://<monitoring-vm-public-ip>:3000
```

Slack 알림을 사용할 경우 `.env`에 `SLACK_WEBHOOK_URL`을 설정한다.

## App VM Setup

Repository를 App VM에 복사한 뒤 `configmap.example.yaml`을 로컬 전용 `configmap.yaml`로 복사하고 Monitoring VM private IP를 수정한다.

```bash
cp k3s/app-vm/configmap.example.yaml k3s/app-vm/configmap.yaml
```

```yaml
OTEL_EXPORTER_OTLP_ENDPOINT: "http://alloy:4317"
ALLOY_OTLP_EXPORTER_ENDPOINT: "<monitoring-vm-private-ip>:4317"
MIMIR_REMOTE_WRITE_URL: "http://<monitoring-vm-private-ip>:9009/api/v1/push"
LOKI_PUSH_URL: "http://<monitoring-vm-private-ip>:3100/loki/api/v1/push"
```

K3S 배포 절차는 `docs/app-vm-k3s.md`를 따른다.

## Validation

Monitoring VM에서 backend endpoint를 확인한다.

```bash
curl http://localhost:3100/ready
curl http://localhost:9009/ready
curl http://localhost:3200/ready
```

App VM에서 Loki, Mimir, OTel Collector에 접근 가능한지 확인한다.

```bash
curl http://<monitoring-vm-private-ip>:3100/ready
curl http://<monitoring-vm-private-ip>:9009/ready
curl http://<monitoring-vm-private-ip>:4318/
```

App VM에서 샘플 트래픽을 생성한다.

```bash
curl http://localhost:8080/
curl http://localhost:8080/browse
curl http://localhost:8080/cart/add
curl http://localhost:8080/checkout
curl http://localhost:8080/error
```

여러 날 관찰하려면 App VM에 랜덤 트래픽 스크립트를 cron으로 등록한다.

```bash
chmod +x ./scripts/random-demo-traffic.sh
crontab -e
```

랜덤 트래픽 스크립트는 기본적으로 `/error` 요청을 보내지 않는다.
오류율 관찰이 필요하면 `./scripts/k3s-fault-injection.sh error-burst`로 별도 생성한다.

Example cron entry:

```cron
* * * * * cd /home/ubuntu/lgtm-observability-stack && DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh >> /home/ubuntu/lgtm-observability-stack/logs/random-demo-traffic.log 2>&1
```

cron 등록 전에 로그 디렉터리를 생성한다.

```bash
mkdir -p /home/ubuntu/lgtm-observability-stack/logs
```

이후 Grafana에서 다음 항목을 확인한다.

- Metrics: `up`, `rate(demo_app_requests_total[5m])`
- MSA metrics: `sum by (service) (rate(demo_app_requests_total[5m]))`
- VM metrics: VM Metrics dashboard의 CPU, disk, filesystem, network panel
- Logs: `{job="k3s-pods", host="app-vm"}`
- Traces: `{ resource.service.name = "api-service" }`
- MSA traces: `{ resource.service.name = "api-service" || resource.service.name = "cart-service" || resource.service.name = "order-service" }`
- Alerts: Prometheus는 backend metric alert를 평가하고, Mimir Ruler는 App/MSA metric alert를 평가한 뒤 Alertmanager로 전달

## Security Group Checklist

Monitoring VM inbound:

- `3000/tcp` from your IP
- `3100/tcp` from App VM private IP
- `4317/tcp` from App VM private IP
- `9009/tcp` from App VM private IP
- `22/tcp` from your IP

App VM inbound:

- `22/tcp` from your IP

Mimir, Tempo query API, Prometheus, MinIO console은 디버깅 목적이 아니라면 외부에 공개하지 않는다.
