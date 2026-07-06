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
