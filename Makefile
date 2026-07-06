.PHONY: up down restart ps logs validate traffic k3s-load-image k3s-app-apply k3s-app-delete k3s-app-status k3s-app-logs

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=200

validate:
	bash ./scripts/healthcheck.sh

traffic:
	bash ./scripts/random-demo-traffic.sh

k3s-load-image:
	bash ./scripts/k3s-load-demo-image.sh

k3s-app-apply:
	kubectl apply -k ./k3s/app-vm

k3s-app-delete:
	kubectl delete -k ./k3s/app-vm

k3s-app-status:
	kubectl -n msa-demo get pods,svc,daemonset

k3s-app-logs:
	kubectl -n msa-demo logs -l app.kubernetes.io/part-of=msa-demo --tail=200
