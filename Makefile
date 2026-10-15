# Docker Compose commands

# Default prompt if none is provided via command line
PROMPT ?= "A cinematic shot of a futuristic cyberpunk city, neon lights, rainy streets, highly detailed, 8k"

.PHONY: dcu dcexec gen stop logs

# Build and start containers in background
dcu:
	docker compose up -d --build

# Execute bash inside the container
dcexec:
	docker compose exec ai-app bash

# Generate image with a prompt (Usage: make gen PROMPT="your prompt")
gen:
	docker compose exec ai-app python3 -m src.main image "$(PROMPT)"

# Stop containers
stop:
	docker compose down

# View logs
logs:
	docker compose logs -f
