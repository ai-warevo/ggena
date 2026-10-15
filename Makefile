# Docker Compose commands

include .env
export

# Default values from .env if not provided via command line
PROMPT ?= $(DEFAULT_PROMPT)
NEGATIVE_PROMPT ?= $(DEFAULT_NEGATIVE_PROMPT)

.PHONY: dcu dcexec gen stop logs

# Build and start containers in background
dcu:
	docker compose up -d --build

# Execute bash inside the container
dcexec:
	docker compose exec ai-app bash

# Generate image (Usage: make gen PROMPT="your prompt" NEGATIVE_PROMPT="your neg prompt")
gen:
	docker compose exec ai-app python3 -m src.main image $(PROMPT) --negative-prompt $(NEGATIVE_PROMPT)

# Stop containers
stop:
	docker compose down

# View logs
logs:
	docker compose logs -f
