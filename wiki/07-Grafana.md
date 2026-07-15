# 7. Grafana

## 7.1 Dashboard

Grafana dashboard는 `grafana/dashboards` 디렉터리의 JSON 파일로 자동 provision됩니다.

| Dashboard | 설명 |
| --- | --- |
| `MSA Overview` | MSA service scrape status, request rate, latency, HTTP status, error rate 확인 |
| `Logs Overview` | 서비스별 로그량, 레벨별 로그량, 최근 오류 로그 확인 |
| `Traces Overview` | trace 검색, entry/downstream span call rate, span latency 확인 |
| `VM Metrics` | Monitoring VM과 App VM의 CPU, memory, disk, network 확인 |
| `Alerts Overview` | App/MSA alert와 Monitoring backend alert 상태 확인 |

### 대시보드 스크린샷

MSA Overview:

![MSA Overview](https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/dashboards/msa_overview.png)

Logs Overview:

![Logs Overview](https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/dashboards/logs_overview.png)

Traces Overview:

![Traces Overview](https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/dashboards/traces_overview.png)

VM Metrics:

![VM Metrics](https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/dashboards/vm_metrics.png)

Alerts Overview:

![Alerts Overview](https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/dashboards/alerts_overview.png)

## 7.2 Alert Rules

Alert rule은 Monitoring VM backend alert와 App/MSA alert로 나누어 관리합니다.

| 파일 | 평가 주체 | 주요 Alert |
| --- | --- | --- |
| `configs/prometheus/rules/backend-alerts.yml` | Prometheus | `LokiTargetDown`, `MimirTargetDown`, `TempoTargetDown`, `GrafanaTargetDown`, `AlertmanagerTargetDown`, `MonitoringNodeExporterDown`, `MonitoringVmHighCpuUsage`, `MonitoringVmHighDiskUsage` |
| `configs/mimir/rules/app-alerts.yml` | Mimir Ruler | `AppMetricsMissing`, `MsaServiceDown`, `AppVmNodeExporterDown`, `MsaHighLatencyP95`, `AppVmHighCpuUsage`, `AppVmHighDiskUsage` |

## 7.3 Grafana Explore 유용한 쿼리

### 7.3.1 PromQL

| PromQL | 설명 |
| --- | --- |
| `up` | Monitoring VM backend metric scrape 상태 확인 |
| `up{job="msa-demo"}` | App VM metric scrape 상태 확인 |
| `sum by (service) (rate(demo_app_requests_total[5m]))` | App VM MSA 서비스별 request rate 확인 |
| `sum by (service, status) (rate(demo_app_requests_total{endpoint!="metrics"}[5m]))` | App VM MSA 서비스별 HTTP status code 확인 |
| `histogram_quantile(0.95, sum by (le, service) (rate(demo_app_request_duration_seconds_bucket[5m])))` | App VM MSA 서비스별 95th percentile latency 확인 |
| `ALERTS` | 현재 firing alert 확인 |

### 7.3.2 LogQL

| LogQL | 설명 |
| --- | --- |
| `{job="k3s-pods", host=~"app-vm-.*"}` | 전체 App VM K3S Pod 로그 확인 |
| `{job="k3s-pods", host="app-vm-1", level="ERROR"}` | 특정 App VM K3S Pod ERROR 로그 확인 |
| `{job="k3s-pods", host="app-vm-1", service="api-service"}` | 특정 App VM의 api-service 로그 확인 |

### 7.3.3 TraceQL

| TraceQL | 설명 |
| --- | --- |
| `{ resource.service.name = "api-service" }` | api-service 관련 trace 확인 |
| `{ resource.service.name = "api-service" \|\| resource.service.name = "cart-service" \|\| resource.service.name = "order-service" }` | api-service, cart-service, order-service 관련 trace 확인 |
