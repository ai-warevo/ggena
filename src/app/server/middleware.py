import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from src.core.metrics import REQUEST_LATENCY

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            process_time = time.perf_counter() - start_time
            REQUEST_LATENCY.observe(process_time)
