# LGTM Observability Stack

K3S 기반 애플리케이션을 대상으로 로그, 메트릭, 트레이스를 수집하고 Grafana 대시보드와 Slack 알림으로 장애를 관측하는 2-VM 기반 LGTM Observability 프로젝트

<details>
<summary><strong>1. 프로젝트 아키텍처</strong></summary>

## 1. 프로젝트 아키텍처

![Architecture Diagram](images/architecture_diagram.jpg)

Docker Compose로 구성한 Monitoring VM 서비스는 다음과 같다.

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

K3S로 구성한 App VM 리소스는 다음과 같다.

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

### 1.1 Telemetry Flow

| 구분 | 흐름 |
| --- | --- |
| Logs | K3S Pod stdout/stderr -> `/var/log/containers/*.log` -> Alloy -> Loki -> Grafana |
| Metrics (App VM) | App VM의 Alloy가 App /metrics와 Node Exporter를 scrape하고, Prometheus remote_write 방식으로 Mimir /api/v1/push에 전송 -> Grafana |
| Metrics (Monitoring VM) | Prometheus가 Grafana, Loki, Mimir, Tempo, Alertmanager, Monitoring VM Node Exporter `/metrics`를 scrape -> Mimir remote_write -> Grafana |
| Traces | App 서비스 -> OTLP gRPC -> Alloy -> OTel Collector -> Tempo -> Grafana |
| Backend Alerts | Prometheus -> Alertmanager -> Slack |
| App/MSA Alerts | Alloy -> Mimir -> Mimir Ruler -> Alertmanager -> Slack |
| Storage | Mimir, Tempo -> MinIO object storage |

- 자세한 수집 경로는 docs/set-up-details.md 참고

### 1.2 Application Request Flow

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

</details>

<details>
<summary><strong>2. 사전 요구사항</strong></summary>

## 2. 사전 요구사항

### 2.1 VM 구성

| VM | 역할 | 권장 사양 |
| --- | --- | --- |
| Monitoring VM | Grafana, Loki, Mimir, Tempo, Prometheus, Alertmanager, MinIO 실행 | 2 vCPU 이상, 4 GB RAM 이상 |
| App VM | K3S 기반 MSA 데모 서비스와 Alloy 실행 | 2 vCPU 이상, 4 GB RAM 이상 |

### 2.2 필수 소프트웨어

| 대상 | 필요 소프트웨어 |
| --- | --- |
| Monitoring VM | Ubuntu 24.04 LTS, Docker Engine 26.x 이상, Docker Compose v2.x 이상, Git 2.x 이상, curl |
| App VM | Ubuntu 24.04 LTS, Docker Engine 26.x 이상, K3S, kubectl, Git 2.x 이상, curl |

### 2.3 주요 버전 정보

플랫폼, 런타임, 컨테이너 이미지 버전은 `docs/version-policy.md`에서 관리한다.

</details>

<details>
<summary><strong>3. 네트워크 및 포트 정책</strong></summary>

## 3. 네트워크 및 포트 정책

### 3.1 Security Group Inbound 정책

Inbound는 기본적으로 암시적 거부 정책을 적용하며, 필요한 포트만 허용한다.
Outbound는 기본적으로 모두 허용 정책을 적용한다. 실무에서는 필요 시 outbound도 제한한다.

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

### 3.2 서비스 포트

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

</details>

<details>
<summary><strong>4. 설치 및 기동 방법</strong></summary>

## 4. 설치 및 기동 방법

### 4.1 프로젝트 다운로드

각 VM에서 리포지토리를 내려받고 프로젝트 디렉터리로 이동한다.

```bash
git clone <REPOSITORY_URL>
cd lgtm-observability-stack
```

### 4.2 Monitoring VM 환경 변수 설정

예시 환경 변수 파일을 복사하여 실제 Docker Compose 실행에 사용할 `.env` 파일을 생성한다.

```bash
cp .env.example .env
```

`.env`에서 다음 값을 환경에 맞게 수정한다.

```env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<CHANGE_ME>
MINIO_ROOT_USER=lgtm
MINIO_ROOT_PASSWORD=<CHANGE_ME>
SLACK_WEBHOOK_URL=<SLACK_INCOMING_WEBHOOK_URL>
```

### 4.3 Monitoring VM 기동

