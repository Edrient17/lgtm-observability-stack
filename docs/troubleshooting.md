# Troubleshooting

이 파일은 실제 구축 과정의 증상, 원인, 조치, 결과를 정리하는 기록용 문서

## Case 1: Demo Service Exits With Missing `pkg_resources`

- Symptom:
  - App VM service가 시작 직후 `ModuleNotFoundError: No module named 'pkg_resources'` 오류로 종료된다.
- Root cause:
  - `python:3.12-slim`에는 기본적으로 `setuptools`가 포함되지 않는데, OpenTelemetry instrumentation이 `pkg_resources`를 import 하기 때문에 발생한다.
- Fix:
  - `msa-demo/requirements.txt`에 `setuptools`를 추가
  - `./scripts/k3s-load-demo-image.sh`로 이미지를 다시 빌드하고 k3s containerd에 import
  - `kubectl -n msa-demo rollout restart deployment`로 demo MSA pod를 재시작

## Case 2: Dashboard Has No Data

- Symptom:
  - Grafana dashboard는 열리지만 panel에 `No data`가 표시됨.
- Root cause:
  - App VM 트래픽이 생성되지 않았거나, Alloy가 Mimir/Loki/OTel Collector로 데이터를 보내지 못하고 있을 수 있음.
- Fix:
  - App VM에서 `./scripts/random-demo-traffic.sh`를 실행
  - `up`과 `sum by (service) (rate(demo_app_requests_total[5m]))`를 조회
  - App VM에서 `kubectl -n msa-demo logs daemonset/alloy --tail=100`으로 전송 오류를 확인
  - `k3s/app-vm/configmap.yaml`의 `LOKI_PUSH_URL`, `MIMIR_REMOTE_WRITE_URL`, `ALLOY_OTLP_EXPORTER_ENDPOINT`가 Monitoring VM private IP를 가리키는지 확인

## Case 3: New App VM Is Running But Grafana Shows No App Metrics

- Symptom:
  - App VM에서 `kubectl -n msa-demo get pods,svc,daemonset`은 정상이다.
  - App VM local `/metrics` endpoint도 응답한다.
  - Grafana `MSA Overview` 또는 `VM Metrics`에서 App VM metric이 보이지 않는다.
- Root cause:
  - Alloy가 App VM 내부 target scrape에는 성공하지만, Monitoring VM의 Mimir `9009/tcp`로 remote_write 하지 못하는 상태일 수 있다.
  - 보안그룹에서 Monitoring VM `9009/tcp` inbound가 App VM private IP에 열려 있지 않거나, `MIMIR_REMOTE_WRITE_URL` 값이 잘못되었을 수 있다.
- Check:
  - App VM에서 Monitoring VM Mimir ready endpoint를 확인한다.

    ```bash
    curl http://<monitoring-vm-private-ip>:9009/ready
    ```

  - Alloy 로그를 확인한다.

    ```bash
    kubectl -n msa-demo logs daemonset/alloy --tail=100
    ```
- Fix:
  - Monitoring VM 보안그룹에서 `9009/tcp`를 App VM private IP에 허용한다.
  - App VM의 `k3s/app-vm/configmap.yaml`에서 `MIMIR_REMOTE_WRITE_URL`을 수정한다.
  - K3S 리소스를 다시 적용하고 Alloy를 재시작한다.

    ```bash
    kubectl apply -k ./k3s/app-vm
    kubectl -n msa-demo rollout restart daemonset/alloy
    ```
  - Grafana `MSA Overview`를 새로고침하고 `Service Up`이 `UP`으로 돌아오는지 확인한다.

## Case 4: MSA Dashboard Shows Duplicated App Metrics

- Symptom:
  - Grafana `MSA Overview`에서 `Service Up` 행이 비정상적으로 많이 표시된다.
  - `Scrape Request Rate` 또는 App request graph가 동일한 series가 여러 번 겹쳐 보인다.
  - PromQL 결과에 `replica="prometheus-1"`가 붙은 App metric series가 함께 보인다.
- Root cause:
  - App VM metric은 Alloy가 Mimir로 `remote_write` 한다.
  - App/MSA alert 평가를 위해 Prometheus가 Mimir의 `/prometheus/federate`에서 App metric을 가져온다.
  - 이때 Prometheus가 federation으로 가져온 App metric까지 다시 Mimir로 `remote_write`하면 Mimir 안에 동일 App metric이 중복 저장된다.
- Check:
  - Grafana Explore에서 Mimir datasource로 다음을 조회한다.

    ```promql
    up{job="msa-demo"}
    ```

  - 결과에 원본 series와 함께 `replica="prometheus-1"`가 붙은 series가 보이면 Prometheus가 federated App metric을 재적재한 상태다.
  - Prometheus 설정에서 `app-metrics-from-mimir` scrape job과 `remote_write.write_relabel_configs`를 확인한다.

    ```bash
    docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
    ```
- Fix:
  - Prometheus `remote_write`에 App metric 재적재 방지 rule을 둔다.

    ```yaml
    remote_write:
      - url: http://mimir:9009/api/v1/push
        write_relabel_configs:
          - source_labels:
              - job
            regex: msa-demo
            action: drop
          - source_labels:
              - job
              - instance
            separator: ;
            regex: node-exporter;app-vm
            action: drop
    ```

  - Mimir federation으로 가져온 재적재본은 Prometheus 내부 alert 평가에만 사용하고, 다시 Mimir로 쓰지 않는다.
  - 대시보드 쿼리에는 필요 시 `replica!="prometheus-1"` 조건을 추가해 기존 중복 sample의 영향을 줄인다.

    ```promql
    up{job="msa-demo", replica!="prometheus-1"}
    ```

  - Monitoring VM에서 Prometheus와 Grafana를 재적용한다.

    ```bash
    docker compose up -d prometheus grafana
    docker compose restart prometheus grafana
    ```
- Note:
  - 이미 Mimir에 저장된 중복 series는 retention 기간 동안 남을 수 있다.
  - 수정 직후에는 Grafana 시간 범위를 `Last 5 minutes`로 줄여 새로 들어오는 sample 기준으로 정상화 여부를 확인한다.
