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
  - App VM 트래픽이 생성되지 않았거나, Prometheus target이 down 상태이거나, Mimir remote write가 아직 준비되지 않았을 수 있음.
- Fix:
  - App VM에서 `./scripts/random-demo-traffic.sh`를 실행
  - `up`과 `sum by (service) (rate(demo_app_requests_total[5m]))`를 조회
  - Grafana Explore 또는 Prometheus UI에서 Prometheus target 상태를 확인

## Case 3: New App VM Metrics Are Reachable But Grafana Shows Services Down

- Symptom:
  - Monitoring VM host에서 `curl http://<new-app-vm-private-ip>:8080/metrics`는 성공한다.
  - Grafana `MSA Overview`의 `Service Up` panel에서는 `api-service`, `cart-service`, `catalog-service`, `inventory-service`, `order-service`, `payment-service`가 모두 `DOWN`으로 표시된다.
  - Prometheus/Grafana dashboard에는 이전 App VM target 상태가 남아 있는 것처럼 보인다.
- Root cause:
  - 새 App VM으로 교체하면서 Monitoring VM의 `.env`에 있는 `APP_VM_PRIVATE_IP`를 수정했지만, Prometheus container가 재생성되지 않아 `extra_hosts`의 `app-vm` 매핑이 예전 private IP를 계속 사용했다.
  - Docker Compose `extra_hosts` 값은 container 생성 시점에 `/etc/hosts`에 반영되므로 단순 `docker compose restart prometheus`만으로는 새 IP가 반영되지 않을 수 있다.
- Check:
  - Monitoring VM host에서 새 App VM endpoint 접근을 확인한다.

    ```bash
    curl http://<new-app-vm-private-ip>:8080/metrics
    curl http://<new-app-vm-private-ip>:9100/metrics
    ```

  - Prometheus container 내부의 `app-vm` 해석 결과를 확인한다.

    ```bash
    docker compose exec prometheus getent hosts app-vm
    ```

  - 출력 IP가 새 App VM private IP와 다르면 Prometheus container가 예전 `extra_hosts` 값을 보고 있는 상태다.
- Fix:
  - Monitoring VM의 `.env`에서 `APP_VM_PRIVATE_IP`를 새 App VM private IP로 수정한다.
  - Prometheus container를 강제로 재생성한다.

    ```bash
    docker compose up -d --force-recreate prometheus
    ```

  - Prometheus container 내부에서 새 App VM target 접근을 확인한다.

    ```bash
    docker compose exec prometheus getent hosts app-vm
    docker compose exec prometheus wget -qO- http://app-vm:8080/metrics | head
    ```

  - Grafana `MSA Overview`를 새로고침하고 `Service Up`이 `UP`으로 돌아오는지 확인한다.
