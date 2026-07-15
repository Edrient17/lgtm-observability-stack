# 6. 주요 설정

## 6.1 주요 파일

| 파일 | 설명 |
| --- | --- |
| `docker-compose.yml` | Monitoring VM에서 실행되는 LGTM backend stack 정의 |
| `.env.example` | Monitoring VM 환경 변수 예시 |
| `configs/loki/loki-config.yaml` | Loki 로그 저장 및 retention 설정 |
| `configs/mimir/mimir-config.yaml` | Mimir metric 저장소, ruler, MinIO 연동 설정 |
| `configs/mimir/rules/app-alerts.yml` | Mimir Ruler가 평가하는 App/MSA 및 App VM CPU/Disk alert rule |
| `configs/tempo/tempo-config.yaml` | Tempo trace 저장 및 MinIO 연동 설정 |
| `configs/prometheus/prometheus.yml` | Monitoring VM backend scrape 및 backend alert 설정 |
| `configs/prometheus/rules/backend-alerts.yml` | Prometheus가 평가하는 Monitoring backend 및 Monitoring VM CPU/Disk alert rule |
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

## 6.2 주요 환경 변수

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

## 6.3 App VM ConfigMap 주요 값

| Key | 의미 |
| --- | --- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | MSA 서비스가 trace를 보낼 Alloy OTLP endpoint |
| `ALLOY_OTLP_EXPORTER_ENDPOINT` | Alloy가 trace를 전달할 Monitoring VM OTel Collector 주소 |
| `MIMIR_REMOTE_WRITE_URL` | Alloy `prometheus.remote_write`가 사용할 Mimir endpoint |
| `LOKI_PUSH_URL` | Alloy가 log를 push할 Loki 주소 |
| `APP_HOST_LABEL` | App VM metric/log label. VM마다 `app-vm-1`, `app-vm-2`처럼 유니크하게 지정 |
| `LOG_LEVEL` | MSA 서비스 로그 레벨 |
