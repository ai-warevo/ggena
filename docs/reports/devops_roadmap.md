# DevOps & SRE Roadmap for Ggena

This document outlines the strategy for optimizing the deployment, automation, and operational lifecycle of the **ggena** project.

## 1. Containerization Strategy

### Current State Assessment
- **Base Image**: Uses `huggingface/transformers-pytorch-gpu`, which is functional but heavy.
- **Build Process**: Uses `uv` for fast dependency management (excellent).
- **Security**: Production image uses a non-root user (excellent).
- **Caching**: Leverages layer caching by copying packaging files first.

### Proposed Optimization: Multi-Stage Builds
To reduce production image size and improve security, we should implement a multi-stage build. This separates the build environment (containing `uv` and compilers) from the runtime environment.

#### Optimized `Dockerfile.prod` (Proposed)
```dockerfile
# --- Stage 1: Builder ---
FROM huggingface/transformers-pytorch-gpu AS builder

ENV TZ=Asia/Krasnoyarsk \
    DEBIAN_FRONTEND=noninteractive \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy only dependency files first
COPY pyproject.toml README.md ./

# Install dependencies into a specific prefix to easily copy them later
RUN uv pip install --system --no-cache .

# --- Stage 2: Runtime ---
FROM huggingface/transformers-pytorch-gpu AS runtime

ENV TZ=Asia/Krasnoyarsk \
    DEBIAN_FRONTEND=noninteractive

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get update && apt-get install -y tzdata && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Create non-root user
RUN groupadd -r ggena_group && useradd -r -g ggena_group -m -s /sbin/nologin ggena_user

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code and static assets
COPY src/ ./src/
COPY static/ ./static/

# Ensure ownership
RUN chown -R ggena_user:ggena_group /workspace

USER ggena_user

CMD ["python3", "-m", "src.app.server"]
```

---

## 2. CI/CD Pipeline Design (GitHub Actions)

We propose a GitHub Actions workflow to ensure code quality and security at every pull request and push to `main`.

#### Proposed `.github/workflows/ci.yml`
```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install --system ruff mypy pytest safety

      - name: Lint with Ruff
        run: ruff check .

      - name: Type Check with Mypy
        run: mypy src/

      - name: Security Scan (Safety)
        run: safety check

  test:
    needs: quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install --system . pytest

      - name: Run Tests
        run: pytest tests/

  container-scan:
    needs: quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker Image (Local)
        run: docker build -t ggena-test:latest -f Dockerfile.local .

      - name: Scan image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'ggena-test:latest'
          format: 'table'
          exit-code: '1' # Fail the build if vulnerabilities are found
          severity: 'CRITICAL,HIGH'
```

---

## 3. Developer Experience (DX)

### Makefile Improvements
The current `Makefile` is a good start but lacks standard automation for testing and linting. We also need to fix the discrepancy where `README.md` refers to `make dcu`, which does not exist.

#### Expanded `Makefile` (Proposed)
```makefile
include .env
export

PROMPT ?= $(DEFAULT_PROMPT)
IMAGE_GEN_COUNT ?= $(IMAGE_GEN_COUNT)

TRACK ?= local
COMPOSE_FILE := docker-compose.$(TRACK).yml

.PHONY: help up exec gen_image stop logs server dev prod dev-up prod-up \
        lint test setup clean dcu

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
```

---

## 4. Deployment & Orchestration

### Production Environment (Kubernetes)
For a production-grade deployment, we recommend **Kubernetes** with the following components:
1.  **NVIDIA Device Plugin**: To allow pods to request and utilize GPU resources.
2.  **Horizontal Pod Autoscaler (HPA)**: Scale based on custom metrics like GPU utilization or request queue depth.
3.  **Ingress Controller**: (e.g., Nginx or Traefik) for managing external access and SSL termination.

### Large Model Weights Management
Managing multi-gigabyte model weights in a distributed environment requires avoiding downloading them every time a pod starts.

**Strategies:**
1.  **Shared Persistent Volumes (PV/PVC)**: Use high-performance shared filesystems like **Amazon EFS**, **Google Cloud Filestore**, or **Azure Files**. Mount the `hf_cache` directory to all pods.
2.  **Object Storage with Local Caching**: Store weights in S3/GCS and use a sidecar container or an init container to pull them into a local ephemeral volume before the main application starts.
3.  **ReadWriteMany (RWX) Volumes**: Ensure the storage class supports `ReadWriteMany` so multiple pods can read from the same cache simultaneously.

---

## 5. Observability Strategy

To maintain high availability and performance, we recommend a three-pillar approach:

### 1. Structured Logging
Replace standard print/logging with **JSON structured logging**. This allows tools like ELK (Elasticsearch, Logstash, Kibana) or Loki to parse logs easily for querying.
*   **Implementation**: Use `structlog` or configure the standard `logging` library to output JSON.

### 2. Metrics Collection (Prometheus/Grafana)
Expose a `/metrics` endpoint in the FastAPI application using `prometheus-client`.
*   **Key Metrics to Track**:
    *   `ggena_request_latency_seconds`: Histogram of request durations.
    *   `ggena_generation_errors_total`: Counter for failed generation attempts (labeled by error type).
    *   `ggena_active_generations`: Gauge of currently running tasks.
    *   **GPU Metrics**: Use `nvidia-dcgm-exporter` to track GPU temperature, memory usage, and utilization at the node level.

### 3. Health Checks
Implement Kubernetes **Liveness** and **Readiness** probes:
*   **Readiness Probe**: Ensures the model is fully loaded into VRAM before sending traffic.
*   **Liveness Probe**: Restarts the container if the FastAPI server becomes unresponsive.
