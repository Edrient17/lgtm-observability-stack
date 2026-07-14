# Set-Up Details

이 문서는 README의 기본 설치 절차를 보완하는 상세 안내다.
두 VM 모두 Ubuntu 24.04 LTS 기준이며, Monitoring VM은 Docker Compose로 LGTM backend stack을 실행하고 App VM은 K3S로 demo MSA, Alloy, Node Exporter를 실행한다.

## 1. VM 초기 설정

아래 작업은 `git clone` 이전에 각 VM에서 수행한다.

### 1.1 공통 패키지 업데이트

Monitoring VM과 App VM 모두에서 실행한다.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg git make
```

시간대가 맞지 않으면 로그와 대시보드 시간이 헷갈릴 수 있으므로 Asia/Seoul로 맞춘다.

```bash
sudo timedatectl set-timezone Asia/Seoul
timedatectl
```

### 1.2 Docker Engine 설치

Monitoring VM과 App VM 모두 Docker를 사용한다.
Monitoring VM은 Docker Compose stack 실행에 사용하고, App VM은 `msa-demo:local` 이미지를 빌드한 뒤 K3S containerd로 import할 때 사용한다.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

현재 사용자를 `docker` 그룹에 추가한다.

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker version
docker compose version
```

`newgrp docker` 이후에도 Docker 권한 오류가 나면 SSH 세션을 종료하고 다시 접속한다.

### 1.3 Repository clone

초기 패키지와 Docker 설치가 끝난 뒤 각 VM에서 repository를 내려받는다.

```bash
git clone <REPOSITORY_URL>
cd lgtm-observability-stack
```

## 2. Monitoring VM 상세 안내

### 2.1 역할

Monitoring VM은 관측 backend를 담당한다.

```text
Grafana
Loki
Mimir
Tempo
Prometheus
Alertmanager
MinIO
OpenTelemetry Collector
Monitoring VM Node Exporter
```

### 2.2 Security Group

Monitoring VM inbound는 아래 포트만 허용한다.

| Port | Source | 용도 |
| ---: | --- | --- |
| `22/tcp` | 관리자 IP | SSH 접속 |
| `3000/tcp` | 관리자 IP | Grafana Web UI |
| `3100/tcp` | App VM private IP | Alloy -> Loki 로그 전송 |
| `4317/tcp` | App VM private IP | Alloy -> OTel Collector OTLP gRPC trace 전송 |
| `9009/tcp` | App VM private IP | Alloy `prometheus.remote_write` -> Mimir `/api/v1/push` |

Prometheus `9090`, Alertmanager `9093`, Tempo `3200`, MinIO `9000/9001`은 외부에 공개하지 않는다.

### 2.3 환경 변수 설정

```bash
cp .env.example .env
```

`.env`에서 최소한 아래 값을 수정한다.

```env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<strong-password>
MINIO_ROOT_USER=lgtm
MINIO_ROOT_PASSWORD=<strong-password>
SLACK_WEBHOOK_URL=<slack-incoming-webhook-url>
```

Slack 알림을 사용하지 않을 경우에도 현재 Alertmanager entrypoint는 `SLACK_WEBHOOK_URL`을 요구한다.
테스트 전에는 실제 Slack Incoming Webhook URL을 넣어두는 것을 권장한다.

### 2.4 Stack 기동

```bash
docker compose up -d
docker compose ps
```

정상적으로 올라오면 주요 컨테이너가 다음 이름으로 표시된다.

```text
grafana
loki
mimir
tempo
prometheus
alertmanager
otel-collector
minio
node-exporter-monitoring
```

### 2.5 Backend 상태 확인

Monitoring VM에서 확인한다.

```bash
curl http://localhost:3100/ready
curl http://localhost:9009/ready
curl http://localhost:3200/ready
curl http://localhost:9090/-/ready
```

Mimir Ruler rule이 로드되었는지 확인한다.

```bash
curl http://localhost:9009/prometheus/api/v1/rules
```

Prometheus backend rule은 다음 명령으로 확인한다.

```bash
docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

### 2.6 Grafana 접속

브라우저에서 접속한다.

```text
http://<monitoring-vm-public-ip>:3000
```

로그인 계정은 `.env`의 `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`를 사용한다.

### 2.7 Monitoring VM 중지

일반 중지는 다음 명령을 사용한다.

```bash
docker compose down
```

데이터 볼륨까지 삭제해야 하는 초기화 상황에서만 `-v`를 사용한다.

```bash
docker compose down -v
```

## 3. App VM 상세 안내

### 3.1 역할

App VM은 K3S 단일 노드에서 demo MSA와 telemetry agent를 실행한다.

```text
api-service
catalog-service
inventory-service
cart-service
order-service
payment-service
Alloy
App VM Node Exporter
```

Telemetry 흐름은 다음과 같다.

```text
logs    K3S pod log files -> Alloy -> Loki
metrics App services /metrics, Node Exporter -> Alloy prometheus.scrape -> Alloy prometheus.remote_write -> Mimir /api/v1/push
traces  App services OTLP gRPC -> Alloy -> OTel Collector -> Tempo
```

### 3.2 Security Group

App VM inbound는 기본적으로 관리자 SSH만 허용한다.
App VM의 service port는 K3S 내부 통신과 VM 내부 검증에 사용하며 외부 공개하지 않는다.

| Port | Source | 용도 |
| ---: | --- | --- |
| `22/tcp` | 관리자 IP | SSH 접속 |

App VM outbound는 Monitoring VM private IP의 `3100/tcp`, `4317/tcp`, `9009/tcp`에 접근 가능해야 한다.
특히 Mimir metric 전송은 `http://<monitoring-vm-private-ip>:9009/api/v1/push` endpoint를 사용하는 Prometheus remote_write 방식이다.

