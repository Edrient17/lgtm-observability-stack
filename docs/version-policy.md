# Version Policy

이 문서는 프로젝트에서 사용하는 플랫폼, 런타임, 컨테이너 이미지 버전을 관리한다.
README에는 요약만 두고, 실제 버전 기준과 변경 절차는 이 문서를 기준으로 한다.

## 플랫폼 및 런타임

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

## 버전 관리 원칙

- floating tag보다 안정적인 patch release를 우선 사용
- 필요한 기능이 없다면 프로젝트 기간 중 새 major line은 피한다.
- 밀접하게 연동되는 component는 호환되는 release line으로 유지한다.
- version upgrade가 필요하면 이 파일에 기록하고 이후 검증을 다시 수행한다.

## 고정 버전

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
| OpenTelemetry Collector Contrib | `otel/opentelemetry-collector-contrib` | `0.155.0` | 안정적인 collector release tag |
| MinIO | `quay.io/minio/minio` | `RELEASE.2025-09-07T16-13-09Z` | MinIO server release tag를 고정합니다. |
| MinIO Client | `quay.io/minio/mc` | `RELEASE.2025-08-13T08-35-41Z` | bucket 초기화를 위한 client release tag를 고정 |
| Python base image | `python` | `3.12-slim` | `msa-demo` 서비스에 사용하는 가벼운 Python runtime |
| Demo App image | `msa-demo` | `local` | App VM에서 직접 빌드 후 K3S containerd로 import하는 로컬 이미지 |
