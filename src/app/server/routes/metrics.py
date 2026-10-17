from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter(prefix="/metrics")

@router.get("")
async def get_metrics():
    """Exposes Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