### 3.3 `user-data.yaml`을 이용한 자동 기동

App VM을 추가로 생성하거나 auto scaling 시연을 할 때는 `docs/user-data.yaml`을 VM 생성 화면의 user-data 또는 cloud-init 입력란에 넣어 자동 기동할 수 있다.
이 방식은 VM 부팅 후 bootstrap script를 systemd service로 실행하며, 실패 시 재시도한다.

자동 기동에서 수행하는 작업은 다음과 같다.

```text
필수 패키지 설치
Docker 기동
K3S 설치
Repository clone 또는 pull
App VM ConfigMap 생성
Demo image build/import
K3S manifest apply
Alloy, Node Exporter, MSA rollout 대기
랜덤 트래픽 cron 등록 및 초기 트래픽 생성
```

사용 전 `docs/user-data.yaml`에서 아래 값을 환경에 맞게 수정한다.

```bash
REPO_URL="<repository-url>"
MONITORING_VM_IP="<monitoring-vm-private-ip>"
```

`APP_HOST_LABEL`은 기본적으로 VM hostname을 사용한다.
따라서 VM 이름을 `app-vm-1`, `app-vm-2`, `app-vm-3`처럼 유니크하게 생성하면 Grafana에서 VM별로 분리 조회할 수 있다.

자동 기동 완료 후 Grafana에서 다음 쿼리로 신규 App VM 수집 여부를 확인할 수 있다.

```promql
up{job="msa-demo", instance="<app-vm-hostname>"}
```

```logql
{job="k3s-pods", host="<app-vm-hostname>"}
```

문제가 발생하면 App VM에서 아래 명령으로 bootstrap 상태를 확인한다.

```bash
cloud-init status --long
sudo journalctl -u lgtm-app-bootstrap --no-pager -n 100
kubectl -n msa-demo get pods,svc,daemonset
```

### 3.4 수동 기동 방법

자동 기동을 사용하지 않거나 단계별로 검증하면서 배포할 경우에는 아래 수동 절차를 따른다.

#### 3.4.1 K3S 설치