Monitoring VM의 전체 LGTM backend stack은 프로젝트 루트에서 다음 단일 명령으로 기동한다.

```bash
docker compose up -d
```

이후 정상 기동 여부를 확인한다.

```bash
docker compose ps
```

정상 기동 예시 ↓

![Docker Compose](images/docker_compose_ps.png)

### 4.4 App VM 설정

App VM에서는 K3S manifest에 사용할 ConfigMap을 생성하고 Monitoring VM private IP를 입력한다.

```bash
cp k3s/app-vm/configmap.example.yaml k3s/app-vm/configmap.yaml
```

수정할 주요 항목은 다음과 같다.

```yaml
ALLOY_OTLP_EXPORTER_ENDPOINT: "<monitoring-vm-private-ip>:4317"
MIMIR_REMOTE_WRITE_URL: "http://<monitoring-vm-private-ip>:9009/api/v1/push"
LOKI_PUSH_URL: "http://<monitoring-vm-private-ip>:3100/loki/api/v1/push"
```

### 4.5 App VM 이미지 빌드 및 K3S 배포

MSA 데모 이미지를 빌드하고 K3S containerd에 import한다.

```bash
./scripts/k3s-load-demo-image.sh
```

K3S 리소스를 적용한다.

```bash
kubectl apply -k ./k3s/app-vm
```

상태를 확인한다.

```bash
kubectl -n msa-demo get pods,svc,daemonset
```

### 4.6 서비스 중지

Monitoring VM stack을 중지한다.

```bash
docker compose down
```

볼륨까지 삭제하는 초기화가 필요한 경우에만 `-v`를 사용한다.

```bash
docker compose down -v
```

App VM의 K3S 리소스를 중지한다.

```bash
kubectl delete -k ./k3s/app-vm
```

K3S 자체를 제거해야 하는 경우에만 아래 명령을 사용한다.

```bash
sudo /usr/local/bin/k3s-uninstall.sh
```

</details>

<details>
<summary><strong>5. 서비스 접속 정보</strong></summary>

## 5. 서비스 접속 정보

### 5.1 Grafana

| 항목 | 값 |
| --- | --- |
| URL | `http://<monitoring-vm-public-ip>:3000` |
| 기본 계정 | `.env`의 `GRAFANA_ADMIN_USER` |
| 기본 비밀번호 | `.env`의 `GRAFANA_ADMIN_PASSWORD` |

초기 예시는 다음과 같다.

```text
Username: admin
Password: admin
```

실제 배포 시에는 `.env`에서 `GRAFANA_ADMIN_PASSWORD`를 변경한다.

### 5.2 주요 내부 Endpoint

Monitoring VM에서 확인:

```bash
curl http://localhost:3100/ready
curl http://localhost:9009/ready
curl http://localhost:3200/ready
curl http://localhost:9090/-/ready
```

App VM에서 확인:

```bash
curl http://<monitoring-vm-private-ip>:3100/ready
curl http://<monitoring-vm-private-ip>:9009/ready
curl http://<monitoring-vm-private-ip>:4318/
curl http://localhost:8080/browse
curl http://localhost:8080/cart/add
curl http://localhost:8080/checkout
```

</details>

<details>
<summary><strong>6. 주요 설정 파일</strong></summary>

## 6. 주요 설정

### 6.1 주요 파일

