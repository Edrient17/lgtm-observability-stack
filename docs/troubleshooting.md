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
