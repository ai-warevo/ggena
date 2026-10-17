# Refactoring Task: Decomposing Server (`src/app/server.py`)

You are a senior developer tasked with decomposing the monolithic `src/app/server.py` into a modular FastAPI application structure.

## Context
The current server implementation mixes app configuration, middleware, lifespan management, and all API routes (HTTP and WebSocket) in a single file.

## Refactoring Plan
Create a new directory `src/app/server/` and move logic as follows:
1. **`main.py`**: The entry point; creates the `FastAPI` app, registers middleware, mounts static files, and handles the `lifespan`.
2. **`models.py`**: Contains Pydantic models (`RequestModel`, `ResponseModel`).
3. **`middleware.py`**: Contains custom middleware like `MetricsMiddleware`.
4. **`routes/`**: A directory for all API endpoints using `APIRouter`.
    - **`health.py`**: `/health/live` and `/health/ready`.
    - **`metrics.py`**: `/metrics`.
    - **`static.py`**: `/` (index) and static file mounting logic.
    - **`generation.py`**: The core generation endpoints: `POST /generate/{module}` and `WS /ws/generate/{module}`.

## Verification
- Ensure the API remains fully functional with all HTTP and WebSocket routes.
- Verify that `app.state` (config, registry, executor, etc.) is correctly populated in `main.py` and accessible to route handlers via `request.app.state`.
- Run existing integration tests to ensure no regressions in endpoint behavior.
