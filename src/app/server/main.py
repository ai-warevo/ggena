import uvicorn
import asyncio
import threading
import torch
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.registry import GeneratorRegistry
from src.core.utils import discover_and_register_generators
from src.core.config import ConfigManager, config
from src.core.commands import GenerationCommand, CommandContext
from src.core.executor import CommandExecutor
from src.core.logging_setup import setup_logging

from src.app.server.middleware import MetricsMiddleware
from src.app.server.routes import health_router, metrics_router, static_router, http_generation_router, ws_generation_router

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("--- [Server] Starting up ---")
    # 1. Initialize core components
    config_mgr = ConfigManager()
    registry = GeneratorRegistry()
    discover_and_register_generators("src.generators", registry)
    
    # Store them in app state for access in routes
    app.state.config = config_mgr
    app.state.registry = registry
    app.state.models_loaded = False

    # Create a shutdown event to signal all running generators
    shutdown_event = threading.Event()
    app.state.shutdown_event = shutdown_event
    app.state.executor = CommandExecutor(CommandContext(registry=registry, config=config_mgr, shutdown_event=shutdown_event))
    
    # 2. Pre-load models by getting singleton instances and setting shutdown event
    available = registry.list_available()
    logger.info(f"--- [Server] Available modules: {available} ---")
    for module in available:
        logger.info(f"--- [Server] Pre-loading model for '{module}'... ---")
        registry.get_instance(module, config=config_mgr)
    
    app.state.models_loaded = True
    # RTX 4080 Optimizations
    torch.backends.cuda.matmul.allow_tf32 = True
    logger.info("--- [Server] All models pre-loaded and GPU optimized! ---")

    yield

    logger.info("--- [Server] Shutting down ---")
    shutdown_event.set()
    # Allow a small grace period for generators to catch the event
    await asyncio.sleep(1)

app = FastAPI(title="ggena API Server", lifespan=lifespan)

# Add middleware
app.add_middleware(MetricsMiddleware)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in config.get_str("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="src/app/frontend"), name="static")

# Include routers
app.include_router(static_router)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(http_generation_router)
app.include_router(ws_generation_router)

if __name__ == "__main__":
    port = config.get_int("PORT", 8000)
    uvicorn.run(app, host="0.0.0.0", port=port)
