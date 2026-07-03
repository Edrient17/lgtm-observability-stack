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
  - MinIO
  - OpenTelemetry Collector
  - Node Exporter for Monitoring VM metrics

App VM
  - API Service
  - Catalog Service
  - Inventory Service
  - Cart Service
  - Order Service
  - Payment Service
  - Node Exporter for App VM metrics
  - Promtail (App VM logs)
```

## Network Flow

```text
App VM -> Monitoring VM
  - 3100/tcp: Promtail이 Loki로 로그를 push
  - 4317/tcp: MSA 서비스가 OTel Collector로 OTLP gRPC trace 전송

Monitoring VM -> App VM
  - 8080/tcp: Prometheus가 API Service 메트릭 scrape
  - 8081/tcp: Prometheus가 Catalog Service 메트릭 scrape
  - 8082/tcp: Prometheus가 Inventory Service 메트릭 scrape
  - 8083/tcp: Prometheus가 Cart Service 메트릭 scrape
  - 8084/tcp: Prometheus가 Order Service 메트릭 scrape
  - 8085/tcp: Prometheus가 Payment Service 메트릭 scrape
  - 9100/tcp: Prometheus가 Node Exporter 메트릭 scrape

User -> Monitoring VM
  - 3000/tcp: Grafana Web UI
```

클라우드 네트워크에서 private IP 통신을 지원하면, VM 간 트래픽은 private IP를 기준으로 제한한다.

## Files

| File | VM | Purpose |
| --- | --- | --- |
| `.env.monitoring.example` | Monitoring VM | backend stack용 `.env` 템플릿 |
| `docker-compose.monitoring.yml` | Monitoring VM | Grafana, Loki, Mimir, Tempo, Prometheus, MinIO 구성 |
| `configs/prometheus/prometheus.two-vm.yml` | Monitoring VM | Monitoring VM과 App VM target scrape 설정 |
| `.env.app.example` | App VM | monitored app stack용 `.env` 템플릿 |
| `docker-compose.app.yml` | App VM | API, Catalog, Inventory, Cart, Order, Payment, Node Exporter, Promtail 구성 |
| `configs/promtail/promtail-app-config.yaml` | App VM | App VM 로그를 Monitoring VM Loki로 전송하는 Promtail 설정 |

## Monitoring VM Setup

Repository를 Monitoring VM에 복사한 뒤 환경 파일을 생성한다.

```bash
cp .env.monitoring.example .env
```

`.env`를 수정합니다.

```bash
COMPOSE_FILE=docker-compose.monitoring.yml
APP_VM_PRIVATE_IP=<app-vm-private-ip>
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

## App VM Setup

Repository를 App VM에 복사한 뒤 환경 파일을 생성한다.

```bash
cp .env.app.example .env
```

`.env`를 수정한다.

```bash
COMPOSE_FILE=docker-compose.app.yml
MONITORING_VM_PRIVATE_IP=<monitoring-vm-private-ip>
APP_HOST_LABEL=app-vm
```

App VM stack을 기동한다.

```bash
docker compose up -d --build
docker compose ps
```

## Validation

Monitoring VM에서 Prometheus가 App VM에 접근 가능한지 확인한다.

```bash
curl http://<app-vm-private-ip>:9100/metrics
curl http://<app-vm-private-ip>:8080/metrics
curl http://<app-vm-private-ip>:8081/metrics
curl http://<app-vm-private-ip>:8082/metrics
curl http://<app-vm-private-ip>:8083/metrics
curl http://<app-vm-private-ip>:8084/metrics
curl http://<app-vm-private-ip>:8085/metrics
```

App VM에서 Loki와 OTel Collector에 접근 가능한지 확인한다.

```bash
curl http://<monitoring-vm-private-ip>:3100/ready
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
- Logs: `{job="docker", host="app-vm"}`
- Traces: `{ resource.service.name = "api-service" }`
- MSA traces: `{ resource.service.name = "api-service" || resource.service.name = "cart-service" || resource.service.name = "order-service" }`

## Security Group Checklist

Monitoring VM inbound:

- `3000/tcp` from your IP
- `3100/tcp` from App VM private IP
- `4317/tcp` from App VM private IP
- `22/tcp` from your IP

App VM inbound:

- `8080/tcp` from Monitoring VM private IP
- `8081/tcp` from Monitoring VM private IP
- `8082/tcp` from Monitoring VM private IP
- `8083/tcp` from Monitoring VM private IP
- `8084/tcp` from Monitoring VM private IP
- `8085/tcp` from Monitoring VM private IP
- `9100/tcp` from Monitoring VM private IP
- `22/tcp` from your IP

Mimir, Tempo query API, Prometheus, MinIO console은 디버깅 목적이 아니라면 외부에 공개하지 않는다.
