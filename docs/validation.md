# Validation Checklist

## Compose

- [ ] `docker compose up -d --build` completes.
- [ ] `docker compose ps` shows all services running or completed successfully for `minio-init`.
- [ ] Grafana is reachable on port `3000`.

## Logs

- [ ] Loki datasource is healthy in Grafana.
- [ ] `Logs Overview` dashboard loads.
- [ ] `{job="docker"} |= "demo-app"` returns logs.
- [ ] A log line with `trace_id` links to Tempo.

## Metrics

- [ ] Prometheus target page shows core targets as up.
- [ ] Mimir datasource is healthy in Grafana.
- [ ] `VM Metrics` dashboard shows CPU, memory, and disk panels.
- [ ] `rate(demo_app_requests_total[5m])` returns samples from Mimir.

## Traces

- [ ] Tempo datasource is healthy in Grafana.
- [ ] `Traces Overview` dashboard loads.
- [ ] `{ resource.service.name = "demo-app" }` returns traces after running `bash scripts/generate-load.sh`.
- [ ] Span metrics appear in Mimir after traces are generated.

## Alerts

- [ ] `HighCpuUsage` rule exists.
- [ ] `HighDiskUsage` rule exists.
- [ ] At least one contact point send-test screenshot is captured for the final report.
