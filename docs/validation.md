# Validation Checklist

## Monitoring VM

- [ ] `.env`를 `.env.monitoring.example`에서 생성
- [ ] `APP_VM_PRIVATE_IP`가 App VM private IP를 가리킨다.
- [ ] `docker compose up -d`가 정상 완료된다.
- [ ] `docker compose ps`에서 Grafana, Loki, Mimir, Tempo, Prometheus, OTel Collector, MinIO, Node Exporter가 실행 중이다.
- [ ] Grafana가 `http://<monitoring-vm-public-ip>:3000`에서 접속된다.

## App VM

- [ ] `.env`를 `.env.app.example`에서 생성한다.
- [ ] `MONITORING_VM_PRIVATE_IP`가 Monitoring VM private IP를 가리킨다.
- [ ] `docker compose up -d --build`가 정상 완료된다.
- [ ] `docker compose ps`에서 `api-service`, `catalog-service`, `inventory-service`, `cart-service`, `order-service`, `payment-service`, `promtail`, `node-exporter`가 실행 중이다.

## Connectivity

Monitoring VM에서 확인

- [ ] `curl http://<app-vm-private-ip>:8080/metrics`가 성공
- [ ] `curl http://<app-vm-private-ip>:8081/metrics`가 성공
- [ ] `curl http://<app-vm-private-ip>:8082/metrics`가 성공
- [ ] `curl http://<app-vm-private-ip>:8083/metrics`가 성공
- [ ] `curl http://<app-vm-private-ip>:8084/metrics`가 성공
- [ ] `curl http://<app-vm-private-ip>:8085/metrics`가 성공
- [ ] `curl http://<app-vm-private-ip>:9100/metrics`가 성공

App VM에서 확인

- [ ] `curl http://<monitoring-vm-private-ip>:3100/ready`가 최종적으로 `ready`를 반환한다.
- [ ] `curl http://<monitoring-vm-private-ip>:4318/`가 `404 page not found` 같은 HTTP 응답을 반환한다.

## Logs

- [ ] Grafana에서 Loki datasource가 healthy 상태이다.
- [ ] `{job="docker", host="app-vm"}` 쿼리로 App 컨테이너 로그가 조회된다.
- [ ] 로그에 `service`, `trace_id`, `span_id` 필드가 포함된다.
- [ ] `/checkout` 트래픽 이후 `payment-service` 오류 로그를 확인할 수 있다.

## Metrics

- [ ] Grafana에서 Mimir datasource가 healthy 상태이다.
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
- [ ] 오류율 테스트가 필요할 때 `./scripts/fault-injection.sh error-burst`로 `/error` 요청을 별도 생성할 수 있다.

## Alerts

- [ ] Prometheus가 `configs/prometheus/rules/node-alerts.yml`을 로드한다.
- [ ] Alertmanager가 실행 중이며 `.env`의 `SLACK_WEBHOOK_URL`을 사용한다.
- [ ] Grafana에서 `Alerts Overview` 대시보드가 표시된다.
- [ ] App VM 서비스 하나를 약 1분 동안 중지하면 `MsaServiceDown`이 firing 상태가 된다.
- [ ] `MsaServiceDown` firing 알림이 Slack 채널에 전송된다.
- [ ] `/error` 요청을 반복 생성하면 `MsaHighErrorRate`가 firing 상태가 된다.
- [ ] App VM Node Exporter를 약 1분 동안 중지하면 `AppVmNodeExporterDown`이 firing 상태가 된다.
- [ ] 중지한 컨테이너를 다시 시작한 뒤 alert가 해제되는 것을 확인한다.
- [ ] resolved 알림이 Slack 채널에 전송된다.
