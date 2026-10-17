include .env
export

PROMPT ?= $(DEFAULT_PROMPT)
IMAGE_GEN_COUNT ?= $(IMAGE_GEN_COUNT)

TRACK ?= local
COMPOSE_FILE := docker-compose.$(TRACK).yml

.PHONY: help up exec gen_image stop logs server dev prod dev-up prod-up lint test setup clean dcu

help:
	@echo "Usage:"
	@echo "  make dev             - Start local development (dev track)"
	@echo "  make prod            - Start production (prod track)"
	@echo ""
	@echo "Available commands:"
	@echo "  up                   - Build and start containers"
	@echo "  exec                 - Execute bash inside the container"
	@echo "  gen_image            - Run image generation"
	@echo "  server               - Start API server (and stop on exit)"
	@echo "  stop                 - Stop containers"
	@echo "  logs                 - View logs"
	@echo "  lint                 - Run Ruff linter"
	@echo "  test                 - Run Pytest in container"
	@echo "  setup                - Install dependencies locally"
	@echo "  clean                - Remove build artifacts and caches"
	@echo "  dcu                  - Docker Compose Up (alias for up)"

# Pattern rules for tracks
dev-%:
	$(MAKE) $(subst dev-,,%) TRACK=local

prod-%:
	$(MAKE) $(subst prod-,,%) TRACK=prod

dev:
	$(MAKE) dev-up

prod:
	$(MAKE) prod-up

# Core commands
up:
	docker compose -f $(COMPOSE_FILE) up -d --build

exec:
	docker compose -f $(COMPOSE_FILE) exec ai-app bash

gen_image:
	docker compose -f $(COMPOSE_FILE) exec ai-app python3 -m src.app.cli image $(PROMPT) --num-outputs $(IMAGE_GEN_COUNT)

server: up
	docker compose -f $(COMPOSE_FILE) exec ai-app python3 -m src.app.server && docker compose -f $(COMPOSE_FILE) down

stop:
	docker compose -f $(COMPOSE_FILE) down

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

# New Automation Commands
lint:
	docker compose -f $(COMPOSE_FILE) exec ai-app ruff check .

test:
	docker compose -f $(COMPOSE_FILE) exec ai-app pytest tests/

setup:
	pip install uv && uv pip install -e .

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +

dcu: up