| 파일 | 설명 |
| --- | --- |
| `docker-compose.yml` | Monitoring VM에서 실행되는 LGTM backend stack 정의 |
| `.env.example` | Monitoring VM 환경 변수 예시 |
| `configs/loki/loki-config.yaml` | Loki 로그 저장 및 retention 설정 |
| `configs/mimir/mimir-config.yaml` | Mimir metric 저장소, ruler, MinIO 연동 설정 |
| `configs/mimir/rules/app-alerts.yml` | Mimir Ruler가 평가하는 App/MSA alert rule |
| `configs/tempo/tempo-config.yaml` | Tempo trace 저장 및 MinIO 연동 설정 |
| `configs/prometheus/prometheus.yml` | Monitoring VM backend scrape 및 backend alert 설정 |
| `configs/prometheus/rules/backend-alerts.yml` | Prometheus가 평가하는 Monitoring backend alert rule |
| `configs/alertmanager/alertmanager.yml` | Alertmanager Slack routing 설정 |
| `grafana/provisioning/datasources/datasources.yaml` | Grafana datasource 자동 등록 설정 |
| `grafana/provisioning/dashboards/dashboards.yaml` | Grafana dashboard 자동 등록 설정 |
| `grafana/dashboards/*.json` | Grafana dashboard JSON |
| `k3s/app-vm/configmap.example.yaml` | App VM ConfigMap 예시 |
| `k3s/app-vm/alloy.yaml` | Alloy 로그, 메트릭, 트레이스 수집 설정 |
| `k3s/app-vm/msa-services.yaml` | MSA 서비스 Deployment, Service 정의 |
| `k3s/app-vm/node-exporter.yaml` | App VM Node Exporter DaemonSet 정의 |
| `msa-demo/app.py` | MSA 데모 애플리케이션 코드 |
| `docs/set-up-details.md` | VM 초기 설정, Monitoring VM, App VM 상세 설치 안내 |
| `docs/version-policy.md` | 플랫폼, 런타임, 이미지 버전 정책 |

### 6.2 주요 환경 변수

| 변수 | 의미 |
| --- | --- |
| `GRAFANA_ADMIN_USER` | Grafana 관리자 계정 |
| `GRAFANA_ADMIN_PASSWORD` | Grafana 관리자 비밀번호 |
| `MINIO_ROOT_USER` | MinIO root 계정 |
| `MINIO_ROOT_PASSWORD` | MinIO root 비밀번호 |
| `SLACK_WEBHOOK_URL` | Alertmanager가 사용할 Slack Incoming Webhook URL |
| `PROMETHEUS_LOCAL_RETENTION` | Prometheus local TSDB 보관 기간 |
| `MIMIR_METRICS_RETENTION` | Mimir metric 보관 기간 |
| `TEMPO_TRACE_RETENTION` | Tempo trace 보관 기간 |

### 6.3 App VM ConfigMap 주요 값

| Key | 의미 |
| --- | --- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | MSA 서비스가 trace를 보낼 Alloy OTLP endpoint |
| `ALLOY_OTLP_EXPORTER_ENDPOINT` | Alloy가 trace를 전달할 Monitoring VM OTel Collector 주소 |
| `MIMIR_REMOTE_WRITE_URL` | Alloy `prometheus.remote_write`가 사용할 Mimir endpoint. |
| `LOKI_PUSH_URL` | Alloy가 log를 push할 Loki 주소 |
| `APP_HOST_LABEL` | App VM metric/log label |
| `LOG_LEVEL` | MSA 서비스 로그 레벨 |

</details>

<details>
<summary><strong>7. Grafana</strong></summary>

## 7. Grafana

### 7.1 Dashboard

Grafana dashboard는 `grafana/dashboards` 디렉터리의 JSON 파일로 자동 provision된다.

| Dashboard | 설명 |
| --- | --- |
| `MSA Overview` | MSA service scrape status, request rate, latency, HTTP status, error rate 확인 |
| `Logs Overview` | 서비스별 로그량, 레벨별 로그량, 최근 오류 로그 확인 |
| `Traces Overview` | trace 검색, entry/downstream span call rate, span latency 확인 |
| `VM Metrics` | Monitoring VM과 App VM의 CPU, memory, disk, network 확인 |
| `Alerts Overview` | App/MSA alert와 Monitoring backend alert 상태 확인 |


<details>
<summary><strong>대시보드 스크린샷</strong></summary>

- MSA Overview
![MSA Overview](images/screenshots/dashboards/msa_overview.png)

- Logs Overview
![Logs Overview](images/screenshots/dashboards/logs_overview.png)

- Traces Overview
![Traces Overview](images/screenshots/dashboards/traces_overview.png)

- VM Metrics
![VM Metrics](images/screenshots/dashboards/vm_metrics.png)

- Alerts Overview
![Alerts Overview](images/screenshots/dashboards/alerts_overview.png)

</details>

### 7.2 Grafana Explore 유용한 쿼리

#### 7.2.1 PromQL

