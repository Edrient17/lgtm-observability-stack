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

### 2.3.1 플랫폼 및 런타임

| 구분 | 구성요소 | 현재 프로젝트 기준 |
| --- | --- | --- |
| OS | Ubuntu | `24.04 LTS` |
| Container Runtime | Docker Engine | `26.x` 이상 |
| Compose | Docker Compose | `v2.x` 이상 |
| Kubernetes Runtime | K3S | 단일 노드 K3S |
| Kubernetes CLI | kubectl | K3S server version과 호환 |
| Source Control | Git | `2.x` 이상 |
| Shell | Bash | Ubuntu 기본 Bash |
| App Runtime | Python | `3.12-slim` base image |

### 2.3.2 버전 관리 원칙

- floating tag보다 안정적인 patch release를 우선 사용합니다.
- 필요한 기능이 없다면 프로젝트 기간 중 새 major line은 피합니다.
- 밀접하게 연동되는 component는 호환되는 release line으로 유지합니다.
- version upgrade가 필요하면 관련 설정과 검증 결과를 함께 갱신합니다.

### 2.3.3 고정 버전

| Component | Image | Version | Reason |
| --- | --- | --- | --- |
| Grafana | `grafana/grafana-oss` | `12.4.3` | 최신 Grafana 13 major line 대신 안정적인 Grafana 12 line을 사용 |
| Loki | `grafana/loki` | `3.6.11` | 현재 Grafana stack과 호환되는 안정적인 Loki 3.6 line |
| Alloy | `grafana/alloy` | `v1.17.0` | App VM 로그, 메트릭, 트레이스를 수집하고 Monitoring VM backend로 전달 |
| Mimir | `grafana/mimir` | `3.1.2` | Mimir 3 line의 안정적인 patch release |
| Tempo | `grafana/tempo` | `2.10.7` | Tempo 3 major line은 피하면서 최근 OTLP/TraceQL 기능을 사용할 수 있는 버전 |
| Prometheus | `prom/prometheus` | `v3.5.4` | 안정적인 Prometheus 3 release branch |
| Alertmanager | `prom/alertmanager` | `v0.28.1` | Monitoring backend alert를 Slack으로 전달하기 위한 안정적인 Alertmanager release |
| Node Exporter | `prom/node-exporter` | `v1.11.1` | 안정적인 node-exporter release |
| MinIO | `quay.io/minio/minio` | `RELEASE.2025-09-07T16-13-09Z` | MinIO server release tag를 고정 |
| MinIO Client | `quay.io/minio/mc` | `RELEASE.2025-08-13T08-35-41Z` | bucket 초기화를 위한 client release tag를 고정 |
| Python base image | `python` | `3.12-slim` | `msa-demo` 서비스에 사용하는 가벼운 Python runtime |
| Demo App image | `msa-demo` | `local` | App VM에서 직접 빌드 후 K3S containerd로 import하는 로컬 이미지 |
