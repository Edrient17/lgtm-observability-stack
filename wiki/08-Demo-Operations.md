# 8. 애플리케이션 시범 운영

## 8.1 랜덤 트래픽 생성

App VM에서 정상 트래픽을 수동으로 생성합니다.

```bash
cd ~/lgtm-observability-stack
DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh
```

반복 생성이 필요하면 다음 명령어를 사용합니다.

```bash
while true; do DEMO_APP_URL=http://localhost:8080 ./scripts/random-demo-traffic.sh; sleep 10; done
```

여러 날 관찰할 경우 cron에 등록합니다.

```cron
* * * * * cd /home/ubuntu/lgtm-observability-stack && DEMO_APP_URL=http://localhost:8080 MAX_REQUESTS_PER_RUN=30 IDLE_CHANCE_PERCENT=0 BURST_CHANCE_PERCENT=20 ./scripts/random-demo-traffic.sh >> /home/ubuntu/lgtm-observability-stack/logs/random-demo-traffic.log 2>&1
```

랜덤 트래픽 스크립트는 정상 요청만 생성합니다.
위 cron 예시는 1분마다 실행하되 한 번 실행될 때 요청 수를 늘려 대시보드에서 request rate를 더 잘 관찰할 수 있게 합니다.
애플리케이션은 평상시 정상 동작을 목표로 하며, 장애 테스트는 실제 컴포넌트를 중단하고 복구하는 방식으로 수행합니다.
