# 4. 설치 및 기동 방법

## 4.1 프로젝트 다운로드

각 VM에서 리포지토리를 내려받고 프로젝트 디렉터리로 이동합니다.

```bash
git clone https://github.com/Edrient17/lgtm-observability-stack.git
cd lgtm-observability-stack
```

## 4.2 Monitoring VM 환경 변수 설정

예시 환경 변수 파일을 복사하여 실제 Docker Compose 실행에 사용할 `.env` 파일을 생성합니다.

```bash
cp .env.example .env
```

`.env`에서 다음 값을 환경에 맞게 수정합니다.

```env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<CHANGE_ME>
MINIO_ROOT_USER=lgtm
MINIO_ROOT_PASSWORD=<CHANGE_ME>
SLACK_WEBHOOK_URL=<SLACK_INCOMING_WEBHOOK_URL>
```

## 4.3 Monitoring VM 기동

Monitoring VM의 전체 LGTM backend stack은 프로젝트 루트에서 다음 단일 명령으로 기동합니다.

```bash
docker compose up -d
```

이후 정상 기동 여부를 확인합니다.

```bash
docker compose ps
```

정상 기동 예시:

![Docker Compose](https://raw.githubusercontent.com/Edrient17/lgtm-observability-stack/main/images/screenshots/docker_compose_ps.png)

## 4.4 App VM 설정

App VM에서는 K3S manifest에 사용할 ConfigMap을 생성하고 Monitoring VM private IP를 입력합니다.

```bash
cp k3s/app-vm/configmap.example.yaml k3s/app-vm/configmap.yaml
```

수정할 주요 항목은 다음과 같습니다.

```yaml
ALLOY_OTLP_EXPORTER_ENDPOINT: "<monitoring-vm-private-ip>:4317"
MIMIR_REMOTE_WRITE_URL: "http://<monitoring-vm-private-ip>:9009/api/v1/push"
LOKI_PUSH_URL: "http://<monitoring-vm-private-ip>:3100/loki/api/v1/push"
```

## 4.5 App VM 이미지 빌드 및 K3S 배포

MSA 데모 이미지를 빌드하고 K3S containerd에 import합니다.

```bash
./scripts/k3s-load-demo-image.sh
```

K3S 리소스를 적용합니다.

```bash
kubectl apply -k ./k3s/app-vm
```

상태를 확인합니다.

```bash
kubectl -n msa-demo get pods,svc,daemonset
```

## 4.6 서비스 중지

Monitoring VM stack을 중지합니다.

```bash
docker compose down
```

볼륨까지 삭제하는 초기화가 필요한 경우에만 `-v`를 사용합니다.

```bash
docker compose down -v
```

App VM의 K3S 리소스를 중지합니다.

```bash
kubectl delete -k ./k3s/app-vm
```

K3S 자체를 제거해야 하는 경우에만 아래 명령을 사용합니다.

```bash
sudo /usr/local/bin/k3s-uninstall.sh
```