| PromQL | 설명 |
|---|---|
| up | Monitoring VM backend metric scrape 상태 확인 |
| up{job="msa-demo"} | App VM metric scrape 상태 확인 |
| sum by (service) (rate(demo_app_requests_total[5m])) | App VM MSA 서비스별 request rate 확인 |
| sum by (service, status) (rate(demo_app_requests_total{endpoint!="metrics"}[5m])) | App VM MSA 서비스별 HTTP status code 확인 |
| histogram_quantile(0.95, sum by (le, service) (rate(demo_app_request_duration_seconds_bucket[5m]))) | App VM MSA 서비스별 95th percentile latency 확인 |
| ALERTS | 현재 firing alert 확인 |

#### 7.2.2 LogQL

| LogQL | 설명 |
|---|---|
| {job="k3s-pods", host="app-vm"} | App VM K3S Pod 로그 확인 |
| {job="k3s-pods", host="app-vm", level="ERROR"} | App VM K3S Pod ERROR 로그 확인 |
| {job="k3s-pods", host="app-vm", service="api-service"} | api-service 로그 확인 |

#### 7.2.3 TraceQL

| TraceQL | 설명 |
|---|---|
| { resource.service.name = "api-service" } | api-service 관련 trace 확인 |
| { resource.service.name = "api-service" \|\| resource.service.name = "cart-service" \|\| resource.service.name = "order-service" } | api-service, cart-service, order-service 관련 trace 확인 |


</details>

<details>
<summary><strong>8. 애플리케이션 시범 운영</strong></summary>

## 8. 애플리케이션 시범 운영

### 8.1 랜덤 트래픽 생성

App VM에서 정상 트래픽을 수동으로 생성한다.

```bash
cd ~/lgtm-observability-stack
DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh
```

반복 생성이 필요하면 다음 명령어를 사용한다.

```bash
while true; do DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh; sleep 10; done
```

여러 날 관찰할 경우 cron에 등록한다.

```cron
* * * * * cd /home/ubuntu/lgtm-observability-stack && DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh >> /home/ubuntu/lgtm-observability-stack/logs/random-demo-traffic.log 2>&1
```

랜덤 트래픽 스크립트는 정상 요청만 생성한다.
애플리케이션은 평상시 정상 동작을 목표로 하며, 장애 테스트는 9번 항목처럼 실제 컴포넌트를 중단하고 복구하는 방식으로 수행한다.

</details>

<details>
<summary><strong>9. 장애 테스트</strong></summary>

## 9. 장애 테스트

### 9.1 App/MSA 장애 테스트

`payment-service`를 중단한다.

```bash
kubectl -n msa-demo scale deployment payment-service --replicas=0
```

복구한다.

```bash
kubectl -n msa-demo scale deployment payment-service --replicas=1
```

기대 결과:

| 관측 위치 | 기대 결과 |
| --- | --- |
| MSA Overview | `payment-service scrape DOWN` 표시 |
| Alerts Overview | `MsaServiceDown` pending 후 firing 전환 |
| Slack | firing 및 resolved 알림 수신 |
| Logs Overview | downstream 호출 실패 로그 확인 |
| Traces Overview | checkout trace에서 payment-service 호출 실패 확인 |

### 9.2 Monitoring backend 장애 테스트

Loki를 중단한다.

```bash
docker compose stop loki
```

복구한다.

```bash
docker compose start loki
```

기대 결과:

| 관측 위치 | 기대 결과 |
| --- | --- |
| Alerts Overview | `LokiTargetDown` backend firing 표시 |
| Slack | Loki backend 장애 알림 수신 |
| Logs Overview | Loki 중단 중 로그 조회 실패 또는 지연 |

### 9.3 장애 테스트 증빙 이미지

```text
images/screenshots/fault-tests/payment_service_down_before.png
images/screenshots/fault-tests/payment_service_down_firing.png
images/screenshots/fault-tests/payment_service_down_slack.png
images/screenshots/fault-tests/payment_service_down_logs.png
images/screenshots/fault-tests/payment_service_down_traces.png
images/screenshots/fault-tests/payment_service_down_resolved.png
```

</details>

<details>
<summary><strong>10. 트러블슈팅</strong></summary>

## 10. 트러블슈팅

### 10.1 Dashboard Has No Data

- Symptom:
  - Grafana dashboard는 열리지만 panel에 `No data`가 표시됨.
- Root cause:
  - App VM 트래픽이 생성되지 않았거나, Alloy가 Mimir/Loki/OTel Collector로 데이터를 보내지 못하고 있을 수 있음.
