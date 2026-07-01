.PHONY: up down restart ps logs preflight validate load monitoring-up monitoring-down monitoring-ps monitoring-logs app-up app-down app-ps app-logs

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d --build

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=200

preflight:
	bash ./scripts/preflight.sh

validate:
	bash ./scripts/healthcheck.sh

load:
	bash ./scripts/generate-load.sh

monitoring-up:
	docker compose up -d

monitoring-down:
	docker compose down

monitoring-ps:
	docker compose ps

monitoring-logs:
	docker compose logs -f --tail=200

app-up:
	docker compose up -d --build

app-down:
	docker compose down

app-ps:
	docker compose ps

app-logs:
	docker compose logs -f --tail=200
