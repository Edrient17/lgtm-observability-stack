# Alert Rules and Failure Scenarios

이 프로젝트는 `configs/prometheus/rules` 아래의 Prometheus alert rule을 사용한다.
Grafana에서는 Prometheus의 `ALERTS` 메트릭을 조회해 `Alerts Overview` 대시보드에서 alert 상태를 확인할 수 있다.
Slack 알림은 Prometheus가 Alertmanager로 alert를 전달하고, Alertmanager가 Slack Incoming Webhook으로 전송하는 방식으로 처리한다.

## Alert Rules

| Alert | Condition | Purpose |
| --- | --- | --- |
| `HighCpuUsage` | VM CPU 사용률이 5분 동안 80% 초과 | VM 리소스 포화 감지 |
| `HighDiskUsage` | VM disk 사용률이 5분 동안 85% 초과 | 디스크 용량 위험 감지 |
| `LokiTargetDown` | Loki scrape target이 2분 동안 down | 로그 backend 가용성 확인 |
| `TempoTargetDown` | Tempo scrape target이 2분 동안 down | 트레이스 backend 가용성 확인 |
| `MimirTargetDown` | Mimir scrape target이 2분 동안 down | 메트릭 backend 가용성 확인 |
| `AlertmanagerTargetDown` | Alertmanager scrape target이 2분 동안 down | Slack 알림 전달 경로 확인 |
| `ObservabilityPipelineTargetDown` | Loki 또는 Tempo scrape target이 2분 동안 down | LGTM pipeline 상태 확인 |
| `MsaServiceDown` | `msa-demo` scrape target 중 하나가 1분 동안 down | 데모 서비스 가용성 확인 |
| `AppVmNodeExporterDown` | App VM Node Exporter가 1분 동안 down | App VM 시스템 메트릭 수집 상태 확인 |
| `MsaHighErrorRate` | non-metrics 요청의 5xx 비율이 1분 동안 20% 초과 | 애플리케이션 오류율 증가 감지 |
| `MsaHighLatencyP95` | non-metrics 요청의 p95 latency가 2분 동안 1초 초과 | 애플리케이션 지연 증가 감지 |

## Apply Rule Changes

Monitoring VM에서 실행한다.

```bash
cd /home/ubuntu/lgtm-observability-stack
git pull
docker compose exec prometheus promtool check rules /etc/prometheus/rules/node-alerts.yml
docker compose up -d alertmanager
docker compose restart prometheus
```

Grafana dashboard provisioning은 보통 30초 안에 갱신된다.
`Alerts Overview` 대시보드가 바로 보이지 않으면 Grafana를 재시작한다.

```bash
docker compose restart grafana
```

## Slack Notification Setup

Monitoring VM의 `.env`에 Slack Incoming Webhook URL을 설정한다.

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Alertmanager 설정을 확인한다.

```bash
docker compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
docker compose logs alertmanager --tail=50
```

Slack 알림 흐름은 다음과 같다.

```text
Prometheus alert rule
-> Alertmanager
-> Slack Incoming Webhook
-> Slack channel
```

## Scenario 1: MSA Service Down

Purpose: Prometheus가 사용할 수 없는 App VM 서비스를 감지하는지 확인한다.

App VM에서 실행한다.

```bash
cd /home/ubuntu/lgtm-observability-stack
./scripts/k3s-fault-injection.sh payment-down
```

Expected result:

- Grafana `MSA Overview`에서 `payment-service`가 `DOWN`으로 변경된다.
- Grafana `Alerts Overview`에서 `MsaServiceDown`이 약 1분 후 pending 상태를 거쳐 firing 상태가 된다.
- Slack 채널에 `MsaServiceDown` firing 알림이 전송된다.

Recovery:

```bash
./scripts/k3s-fault-injection.sh payment-up
```

Expected recovery:

- `payment-service`가 `UP`으로 돌아온다.
- Prometheus가 복구된 target을 다시 scrape하면 `MsaServiceDown`이 해제된다.
- Slack 채널에 resolved 알림이 전송된다.

## Scenario 2: High Application Error Rate

Purpose: 반복적인 5xx 응답이 애플리케이션 오류율 alert를 발생시키는지 확인한다.

App VM에서 실행한다.

```bash
cd /home/ubuntu/lgtm-observability-stack
./scripts/k3s-fault-injection.sh error-burst
```

Expected result:

- Grafana `MSA Overview`에서 `api-service`의 `Error Rate`가 증가한다.
- Grafana `Logs Overview`의 `Recent Errors`에 `intentional demo error` 로그가 표시된다.
- Grafana `Alerts Overview`에서 `MsaHighErrorRate`가 약 1분 후 pending 상태를 거쳐 firing 상태가 된다.

Recovery:

- `/error` 요청 전송을 중단한다.
- 필요하면 정상 요청을 다시 생성한다.

```bash
./scripts/random-demo-traffic.sh
```

Expected recovery:

- 5분 집계 구간에서 테스트 트래픽이 밀려나면서 error rate가 감소한다.
- `MsaHighErrorRate`는 자동으로 해제된다.

## Scenario 3: App VM Metrics Collection Down

Purpose: VM 레벨 메트릭 수집 장애가 감지되는지 확인한다.

App VM에서 실행한다.

```bash
cd /home/ubuntu/lgtm-observability-stack
./scripts/k3s-fault-injection.sh node-exporter-down
```

Expected result:

- Grafana `VM Metrics`에서 App VM 리소스 chart의 신규 sample 수집이 중단된다.
- Grafana `Alerts Overview`에서 `AppVmNodeExporterDown`이 약 1분 후 pending 상태를 거쳐 firing 상태가 된다.

Recovery:

```bash
./scripts/k3s-fault-injection.sh node-exporter-up
```

Expected recovery:

- App VM 리소스 메트릭 수집이 재개된다.
- Prometheus가 복구된 target을 다시 scrape하면 `AppVmNodeExporterDown`이 해제된다.

## Scenario 4: Observability Backend Down

Purpose: LGTM backend target 장애가 감지되는지 확인한다.

Monitoring VM에서 실행한다.

```bash
cd /home/ubuntu/lgtm-observability-stack
docker compose stop loki
```

Expected result:

- `LokiTargetDown`이 약 2분 후 pending 상태를 거쳐 firing 상태가 된다.
- Loki가 중지된 동안 로그 수집과 LogQL 조회가 불가능하다.

Recovery:

```bash
docker compose start loki
```

Expected recovery:

- Loki가 ready 상태로 돌아온다.
- Prometheus가 복구된 target을 다시 scrape하면 `LokiTargetDown`이 해제된다.

## Recovery Helper

테스트 후 App VM K3S 리소스가 중지된 상태로 남아 있으면 아래 명령을 사용한다.

```bash
./scripts/k3s-fault-injection.sh recover-all
```

App VM에서 실행한다.
