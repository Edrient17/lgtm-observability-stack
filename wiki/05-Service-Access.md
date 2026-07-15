# 5. 서비스 접속 정보

## 5.1 Grafana

| 항목 | 값 |
| --- | --- |
| URL | `http://<monitoring-vm-public-ip>:3000` |
| 기본 계정 | `.env`의 `GRAFANA_ADMIN_USER` |
| 기본 비밀번호 | `.env`의 `GRAFANA_ADMIN_PASSWORD` |

초기 예시는 다음과 같습니다.

```text
Username: admin
Password: admin
```

실제 배포 시에는 `.env`에서 `GRAFANA_ADMIN_PASSWORD`를 변경합니다.

## 5.2 주요 내부 Endpoint

Monitoring VM에서 확인:

```bash
curl http://localhost:3100/ready
curl http://localhost:9009/ready
curl http://localhost:3200/ready
curl http://localhost:9090/-/ready
```

App VM에서 확인:

```bash
curl http://<monitoring-vm-private-ip>:3100/ready
curl http://<monitoring-vm-private-ip>:9009/ready
curl http://<monitoring-vm-private-ip>:4318/
curl http://localhost:8080/browse
curl http://localhost:8080/cart/add
curl http://localhost:8080/checkout
```
