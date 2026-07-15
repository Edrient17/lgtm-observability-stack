# LGTM Observability Stack

K3S 기반 애플리케이션을 대상으로 로그, 메트릭, 트레이스를 수집하고 Grafana 대시보드와 Slack 알림으로 장애를 관측하는 2-VM 기반 LGTM Observability 프로젝트입니다.

- Repository: [Edrient17/lgtm-observability-stack](https://github.com/Edrient17/lgtm-observability-stack)
- Notion Report: [LGTM Observability Stack](https://icy-twill-e9c.notion.site/LGTM-Observability-Stack-39874c78d6bb80f1a76cecaf06a397e1)

![Architecture Diagram](https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/architecture_diagram.jpg)

## Wiki 목차

| 페이지 | 내용 |
| --- | --- |
| [프로젝트 아키텍처](01-Architecture.md) | Monitoring VM, App VM 구성과 telemetry/request 흐름 |
| [사전 요구사항](02-Prerequisites.md) | VM 사양, 필수 소프트웨어, 버전 기준 |
| [네트워크 및 포트 정책](03-Network-and-Ports.md) | Security Group inbound 정책과 서비스 포트 |
| [설치 및 기동 방법](04-Installation-and-Runbook.md) | Monitoring VM, App VM 설치 및 실행 절차 |
| [서비스 접속 정보](05-Service-Access.md) | Grafana 접속 정보와 주요 내부 endpoint |
| [주요 설정](06-Configuration.md) | 핵심 설정 파일, 환경 변수, App VM ConfigMap |
| [Grafana](07-Grafana.md) | Dashboard, alert rule, Explore 쿼리 |
| [애플리케이션 시범 운영](08-Demo-Operations.md) | 랜덤 트래픽 생성과 장기 관찰 |
| [장애 테스트](09-Fault-Tests.md) | App/MSA 및 Monitoring backend 장애 테스트 |
| [트러블슈팅](10-Troubleshooting.md) | No data, metric missing, alert count 이슈 대응 |

## 빠른 시작

Monitoring VM에서 backend stack을 기동합니다.

```bash
cp .env.example .env
docker compose up -d
docker compose ps
```

App VM에서 K3S 리소스를 배포합니다.

```bash
cp k3s/app-vm/configmap.example.yaml k3s/app-vm/configmap.yaml
./scripts/k3s-load-demo-image.sh
kubectl apply -k ./k3s/app-vm
kubectl -n msa-demo get pods,svc,daemonset
```

Grafana는 `http://<monitoring-vm-public-ip>:3000`에서 접속합니다.
