# Alert Rules and Failure Scenarios

This project uses Prometheus alert rules under `configs/prometheus/rules`.
Grafana can visualize alert state through the `Alerts Overview` dashboard by querying the Prometheus `ALERTS` metric.

## Alert Rules

| Alert | Condition | Purpose |
| --- | --- | --- |
| `HighCpuUsage` | VM CPU usage above 80% for 5 minutes | VM resource saturation |
| `HighDiskUsage` | VM disk usage above 85% for 5 minutes | Storage capacity risk |
| `LokiTargetDown` | Loki scrape target down for 2 minutes | Log backend availability |
| `TempoTargetDown` | Tempo scrape target down for 2 minutes | Trace backend availability |
| `MimirTargetDown` | Mimir scrape target down for 2 minutes | Metric backend availability |
| `ObservabilityPipelineTargetDown` | Loki or Tempo scrape target down for 2 minutes | LGTM pipeline health |
| `MsaServiceDown` | Any `msa-demo` scrape target down for 1 minute | Demo service availability |
| `AppVmNodeExporterDown` | App VM Node Exporter down for 1 minute | App VM system metrics availability |
| `MsaHighErrorRate` | Non-metrics request 5xx ratio above 20% for 1 minute | Application error detection |
| `MsaHighLatencyP95` | Non-metrics request p95 latency above 1 second for 2 minutes | Application latency detection |

## Apply Rule Changes

On the Monitoring VM:

```bash
cd /home/ubuntu/lgtm-observability-stack
git pull
docker compose exec prometheus promtool check rules /etc/prometheus/rules/node-alerts.yml
docker compose restart prometheus
```

Grafana dashboard provisioning usually refreshes within 30 seconds.
If the `Alerts Overview` dashboard does not appear immediately:

```bash
docker compose restart grafana
```

## Scenario 1: MSA Service Down

Purpose: verify that Prometheus detects an unavailable App VM service.

On the App VM:

```bash
cd /home/ubuntu/lgtm-observability-stack
./scripts/fault-injection.sh payment-down
```

Expected result:

- In Grafana `MSA Overview`, `payment-service` changes to `DOWN`.
- In Grafana `Alerts Overview`, `MsaServiceDown` becomes pending and then firing after about 1 minute.

Recovery:

```bash
./scripts/fault-injection.sh payment-up
```

Expected recovery:

- `payment-service` returns to `UP`.
- `MsaServiceDown` clears after Prometheus scrapes the recovered target.

## Scenario 2: High Application Error Rate

Purpose: verify that repeated 5xx responses trigger an application error alert.

On the App VM:

```bash
cd /home/ubuntu/lgtm-observability-stack
./scripts/fault-injection.sh error-burst
```

Expected result:

- In Grafana `MSA Overview`, `Error Rate` increases for `api-service`.
- In Grafana `Logs Overview`, `Recent Errors` shows `intentional demo error`.
- In Grafana `Alerts Overview`, `MsaHighErrorRate` becomes pending and then firing after about 1 minute.

Recovery:

- Stop sending `/error` requests.
- Generate normal requests if needed:

```bash
./scripts/random-demo-traffic.sh
```

Expected recovery:

- Error rate drops as the 5-minute window moves past the test traffic.
- `MsaHighErrorRate` clears automatically.

## Scenario 3: App VM Metrics Collection Down

Purpose: verify that VM-level metric collection failure is detected.

On the App VM:

```bash
cd /home/ubuntu/lgtm-observability-stack
./scripts/fault-injection.sh node-exporter-down
```

Expected result:

- In Grafana `VM Metrics`, App VM resource charts stop receiving fresh samples.
- In Grafana `Alerts Overview`, `AppVmNodeExporterDown` becomes pending and then firing after about 1 minute.

Recovery:

```bash
./scripts/fault-injection.sh node-exporter-up
```

Expected recovery:

- App VM resource metrics resume.
- `AppVmNodeExporterDown` clears after Prometheus scrapes the recovered target.

## Scenario 4: Observability Backend Down

Purpose: verify that LGTM backend target failures are detected.

On the Monitoring VM:

```bash
cd /home/ubuntu/lgtm-observability-stack
./scripts/fault-injection.sh loki-down
```

Expected result:

- `LokiTargetDown` becomes pending and then firing after about 2 minutes.
- Log ingestion and LogQL queries are unavailable while Loki is stopped.

Recovery:

```bash
./scripts/fault-injection.sh loki-up
```

Expected recovery:

- Loki returns to ready state.
- `LokiTargetDown` clears after Prometheus scrapes the recovered target.

## Recovery Helper

If a test leaves multiple containers stopped, use:

```bash
./scripts/fault-injection.sh recover-all
```

Run it on the VM where the failure was injected.
