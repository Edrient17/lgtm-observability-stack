# 9. 장애 테스트

## 9.1 App/MSA 장애 테스트

`catalog-service`를 중단합니다.

```bash
kubectl -n msa-demo scale deployment catalog-service --replicas=0
```

복구합니다.

```bash
kubectl -n msa-demo scale deployment catalog-service --replicas=1
```

기대 결과:

| 관측 대상 | 기대 결과 |
| --- | --- |
| MSA Overview | `catalog-service scrape DOWN` 표시 |
| Alerts Overview | `MsaServiceDown` pending 후 firing 전환 |
| Slack | firing 및 resolved 알림 수신 |
| Logs Overview | downstream 호출 실패 로그 확인 |
| Traces Overview | checkout trace에서 catalog-service 호출 실패 확인 |

## 9.2 Monitoring backend 장애 테스트

Loki를 중단합니다.

```bash
docker compose stop loki
```

복구합니다.

```bash
docker compose start loki
```

기대 결과:

| 관측 대상 | 기대 결과 |
| --- | --- |
| Alerts Overview | `LokiTargetDown` backend firing 표시 |
| Slack | Loki backend 장애 알림 수신 |
| Logs Overview | Loki 중단 중 로그 조회 실패 또는 지연 |

## 9.3 장애 테스트 증빙 이미지

### 9.3.1 catalog-service 장애 테스트

(1) catalog-service 중단 전 정상 상태 (MSA Overview 대시보드)

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_1/catalog_service_down_before.png" width="800" />

(2) Alert Overview 경고 표시 및 Slack으로 MsaServiceDown firing 알림 수신

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_1/catalog_service_down_Alerts_Overview.png" width="800" />

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_1/catalog_service_down_slack.png" width="800" />

(3) catalog-service 중단 후 MSA Overview에서 DOWN 표시

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_1/catalog_service_down_MSA_Overview.png" width="800" />

(4) Logs Overview에서 downstream 호출 실패 로그 확인

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_1/catalog_service_down_logs.png" width="800" />

(5) Traces Overview에서 checkout trace에서 catalog-service 호출 실패 확인

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_1/catalog_service_down_traces.png" width="800" />

(6) catalog-service 복구 후 MSA Overview에서 UP 표시

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_1/catalog_service_down_resolved.png" width="800" />

(7) Slack으로 MsaServiceDown resolved 알림 수신

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_1/catalog_service_down_slack_resolved.png" width="800" />

### 9.3.2 Loki 장애 테스트

(1) Loki 중단 전 정상 상태 (Alerts Overview 대시보드)

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_2/loki_down_before.png" width="800" />

(2) Loki 중단 후 Alerts Overview에서 firing 표시

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_2/loki_down_firing.png" width="800" />

(3) Slack으로 LokiTargetDown firing 알림 수신

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_2/loki_down_slack.png" width="800" />

(4) Logs Overview에서 Loki 중단 중 로그 조회 실패

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_2/loki_down_logs.png" width="800" />

(5) Loki 복구 후 Alerts Overview에서 resolved 표시

<img src="https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/fault-tests_2/loki_down_resolved.png" width="800" />
