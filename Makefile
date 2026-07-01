.PHONY: up up-build down restart ps logs validate traffic

up:
	docker compose up -d

up-build:
	docker compose up -d --build

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
