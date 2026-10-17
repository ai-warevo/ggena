include .env
export

PROMPT ?= $(DEFAULT_PROMPT)
IMAGE_GEN_COUNT ?= $(IMAGE_GEN_COUNT)

# Default track is local for development convenience
TRACK ?= local
COMPOSE_FILE := docker-compose.$(TRACK).yml

.PHONY: help up exec gen_image stop logs server dev prod dev-up prod-up

help:
	@echo "Usage:"
	@echo "  make dev             - Start local development (dev track)"
	@echo "  make prod            - Start production (prod track)"
	@echo "  make dev-<cmd>       - Run <cmd> in dev track (e.g., make dev-exec)"
	@echo "  make prod-<cmd>      - Run <cmd> in prod track (e.g., make prod-gen_image)"
	@echo ""
	@echo "Available commands:"
	@echo "  up                   - Build and start containers"
	@echo "  exec                 - Execute bash inside the container"
	@echo "  gen_image            - Run image generation"
	@echo "  server               - Start API server (and stop on exit)"
	@echo "  stop                 - Stop containers"
	@echo "  logs                 - View logs"

# Pattern rules for tracks: maps dev-<cmd> -> <cmd> with TRACK=local
dev-%:
	$(MAKE) $(subst dev-,,%) TRACK=local

# Pattern rules for tracks: maps prod-<cmd> -> <cmd> with TRACK=prod
prod-%:
	$(MAKE) $(subst prod-,,%) TRACK=prod

# Shortcuts for the track names themselves
dev:
	$(MAKE) dev-up

prod:
	$(MAKE) prod-up

# Core commands (using $(COMPOSE_FILE))
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
