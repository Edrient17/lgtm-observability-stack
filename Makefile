.PHONY: up down restart ps logs preflight validate load

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
