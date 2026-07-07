# App VM K3S Deployment

이 문서는 Monitoring VM은 Docker Compose 구성을 유지하고, App VM의 demo MSA는 K3S로 실행하는 배포 절차를 설명한다.

## Target Topology

```text
Monitoring VM
  - 기존 docker compose 유지
  - Prometheus, Loki, Tempo, Mimir, Grafana, OpenTelemetry Collector

App VM
  - K3S single-node cluster
  - api-service, catalog-service, inventory-service, cart-service, order-service, payment-service
  - Alloy DaemonSet
  - Node Exporter DaemonSet
```

App VM의 telemetry는 Alloy가 수집하고 Monitoring VM backend로 전송한다.

```text
logs    App pod log files -> Alloy -> Loki
metrics App services /metrics, Node Exporter -> Alloy -> Mimir
traces  App services OTLP gRPC -> Alloy -> OTel Collector -> Tempo
```

## Files

| Path | Purpose |
| --- | --- |
| `k3s/app-vm/namespace.yaml` | `msa-demo` namespace 생성 |
| `k3s/app-vm/configmap.example.yaml` | Monitoring VM 주소와 demo app 공통 환경변수 예시 |
| `k3s/app-vm/msa-services.yaml` | 6개 demo MSA Deployment/Service |
| `k3s/app-vm/alloy.yaml` | K3S pod log, metric, trace를 Monitoring VM backend로 전송 |
| `k3s/app-vm/node-exporter.yaml` | App VM system metric 노출 |
| `scripts/k3s-load-demo-image.sh` | `msa-demo:local` 이미지를 k3s containerd에 import |
| `scripts/k3s-fault-injection.sh` | K3S 기반 장애 주입 및 복구 |

## App VM Setup

k3s를 설치한다.

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable traefik --disable servicelb" sh -
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
kubectl get nodes
```

`configmap.example.yaml`을 로컬 전용 `configmap.yaml`로 복사한 뒤 Monitoring VM private IP를 수정한다.

```bash
cp k3s/app-vm/configmap.example.yaml k3s/app-vm/configmap.yaml
```

```yaml
OTEL_EXPORTER_OTLP_ENDPOINT: "http://alloy:4317"
ALLOY_OTLP_EXPORTER_ENDPOINT: "<monitoring-vm-private-ip>:4317"
MIMIR_REMOTE_WRITE_URL: "http://<monitoring-vm-private-ip>:9009/api/v1/push"
LOKI_PUSH_URL: "http://<monitoring-vm-private-ip>:3100/loki/api/v1/push"
```

Demo app 이미지를 빌드하고 k3s containerd에 import한다.

```bash
chmod +x ./scripts/k3s-load-demo-image.sh
./scripts/k3s-load-demo-image.sh
```

K3S 리소스를 배포한다.

```bash
kubectl apply -k ./k3s/app-vm
kubectl -n msa-demo get pods,svc,daemonset
```

Makefile을 사용할 수도 있다.

```bash
make k3s-load-image
make k3s-app-apply
make k3s-app-status
```

## Validation

App VM에서 서비스 응답을 확인한다.

```bash
curl http://localhost:8080/
curl http://localhost:8080/browse
curl http://localhost:8080/cart/add
curl http://localhost:8080/checkout
curl http://localhost:8080/metrics
```

App VM에서 Alloy와 local scrape 경로를 확인한다.

```bash
kubectl -n msa-demo logs daemonset/alloy --tail=100
curl http://localhost:8080/metrics
curl http://localhost:9100/metrics
```

Grafana에서는 기존 dashboard를 그대로 사용할 수 있다.

- `MSA Overview`: app request, scrape request, error rate, latency 확인
- `Logs Overview`: `{job="k3s-pods", host="app-vm"}` 기준으로 K3S pod log 조회
- `Traces Overview`: `api-service`, `cart-service`, `order-service` trace 확인
- `VM Metrics`: App VM node-exporter metric 확인

## Traffic Generation

기존 트래픽 스크립트를 그대로 사용할 수 있다.

```bash
DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh
```

cron도 기존과 동일하게 사용할 수 있다.

```cron
* * * * * cd /home/ubuntu/lgtm-observability-stack && DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh >> /home/ubuntu/lgtm-observability-stack/logs/random-demo-traffic.log 2>&1
```

## Failure Injection

K3S 배포에서는 `scripts/k3s-fault-injection.sh`를 사용한다.

```bash
chmod +x ./scripts/k3s-fault-injection.sh
./scripts/k3s-fault-injection.sh payment-down
./scripts/k3s-fault-injection.sh payment-up
```

지원하는 주요 작업은 다음과 같다.

```text
api-down / api-up
catalog-down / catalog-up
inventory-down / inventory-up
cart-down / cart-up
order-down / order-up
payment-down / payment-up
node-exporter-down / node-exporter-up
alloy-down / alloy-up
error-burst
recover-all
```

서비스 down 시나리오는 Deployment replica를 0으로 줄이고, 복구 시 replica를 1로 되돌린다.
Node Exporter와 Alloy 시나리오는 DaemonSet 삭제/재적용으로 테스트한다.

## Stop K3S App Stack

K3S App VM 구성을 중지하려면 아래 명령을 사용한다.

```bash
kubectl delete -k ./k3s/app-vm
```

K3S 자체를 제거해야 하는 경우에만 아래 명령을 사용한다.

```bash
sudo /usr/local/bin/k3s-uninstall.sh
```
