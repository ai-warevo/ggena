# Docker Compose commands
include .env
export

# Default values from .env if not provided via command line
PROMPT ?= $(DEFAULT_PROMPT)
IMAGE_GEN_COUNT ?= $(IMAGE_GEN_COUNT)

.PHONY: dcu dcexec gen_image stop logs help server
help:
	@echo "Available commands:"
	@echo "  make gen_image PROMPT=\"your prompt\"   - Run via Docker (uses .env count)"
	@echo "  make gen_image PROMPT=\"...\" IMAGE_GEN_COUNT=5     - Override count manually"
	@echo "  make server                            - Start the long-running API server in background"
	@echo "  make dcu                               - Build and start containers in background"
	@echo "  make stop                              - Stop containers"
	@echo "  make logs                              - View logs"

# Build and start containers in background
dcu:
	docker compose up -d --build

# Execute bash inside the container
dcexec:
	docker compose exec ai-app bash

# Generate image (Usage: make gen_image PROMPT="your prompt" IMAGE_GEN_COUNT=5)
gen_image:
	docker compose exec ai-app python3 -m src.app.cli image $(PROMPT) --num-outputs $(IMAGE_GEN_COUNT)

# Start the API server and clean up on exit
server: dcu
	docker compose exec ai-app python3 -m src.app.server && docker compose down

# Stop containers
stop:
	docker compose down

# View logs
logs:
	docker compose logs -f
