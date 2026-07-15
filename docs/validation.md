# Validation Checklist

## Monitoring VM

- [ ] `.env`를 `.env.example`에서 생성
- [ ] `docker compose up -d`가 정상 완료된다.
- [ ] `docker compose ps`에서 Grafana, Loki, Mimir, Tempo, Prometheus, Alertmanager, MinIO, Node Exporter가 실행 중이다.
- [ ] Grafana가 `http://<monitoring-vm-public-ip>:3000`에서 접속된다.

## App VM

- [ ] App VM에 K3S가 설치되어 있고 `kubectl get nodes`가 정상이다.
- [ ] `k3s/app-vm/configmap.yaml`의 Monitoring VM private IP가 올바르다.
- [ ] `./scripts/k3s-load-demo-image.sh`로 `msa-demo:local` 이미지를 k3s containerd에 import했다.
- [ ] `kubectl apply -k ./k3s/app-vm`가 정상 완료된다.
- [ ] `kubectl -n msa-demo get pods,svc,daemonset`에서 demo MSA, Alloy, Node Exporter가 실행 중이다.

## Connectivity

Monitoring VM에서 확인

- [ ] `curl http://localhost:3100/ready`가 성공
- [ ] `curl http://localhost:9009/ready`가 성공
- [ ] `curl http://localhost:3200/ready`가 성공

App VM에서 확인

- [ ] `curl http://<monitoring-vm-private-ip>:3100/ready`가 최종적으로 `ready`를 반환한다.
- [ ] `curl http://<monitoring-vm-private-ip>:9009/ready`가 성공한다.
- [ ] `timeout 3 bash -c '</dev/tcp/<monitoring-vm-private-ip>/4317'`가 성공한다.
- [ ] `kubectl -n msa-demo logs daemonset/alloy --tail=100`에서 Loki, Mimir, Tempo 전송 오류가 없다.

## Logs

- [ ] Grafana에서 Loki datasource가 healthy 상태이다.
- [ ] `{job="k3s-pods", host=~"app-vm-.*"}` 쿼리로 App 로그가 조회된다.
- [ ] 로그에 `service`, `trace_id`, `span_id` 필드가 포함된다.
- [ ] 정상 트래픽 생성 시 App 로그가 지속적으로 수집된다.

## Metrics

- [ ] Grafana에서 Mimir datasource가 healthy 상태이다.
- [ ] Grafana의 Mimir datasource type은 `Prometheus`, URL은 `http://mimir:9009/prometheus`이다.
- [ ] App VM Alloy의 `prometheus.scrape` component는 `prometheus.remote_write.mimir.receiver`로 metric을 전달한다.
- [ ] App VM의 `MIMIR_REMOTE_WRITE_URL`은 `http://<monitoring-vm-private-ip>:9009/api/v1/push`이다.
- [ ] `up` 쿼리에서 Monitoring VM과 App VM target이 표시된다.
- [ ] `sum by (service) (rate(demo_app_requests_total[5m]))`에서 활성 MSA 서비스 트래픽이 표시된다.
- [ ] VM Metrics dashboard에서 CPU, memory, disk, network panel이 표시된다.

## Traces

- [ ] Grafana에서 Tempo datasource가 healthy 상태이다.
- [ ] App VM에서 `curl http://localhost:8080/browse` 요청 시 trace가 생성된다.
- [ ] App VM에서 `curl http://localhost:8080/cart/add` 요청 시 trace가 생성된다.
- [ ] App VM에서 `curl http://localhost:8080/checkout` 요청 시 trace가 생성된다.
- [ ] Grafana Explore에서 `{ resource.service.name = "api-service" }`로 trace가 조회된다.
- [ ] Browse trace에서 `api-service -> catalog-service -> inventory-service` 흐름이 보인다.
- [ ] Checkout trace에서 `api-service -> cart-service/order-service -> inventory-service/payment-service` 흐름이 보인다.

## Long-Running Observation

- [ ] App VM에서 `scripts/random-demo-traffic.sh`를 수동 실행할 수 있다.
- [ ] 여러 날 관찰을 위한 cron이 등록되어 있다.
- [ ] `logs/random-demo-traffic.log`에 `/browse`, `/cart/add`, `/checkout`, `/work` 요청이 기록된다.
- [ ] 장애 테스트는 정상 트래픽을 흘려둔 상태에서 K3S 리소스 또는 Monitoring backend 컴포넌트를 중단하고 복구하는 방식으로 수행한다.

## Alerts

- [ ] Monitoring VM `.env`에 `SLACK_WEBHOOK_URL`이 설정되어 있다.
- [ ] Prometheus가 `configs/prometheus/rules/backend-alerts.yml`을 로드한다.
- [ ] Mimir Ruler가 `configs/mimir/rules/app-alerts.yml`을 로드한다.
- [ ] Alertmanager가 실행 중이며 Slack 알림을 전송할 수 있다.
- [ ] backend alert 대상은 Grafana, Loki, Mimir, Tempo, Alertmanager, Monitoring VM Node Exporter, Monitoring VM CPU/Disk 사용률이다.
- [ ] App alert 대상은 MSA service up, App VM Node Exporter, App metric missing, 장애 상황의 latency p95, App VM CPU/Disk 사용률이다.
- [ ] `MonitoringVmHighCpuUsage`, `MonitoringVmHighDiskUsage`, `AppVmHighCpuUsage`, `AppVmHighDiskUsage` rule이 로드되어 있다.
- [ ] Mimir datasource에서 `ALERTS`와 `up{job="msa-demo"}` 쿼리로 App/MSA alert 상태를 확인할 수 있다.
