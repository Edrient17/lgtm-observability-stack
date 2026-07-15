# 2. 사전 요구사항

## 2.1 VM 구성

| VM | 역할 | 권장 사양 |
| --- | --- | --- |
| Monitoring VM | Grafana, Loki, Mimir, Tempo, Prometheus, Alertmanager, MinIO 실행 | 2 vCPU 이상, 4 GB RAM 이상 |
| App VM | K3S 기반 MSA 데모 서비스와 Alloy 실행 | 2 vCPU 이상, 4 GB RAM 이상 |

## 2.2 필수 소프트웨어

| 대상 | 필요 소프트웨어 |
| --- | --- |
| Monitoring VM | Ubuntu 24.04 LTS, Docker Engine 26.x 이상, Docker Compose v2.x 이상, Git 2.x 이상, curl |
| App VM | Ubuntu 24.04 LTS, Docker Engine 26.x 이상, K3S, kubectl, Git 2.x 이상, curl |

## 2.3 주요 버전 정보

플랫폼, 런타임, 컨테이너 이미지 버전은 [`docs/version-policy.md`](https://github.com/Edrient17/lgtm-observability-stack/blob/main/docs/version-policy.md)에서 관리합니다.