- Fix:
  - App VM에서 `./scripts/random-demo-traffic.sh`를 실행
  - `up`과 `sum by (service) (rate(demo_app_requests_total[5m]))`를 조회
  - App VM에서 `kubectl -n msa-demo logs daemonset/alloy --tail=100`으로 전송 오류를 확인
  - `k3s/app-vm/configmap.yaml`의 `LOKI_PUSH_URL`, `MIMIR_REMOTE_WRITE_URL`, `ALLOY_OTLP_EXPORTER_ENDPOINT`가 Monitoring VM private IP를 가리키는지 확인

### 10.2 New App VM Is Running But Grafana Shows No App Metrics

- Symptom:
  - App VM에서 `kubectl -n msa-demo get pods,svc,daemonset`은 정상이다.
  - App VM local `/metrics` endpoint도 응답한다.
  - Grafana `MSA Overview` 또는 `VM Metrics`에서 App VM metric이 보이지 않는다.
- Root cause:
  - Alloy가 App VM 내부 target scrape에는 성공하지만, Monitoring VM의 Mimir `9009/tcp`로 remote_write 하지 못하는 상태일 수 있다.
  - 보안그룹에서 Monitoring VM `9009/tcp` inbound가 App VM private IP에 열려 있지 않거나, `MIMIR_REMOTE_WRITE_URL` 값이 잘못되었을 수 있다.
- Check:
  - App VM에서 Monitoring VM Mimir ready endpoint를 확인한다.

    ```bash
    curl http://<monitoring-vm-private-ip>:9009/ready
    ```

  - Alloy 로그를 확인한다.

    ```bash
    kubectl -n msa-demo logs daemonset/alloy --tail=100
    ```
- Fix:
  - Monitoring VM 보안그룹에서 `9009/tcp`를 App VM private IP에 허용한다.
  - App VM의 `k3s/app-vm/configmap.yaml`에서 `MIMIR_REMOTE_WRITE_URL`을 수정한다.
  - K3S 리소스를 다시 적용하고 Alloy를 재시작한다.

    ```bash
    kubectl apply -k ./k3s/app-vm
    kubectl -n msa-demo rollout restart daemonset/alloy
    ```
  - Grafana `MSA Overview`를 새로고침하고 `Service Up`이 `UP`으로 돌아오는지 확인한다.

### 10.3 Alert Count Panel Changes When Time Range Is Expanded

- Symptom:
  - Grafana `Alerts Overview`에서 `App/MSA Firing Alert Count` 또는 `Backend Firing Alert Count`가 `Last 30 minutes`에서는 `OK`로 보인다.
  - 같은 패널이 `Last 90 days`처럼 긴 기간에서는 `1` 이상으로 표시된다.
  - 실제 현재 장애는 없는데 과거 firing 이력이 현재 alert count처럼 보인다.
- Root cause:
  - Alert count stat panel은 현재 시점의 firing alert 개수를 보여야 한다.
  - 하지만 query target이 range query로 설정되어 있으면 Grafana가 선택한 전체 시간 범위의 `ALERTS{alertstate="firing"}` series를 조회한다.
  - 이 경우 과거에 firing 되었던 alert sample이 stat reduce 과정에 포함되어 현재 firing count처럼 표시될 수 있다.
- Check:
  - `grafana/dashboards/alerts-overview.json`에서 firing count panel target을 확인한다.

    ```json
    "instant": true,
    "range": false
    ```

  - Timeline panel은 과거 이력을 보여야 하므로 `range: true`가 맞다.
- Fix:
  - 현재 상태를 나타내는 firing count stat panel은 instant query로 설정한다.
  - App/MSA와 Backend firing count panel 모두 다음 설정을 사용한다.

    ```json
    "instant": true,
    "range": false
    ```

  - Monitoring VM에서 Grafana를 재시작해 provisioned dashboard를 다시 읽게 한다.

    ```bash
    docker compose restart grafana
    ```
- Result:
  - `Last 90 days`처럼 긴 시간 범위를 선택해도 firing count panel은 현재 시점의 firing alert 개수만 표시한다.
  - 과거 firing 이력은 `App/MSA Firing Timeline`, `Backend Firing Timeline`에서 확인한다.

</details>
