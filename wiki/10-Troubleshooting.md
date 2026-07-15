# 10. 트러블슈팅

## 10.1 Dashboard Has No Data

Symptom:

- Grafana dashboard는 열리지만 panel에 `No data`가 표시됩니다.

Root cause:

- App VM 트래픽이 생성되지 않았거나, Alloy가 Mimir/Loki/Tempo로 데이터를 보내지 못하고 있을 수 있습니다.

Fix:

- App VM에서 `./scripts/random-demo-traffic.sh`를 실행합니다.
- `up`과 `sum by (service) (rate(demo_app_requests_total[5m]))`를 조회합니다.
- App VM에서 `kubectl -n msa-demo logs daemonset/alloy --tail=100`으로 전송 오류를 확인합니다.
- `k3s/app-vm/configmap.yaml`의 `LOKI_PUSH_URL`, `MIMIR_REMOTE_WRITE_URL`, `ALLOY_OTLP_EXPORTER_ENDPOINT`가 Monitoring VM private IP를 가리키는지 확인합니다.

## 10.2 New App VM Is Running But Grafana Shows No App Metrics

Symptom:

- App VM에서 `kubectl -n msa-demo get pods,svc,daemonset`은 정상입니다.
- App VM local `/metrics` endpoint도 응답합니다.
- Grafana `MSA Overview` 또는 `VM Metrics`에서 App VM metric이 보이지 않습니다.

Root cause:

- Alloy가 App VM 내부 target scrape에는 성공하지만, Monitoring VM의 Mimir `9009/tcp`로 remote_write 하지 못하는 상태일 수 있습니다.
- 보안그룹에서 Monitoring VM `9009/tcp` inbound가 App VM private IP에 열려 있지 않거나, `MIMIR_REMOTE_WRITE_URL` 값이 잘못되었을 수 있습니다.

Check:

App VM에서 Monitoring VM Mimir ready endpoint를 확인합니다.

```bash
curl http://<monitoring-vm-private-ip>:9009/ready
```

Alloy 로그를 확인합니다.

```bash
kubectl -n msa-demo logs daemonset/alloy --tail=100
```

Fix:

- Monitoring VM 보안그룹에서 `9009/tcp`를 App VM private IP에 허용합니다.
- App VM의 `k3s/app-vm/configmap.yaml`에서 `MIMIR_REMOTE_WRITE_URL`을 수정합니다.
- K3S 리소스를 다시 적용하고 Alloy를 재시작합니다.

```bash
kubectl apply -k ./k3s/app-vm
kubectl -n msa-demo rollout restart daemonset/alloy
```

Grafana `MSA Overview`를 새로고침하고 `Service Up`이 `UP`으로 돌아오는지 확인합니다.

## 10.3 Alert Count Panel Changes When Time Range Is Expanded

Symptom:

- Grafana `Alerts Overview`에서 `App/MSA Firing Alert Count` 또는 `Backend Firing Alert Count`가 `Last 30 minutes`에서는 `OK`로 보입니다.
- 같은 패널이 `Last 90 days`처럼 긴 기간에서는 `1` 이상으로 표시됩니다.
- 실제 현재 장애는 없는데 과거 firing 이력이 현재 alert count처럼 보입니다.

Root cause:

- Alert count stat panel은 현재 시점의 firing alert 개수를 보여야 합니다.
- 하지만 query target이 range query로 설정되어 있으면 Grafana가 선택한 전체 시간 범위의 `ALERTS{alertstate="firing"}` series를 조회합니다.
- 이 경우 과거에 firing 되었던 alert sample이 stat reduce 과정에 포함되어 현재 firing count처럼 표시될 수 있습니다.

Check:

`grafana/dashboards/alerts-overview.json`에서 firing count panel target을 확인합니다.

```json
"instant": true,
"range": false
```

Timeline panel은 과거 이력을 보여야 하므로 `range: true`가 맞습니다.

Fix:

- 현재 상태를 나타내는 firing count stat panel은 instant query로 설정합니다.
- App/MSA와 Backend firing count panel 모두 다음 설정을 사용합니다.

```json
"instant": true,
"range": false
```

Monitoring VM에서 Grafana를 재시작해 provisioned dashboard를 다시 읽게 합니다.

```bash
docker compose restart grafana
```

Result:

- `Last 90 days`처럼 긴 시간 범위를 선택해도 firing count panel은 현재 시점의 firing alert 개수만 표시합니다.
- 과거 firing 이력은 `App/MSA Firing Timeline`, `Backend Firing Timeline`에서 확인합니다.