App VM에서 실행한다.

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable traefik --disable servicelb" sh -
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
kubectl get nodes
```

`kubectl get nodes`가 너무 오래 걸리면 K3S 서비스 상태를 확인한다.

```bash
sudo systemctl status k3s
sudo journalctl -u k3s --no-pager -n 100
```

#### 3.4.2 ConfigMap 생성

Repository clone 이후 App VM에서 ConfigMap 예시 파일을 로컬 전용 파일로 복사한다.

```bash
cp k3s/app-vm/configmap.example.yaml k3s/app-vm/configmap.yaml
```

`configmap.yaml`에서 Monitoring VM private IP를 입력한다.

```yaml
OTEL_EXPORTER_OTLP_ENDPOINT: "http://alloy:4317"
OTEL_EXPORTER_OTLP_INSECURE: "true"
ALLOY_OTLP_EXPORTER_ENDPOINT: "<monitoring-vm-private-ip>:4317"
MIMIR_REMOTE_WRITE_URL: "http://<monitoring-vm-private-ip>:9009/api/v1/push"
LOKI_PUSH_URL: "http://<monitoring-vm-private-ip>:3100/loki/api/v1/push"
LOG_LEVEL: "INFO"
APP_HOST_LABEL: "app-vm-1"
```

`APP_HOST_LABEL`은 VM마다 `app-vm-1`, `app-vm-2`처럼 유니크하게 지정한다.
`configmap.yaml`은 VM별 private IP와 host label을 포함하므로 git에 올리지 않는다.

#### 3.4.3 Monitoring VM 연결 확인

App VM에서 Monitoring VM endpoint에 접근 가능한지 확인한다.

```bash
curl http://<monitoring-vm-private-ip>:3100/ready
curl http://<monitoring-vm-private-ip>:9009/ready
curl http://<monitoring-vm-private-ip>:4318/
```

`4318`은 HTTP receiver 확인용이므로 `404 page not found` 같은 HTTP 응답이 오면 네트워크 연결은 된 것이다.

#### 3.4.4 Demo app 이미지 빌드 및 import

```bash
chmod +x ./scripts/k3s-load-demo-image.sh
./scripts/k3s-load-demo-image.sh
```

Docker 권한 오류가 나면 사용자가 `docker` 그룹에 반영되지 않은 상태다.
SSH 재접속 후 다시 실행하거나 임시로 `sudo`를 사용한다.

```bash
sudo ./scripts/k3s-load-demo-image.sh
```

#### 3.4.5 K3S 리소스 배포

```bash
kubectl apply -k ./k3s/app-vm
kubectl -n msa-demo get pods,svc,daemonset
```

정상 상태 예시:

```text
pod/api-service-...          1/1 Running
pod/cart-service-...         1/1 Running
pod/catalog-service-...      1/1 Running
pod/inventory-service-...    1/1 Running
pod/order-service-...        1/1 Running
pod/payment-service-...      1/1 Running
pod/alloy-...                1/1 Running
pod/node-exporter-...        1/1 Running
```

#### 3.4.6 App VM 기능 확인

App VM에서 demo app endpoint를 확인한다.

```bash
curl http://localhost:8080/
curl http://localhost:8080/browse
curl http://localhost:8080/cart/add
curl http://localhost:8080/checkout
curl http://localhost:8080/metrics
```

Alloy와 Node Exporter도 확인한다.

```bash
kubectl -n msa-demo logs daemonset/alloy --tail=100
curl http://localhost:9100/metrics
```

#### 3.4.7 정상 트래픽 생성

정상 트래픽을 수동 생성한다.

```bash
DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh
```

반복 생성이 필요하면 다음 명령을 사용한다.

```bash
while true; do DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh; sleep 10; done
```

여러 날 관찰하려면 cron에 등록한다.

```bash
mkdir -p /home/ubuntu/lgtm-observability-stack/logs
crontab -e
```

```cron
* * * * * cd /home/ubuntu/lgtm-observability-stack && DEMO_APP_URL=http://localhost:8080 MAX_REQUESTS_PER_RUN=30 IDLE_CHANCE_PERCENT=0 BURST_CHANCE_PERCENT=20 ./scripts/random-demo-traffic.sh >> /home/ubuntu/lgtm-observability-stack/logs/random-demo-traffic.log 2>&1
```

트래픽 스크립트는 정상 요청만 생성한다.
위 cron 예시는 1분마다 실행하되 한 번 실행될 때 요청 수를 늘려 request rate와 trace/log 흐름을 더 쉽게 관찰할 수 있게 한다.
장애 검증은 `scripts/k3s-fault-injection.sh` 또는 Monitoring VM의 Docker Compose stop/start로 실제 컴포넌트를 중단하고 복구하는 방식으로 수행한다.

#### 3.4.8 K3S 장애 테스트

예를 들어 `payment-service`를 중단한다.

```bash
./scripts/k3s-fault-injection.sh payment-down
```

복구한다.

```bash
./scripts/k3s-fault-injection.sh payment-up
```

지원하는 주요 작업:

```text
api-down / api-up
catalog-down / catalog-up
inventory-down / inventory-up
cart-down / cart-up
order-down / order-up
payment-down / payment-up
node-exporter-down / node-exporter-up
alloy-down / alloy-up
recover-all
```

서비스 down 시나리오는 Deployment replica를 0으로 줄이고, 복구 시 replica를 1로 되돌린다.
Node Exporter와 Alloy 시나리오는 DaemonSet 삭제/재적용으로 테스트한다.

### 3.5 App VM 중지

K3S App VM 리소스를 제거한다.

```bash
kubectl delete -k ./k3s/app-vm
```

K3S 자체 제거가 필요한 경우에만 아래 명령을 사용한다.

```bash
sudo /usr/local/bin/k3s-uninstall.sh
```

## 4. 배포 후 Grafana 확인

Monitoring VM과 App VM 배포 후 Grafana에서 다음 항목을 확인한다.

| Dashboard | 확인 항목 |
| --- | --- |
| MSA Overview | `up{job="msa-demo"}`, request rate, latency, HTTP status |
| Logs Overview | `{job="k3s-pods", host=~"app-vm-.*"}` 로그 수집 |
| Traces Overview | `api-service`, `cart-service`, `order-service` trace |
| VM Metrics | Monitoring VM, App VM CPU, memory, disk, network |
| Alerts Overview | Backend alert, App/MSA alert 상태 |

Mimir datasource는 Grafana에서 Prometheus-compatible datasource로 등록되어 있어야 한다.

| 항목 | 값 |
| --- | --- |
| Datasource name | `Mimir` |
| Type | `Prometheus` |
| URL | `http://mimir:9009/prometheus` |

유용한 쿼리:

```promql
up
up{job="msa-demo"}
sum by (service) (rate(demo_app_requests_total[5m]))
```

```logql
{job="k3s-pods", host=~"app-vm-.*"}
```

```traceql
{ resource.service.name = "api-service" }
```
