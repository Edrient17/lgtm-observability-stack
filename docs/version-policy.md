# Version Policy

This project pins container image tags instead of using `latest`.

## Strategy

- Prefer stable patch releases over floating tags.
- Avoid brand-new major lines during the project window unless a feature requires them.
- Keep tightly coupled components on compatible lines.
- Record any version upgrade in this file and re-run validation afterwards.

## Pinned Versions

| Component | Image | Version | Reason |
| --- | --- | --- | --- |
| Grafana | `grafana/grafana-oss` | `12.4.3` | Uses the mature Grafana 12 line instead of the newer Grafana 13 major line. |
| Loki | `grafana/loki` | `3.6.11` | Stable 3.6 line, aligned with Promtail. |
| Promtail | `grafana/promtail` | `3.6.11` | Same release line as Loki for log pipeline compatibility. |
| Mimir | `grafana/mimir` | `3.1.2` | Current stable patch release in the Mimir 3 line. |
| Tempo | `grafana/tempo` | `2.10.7` | Avoids the newer Tempo 3 major line while keeping recent OTLP/TraceQL support. |
| Prometheus | `prom/prometheus` | `v3.5.4` | Stable Prometheus 3 release branch observed in registry tags. |
| Node Exporter | `prom/node-exporter` | `v1.11.1` | Current stable node-exporter release. |
| OpenTelemetry Collector Contrib | `otel/opentelemetry-collector-contrib` | `0.155.0` | Stable collector release tag. |
| MinIO | `quay.io/minio/minio` | `RELEASE.2025-09-07T16-13-09Z` | Fixed MinIO server release tag. |
| MinIO Client | `quay.io/minio/mc` | `RELEASE.2025-08-13T08-35-41Z` | Fixed client release tag for bucket initialization. |

## Upgrade Rule

Upgrade one component family at a time:

1. Update `.env.example` and the fallback tag in `docker-compose.yml`.
2. Run `docker compose config`.
3. Start the stack in a clean environment.
4. Run `bash scripts/healthcheck.sh`.
5. Generate traffic with `bash scripts/generate-load.sh`.
6. Check Grafana datasource health and dashboards.

