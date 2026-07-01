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
	docker compose --env-file .env.monitoring -f docker-compose.monitoring.yml up -d

monitoring-down:
	docker compose --env-file .env.monitoring -f docker-compose.monitoring.yml down

monitoring-ps:
	docker compose --env-file .env.monitoring -f docker-compose.monitoring.yml ps

monitoring-logs:
	docker compose --env-file .env.monitoring -f docker-compose.monitoring.yml logs -f --tail=200

app-up:
	docker compose --env-file .env.app -f docker-compose.app.yml up -d --build

app-down:
	docker compose --env-file .env.app -f docker-compose.app.yml down

app-ps:
	docker compose --env-file .env.app -f docker-compose.app.yml ps

app-logs:
	docker compose --env-file .env.app -f docker-compose.app.yml logs -f --tail=200
