# Version Policy

## Strategy

- floating tag보다 안정적인 patch release를 우선 사용
- 필요한 기능이 없다면 프로젝트 기간 중 새 major line은 피한다.
- 밀접하게 연동되는 component는 호환되는 release line으로 유지한다.
- version upgrade가 필요하면 이 파일에 기록하고 이후 검증을 다시 수행한다.

## Pinned Versions

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

## Upgrade Rule

component 계열은 한 번에 하나씩 upgrade 한다.

1. `.env.example`, `docker-compose.yml`, `k3s/app-vm` manifest의 image tag를 수정
2. 작업 PC에서 `docker compose --env-file .env.example config`를 실행
3. 작업 PC에서 `kubectl kustomize k3s/app-vm`을 실행
4. 깨끗한 테스트 환경에서 Monitoring VM stack과 App VM K3S stack을 시작
5. `bash scripts/healthcheck.sh`를 실행
6. `bash scripts/random-demo-traffic.sh`로 MSA 트래픽을 생성
7. Grafana datasource health, dashboard, logs, metrics, traces를 확인
