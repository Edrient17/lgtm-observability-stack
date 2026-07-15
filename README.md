# LGTM Observability Stack

K3S 기반 MSA 데모 애플리케이션의 로그, 메트릭, 트레이스를 수집하고 Grafana 대시보드와 Slack 알림으로 장애를 관측하는 2-VM 기반 Observability 프로젝트입니다.

![Architecture Diagram](images/architecture_diagram.svg)

## 문서

상세한 설치, 운영, 장애 테스트, 트러블슈팅 문서는 [Wiki Home](wiki/Home.md)에서 확인할 수 있습니다.

GitHub Wiki에 게시하려면 [wiki/Publish-Guide.md](wiki/Publish-Guide.md)를 참고합니다.

프로젝트 결과 보고서는 [Notion Report](https://icy-twill-e9c.notion.site/LGTM-Observability-Stack-39874c78d6bb80f1a76cecaf06a397e1)에서 확인할 수 있습니다.

## 구성 요약

이 프로젝트는 Monitoring VM과 App VM을 분리해 구성합니다.

- Monitoring VM: Grafana, Loki, Mimir, Tempo, Prometheus, Alertmanager, MinIO, Node Exporter를 Docker Compose로 실행합니다.
- App VM: K3S 위에서 MSA demo services, Alloy, Node Exporter를 실행하고 telemetry를 Monitoring VM으로 전송합니다.

## Telemetry Flow

| 구분 | 흐름 |
| --- | --- |
| Logs | K3S Pod stdout/stderr -> Alloy -> Loki -> Grafana |
| Metrics (App VM) | Alloy scrape -> Mimir remote_write -> Grafana |
| Metrics (Monitoring VM) | Prometheus scrape -> Mimir remote_write -> Grafana |
| Traces | App 서비스 -> Alloy -> Tempo -> Grafana |
| Alerts | Prometheus/Mimir Ruler -> Alertmanager -> Slack |
| Storage | Mimir, Tempo -> MinIO |

## 빠른 시작

### Monitoring VM

```bash
git clone https://github.com/Edrient17/lgtm-observability-stack.git
cd lgtm-observability-stack
cp .env.example .env
docker compose up -d
docker compose ps
```

`.env`에서 최소한 다음 값은 운영 환경에 맞게 변경합니다.

```env
GRAFANA_ADMIN_PASSWORD=<CHANGE_ME>
MINIO_ROOT_PASSWORD=<CHANGE_ME>
SLACK_WEBHOOK_URL=<SLACK_INCOMING_WEBHOOK_URL>
```

### App VM

```bash
git clone https://github.com/Edrient17/lgtm-observability-stack.git
cd lgtm-observability-stack
cp k3s/app-vm/configmap.example.yaml k3s/app-vm/configmap.yaml
```

`k3s/app-vm/configmap.yaml`에서 Monitoring VM private IP를 설정합니다.

```yaml
ALLOY_OTLP_EXPORTER_ENDPOINT: "<monitoring-vm-private-ip>:4317"
MIMIR_REMOTE_WRITE_URL: "http://<monitoring-vm-private-ip>:9009/api/v1/push"
LOKI_PUSH_URL: "http://<monitoring-vm-private-ip>:3100/loki/api/v1/push"
```

MSA 데모 이미지를 빌드하고 K3S에 배포합니다.

```bash
./scripts/k3s-load-demo-image.sh
kubectl apply -k ./k3s/app-vm
kubectl -n msa-demo get pods,svc,daemonset
```

## 접속

Grafana:

```text
http://<monitoring-vm-public-ip>:3000
```

기본 계정은 `.env`의 `GRAFANA_ADMIN_USER`, 비밀번호는 `GRAFANA_ADMIN_PASSWORD`를 사용합니다.

## 주요 명령

```bash
make up              # Monitoring VM stack 기동
make down            # Monitoring VM stack 중지
make ps              # Docker Compose 상태 확인
make validate        # Monitoring VM 또는 App VM health check
make traffic         # MSA 데모 트래픽 생성
make k3s-app-status  # App VM K3S 리소스 상태 확인
```

## 저장소 구조

```text
.
├── configs/       # Loki, Mimir, Tempo, Prometheus, Alertmanager 설정
├── grafana/       # Datasource, dashboard provisioning
├── k3s/app-vm/    # App VM K3S manifests
├── msa-demo/      # Python Flask 기반 MSA 데모 애플리케이션
├── scripts/       # healthcheck, traffic, image load, fault injection 스크립트
├── docs/          # 설정 상세, 검증 참고 문서
├── wiki/          # GitHub Wiki export 문서
└── images/        # 아키텍처 및 검증 스크린샷
```

## 검증 자료

Grafana dashboard와 장애 테스트 증빙 이미지는 Wiki에 정리되어 있습니다.

- [Grafana Dashboard](wiki/07-Grafana.md)
- [Fault Tests](wiki/09-Fault-Tests.md)
- [Validation Checklist](docs/validation.md)
